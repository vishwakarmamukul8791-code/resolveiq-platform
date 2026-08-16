import os
import re
from pathlib import PurePath

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from rank_bm25 import BM25Plus

from backend.routes.ask import (
    NO_MATCH_MESSAGE,
    _build_llm_http_exception,
)
from backend.services.llm_service import (
    LLMServiceError,
    generate_answer,
    is_no_information_answer,
)
from backend.services.logging_service import log_error, log_info
from backend.services.question_validation import validate_single_question
from backend.services.rate_limit_service import rate_limit_guest_ask


router = APIRouter()

MAX_TEXT_CHARS = 20_000
MAX_FILENAME_CHARS = 120
CHUNK_SIZE = 700
CHUNK_OVERLAP = 120
TOP_K = 4


def _guest_mode_enabled() -> bool:
    return (
        os.getenv("GUEST_MODE_ENABLED", "false").strip().lower()
        in {"1", "true", "yes"}
    )


def _safe_filename(name: str) -> str:
    cleaned = PurePath(name.strip()).name
    if not cleaned or len(cleaned) > MAX_FILENAME_CHARS:
        raise HTTPException(status_code=400, detail="Invalid document name.")
    if not cleaned.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="The public custom-document sandbox accepts TXT files only.",
        )
    return cleaned


def _normalize_text(text: str) -> str:
    # Null bytes do not belong in plain-text runbooks and can cause surprising
    # downstream behavior. Keep ordinary newlines so incident/runbook structure
    # remains readable in the grounded context sent to the model.
    normalized = text.replace("\x00", "").replace("\r\n", "\n").strip()
    if len(normalized) < 40:
        raise HTTPException(
            status_code=400,
            detail="Upload a TXT document with at least 40 characters.",
        )
    if len(normalized) > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail="TXT sandbox documents are limited to 20,000 characters.",
        )
    return normalized


def _chunk_text(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0
    step = CHUNK_SIZE - CHUNK_OVERLAP

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step

    return chunks


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_./:-]*", value.lower())


def _retrieve_chunks(query: str, chunks: list[str], top_k: int = TOP_K) -> list[dict]:
    tokenized_chunks = [_tokenize(chunk) for chunk in chunks]
    if not any(tokenized_chunks):
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # BM25Plus is used instead of BM25Okapi because visitor-supplied TXT
    # files often produce only one or two chunks. With such tiny corpora,
    # Okapi BM25 can assign zero/negative IDF to otherwise exact matches,
    # causing a valid query to look unrelated. BM25Plus keeps the lexical
    # retrieval behavior while remaining well-defined for tiny corpora.
    bm25 = BM25Plus(tokenized_chunks)
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(
        enumerate(scores),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )

    results = []
    for index, score in ranked:
        numeric_score = float(score)
        if numeric_score <= 0:
            continue
        results.append(
            {
                "chunk_index": index + 1,
                "score": numeric_score,
                "text": chunks[index],
            }
        )
        if len(results) >= top_k:
            break

    return results


class CustomTextAskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_name: str = Field(min_length=1, max_length=MAX_FILENAME_CHARS)
    document_text: str = Field(min_length=40, max_length=MAX_TEXT_CHARS)


class CustomTextSource(BaseModel):
    document_name: str
    chunk_index: int


class CustomTextAskResponse(BaseModel):
    question: str
    answer: str
    confidence: str
    sources: list[CustomTextSource]
    supporting_chunks: int
    retrieval_method: str
    persistence: str


@router.post("/guest/custom-text/ask", response_model=CustomTextAskResponse)
def custom_text_ask(payload: CustomTextAskRequest, request: Request):
    """Ask a question against one visitor-supplied TXT document.

    This endpoint is deliberately separate from ResolveIQ's real upload/process
    APIs. The document is never inserted into the registry, object storage,
    pgvector/FAISS, or chat history. It exists only in the request, is chunked
    in memory, retrieved with bounded BM25, and discarded after the response.

    The main public demo continues to exercise the real hybrid RAG pipeline.
    This sandbox exists only so evaluators can safely try their own small text
    without receiving admin mutation authority or creating persistent data.
    """

    if not _guest_mode_enabled():
        raise HTTPException(status_code=404, detail="Not found.")

    rate_limit_guest_ask(request)

    query = validate_single_question(payload.query)
    document_name = _safe_filename(payload.document_name)
    document_text = _normalize_text(payload.document_text)

    chunks = _chunk_text(document_text)
    relevant = _retrieve_chunks(query, chunks)

    log_info(
        "/guest/custom-text/ask — "
        f"ip={request.client.host if request.client else 'unknown'} "
        f"document={document_name} chunks={len(chunks)} matched={len(relevant)}"
    )

    if not relevant:
        return CustomTextAskResponse(
            question=query,
            answer=NO_MATCH_MESSAGE,
            confidence="Low",
            sources=[],
            supporting_chunks=0,
            retrieval_method="temporary_bm25",
            persistence="not_stored",
        )

    context_parts = [
        (
            f"[Uploaded TXT: {document_name} | chunk {item['chunk_index']}]\n"
            f"{item['text']}"
        )
        for item in relevant
    ]
    context = "\n\n---\n\n".join(context_parts)

    try:
        answer = generate_answer(query, context)
    except LLMServiceError as exc:
        log_error(f"Custom TXT guest LLM error: {exc.category}")
        raise _build_llm_http_exception(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:
        log_error(
            "/guest/custom-text/ask failed — "
            f"type={type(exc).__name__}"
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to generate answer.",
        ) from exc

    if is_no_information_answer(answer):
        return CustomTextAskResponse(
            question=query,
            answer=NO_MATCH_MESSAGE,
            confidence="Low",
            sources=[],
            supporting_chunks=0,
            retrieval_method="temporary_bm25",
            persistence="not_stored",
        )

    return CustomTextAskResponse(
        question=query,
        answer=answer,
        confidence="Grounded",
        sources=[
            CustomTextSource(
                document_name=document_name,
                chunk_index=item["chunk_index"],
            )
            for item in relevant
        ],
        supporting_chunks=len(relevant),
        retrieval_method="temporary_bm25",
        persistence="not_stored",
    )
