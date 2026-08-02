import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from backend.services.auth_service import get_current_user
from backend.services.confidence_service import (
    calculate_confidence,
    filter_relevant_chunks
)
from backend.services.history_service import load_history, save_history
from backend.services.hybrid_retrieval_service import hybrid_search
from backend.services.llm_service import (
    LLMServiceError,
    generate_answer
)
from backend.services.logging_service import log_error, log_info
from backend.services.query_rewrite_service import rewrite_query
from backend.services.rerank_service import rerank
from backend.services.retrieval_contract import (
    build_retrieval_response
)
from backend.services.retrieval_service import get_context
from backend.services.session_service import record_question


router = APIRouter()

NO_MATCH_MESSAGE = (
    "I couldn't find relevant information in the knowledge base "
    "to answer this question confidently."
)

LLM_ERROR_RESPONSES = {
    "rate_limit": (
        429,
        "The AI service quota is temporarily exhausted. "
        "Please try again shortly."
    ),
    "timeout": (
        504,
        "The AI service took too long to respond. "
        "Please try again."
    ),
    "authentication": (
        503,
        "The AI service is temporarily unavailable."
    ),
    "configuration": (
        503,
        "The AI service is temporarily unavailable."
    ),
    "unavailable": (
        503,
        "The AI service is temporarily unavailable. "
        "Please try again later."
    ),
    "provider_error": (
        502,
        "The AI service rejected the request. "
        "Please try again."
    ),
    "empty_response": (
        502,
        "The AI service returned an empty response. "
        "Please try again."
    )
}


class AskRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000
    )
    document_name: Optional[str] = Field(
        default=None,
        max_length=255
    )
    conversation_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description=(
            "Pass back the conversation_id from a previous /ask response "
            "to continue that thread. Omit it to start a new one."
        )
    )


class SourceReference(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    source_location: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    rewritten_query: str
    answer: str
    sources: list[SourceReference]
    confidence: Literal["High", "Medium", "Low"]
    top_relevance_score: Optional[float] = None
    supporting_chunks: int
    conversation_id: str


def _build_sources(relevant_chunks):
    sources = []
    seen_source_keys = set()

    for result in relevant_chunks:
        source_key = (
            result["document_name"],
            result.get("page_number"),
            result.get("source_location")
        )

        if source_key in seen_source_keys:
            continue

        seen_source_keys.add(source_key)

        sources.append({
            "document_name": result["document_name"],
            "page_number": result.get("page_number"),
            "source_location": result.get(
                "source_location"
            )
        })

    return sources


def _normalize_request(payload: AskRequest):
    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty."
        )

    document_name = payload.document_name

    if document_name is not None:
        document_name = document_name.strip() or None

    conversation_id = (
        payload.conversation_id.strip()
        if payload.conversation_id and payload.conversation_id.strip()
        else str(uuid.uuid4())
    )

    return query, document_name, conversation_id


def _build_llm_http_exception(
    exc: LLMServiceError
):
    status_code, detail = LLM_ERROR_RESPONSES.get(
        exc.category,
        (
            502,
            "The AI service could not complete the request. "
            "Please try again."
        )
    )

    headers = (
        {"Retry-After": "30"}
        if status_code == 429
        else None
    )

    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers
    )


@router.post(
    "/ask",
    response_model=AskResponse
)
def ask_question(
    payload: AskRequest,
    x_session_id: Optional[str] = Header(
        default=None
    ),
    current_user: dict = Depends(
        get_current_user
    )
):
    """
    Runs the authenticated RAG pipeline.

    The question and optional document scope are accepted
    in a JSON body so incident details do not appear in
    access logs or browser history.
    """

    try:
        query, document_name, conversation_id = _normalize_request(
            payload
        )

        username = current_user["username"]

        log_info(
            f"/ask — user={username} "
            f"session="
            f"{x_session_id[:8] if x_session_id else 'none'}"
        )

        search_query = rewrite_query(query)

        candidates = hybrid_search(
            search_query,
            top_k=10,
            document_name=document_name
        )

        reranked = rerank(
            search_query,
            candidates,
            top_k=5
        )

        normalized = build_retrieval_response(
            query,
            reranked
        )

        reranked_results = [
            chunk.dict()
            for chunk in normalized.results
        ]

        confidence_info = calculate_confidence(
            reranked_results,
            method=normalized.method,
        )

        relevant_chunks = filter_relevant_chunks(
            reranked_results,
            method=normalized.method,
        )

        if (
            confidence_info["confidence"] == "Low"
            or not relevant_chunks
        ):
            answer = NO_MATCH_MESSAGE
            sources = []

            if not relevant_chunks:
                confidence_info = {
                    **confidence_info,
                    "confidence": "Low",
                    "supporting_chunks": 0
                }

            log_info(
                "Low confidence — LLM skipped "
                f"for user={username}"
            )

        else:
            context = get_context(relevant_chunks)

            answer = generate_answer(
                query,
                context
            )

            # Citations contain only chunks supplied
            # to the answer-generation model.
            sources = _build_sources(
                relevant_chunks
            )

        record_question(
            x_session_id,
            confidence_info["confidence"]
        )

        history = load_history()

        history.append({
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "pinned": False,
            "username": username,
            "session_id": x_session_id,
            "question": query,
            "rewritten_query": search_query,
            "answer": answer,
            "confidence": (
                confidence_info["confidence"]
            ),
            "sources": [
                source["document_name"]
                for source in sources
            ],
            "created_at": datetime.now().isoformat()
        })

        save_history(history)

        log_info(
            f"Request completed — user={username} "
            f"confidence="
            f"{confidence_info['confidence']}"
        )

        return {
            "question": query,
            "rewritten_query": search_query,
            "answer": answer,
            "sources": sources,
            "confidence": (
                confidence_info["confidence"]
            ),
            "top_relevance_score": (
                confidence_info["top_score"]
            ),
            "supporting_chunks": (
                confidence_info["supporting_chunks"]
            ),
            "conversation_id": conversation_id
        }

    except LLMServiceError as exc:
        username = current_user.get(
            "username",
            "unknown"
        )

        log_error(
            f"/ask LLM failure — user={username} "
            f"category={exc.category}"
        )

        raise _build_llm_http_exception(
            exc
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        username = current_user.get(
            "username",
            "unknown"
        )

        log_error(
            f"/ask failed — user={username} "
            f"type={type(exc).__name__}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate answer."
        ) from exc