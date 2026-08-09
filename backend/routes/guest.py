import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.services.confidence_service import (
    calculate_confidence,
    filter_relevant_chunks
)
from backend.services.hybrid_retrieval_service import hybrid_search
from backend.services.llm_service import (
    LLMServiceError,
    generate_answer,
    is_no_information_answer,
)
from backend.services.logging_service import log_error, log_info
from backend.services.query_rewrite_service import rewrite_query
from backend.services.question_validation import validate_single_question
from backend.services.rate_limit_service import rate_limit_guest_ask
from backend.services.rerank_service import rerank
from backend.services.retrieval_contract import build_retrieval_response
from backend.services.retrieval_service import get_context

from backend.routes.ask import (
    NO_MATCH_MESSAGE,
    AskResponse,
    _build_llm_http_exception,
    _build_sources,
)


router = APIRouter()


def _guest_mode_enabled() -> bool:
    return (
        os.getenv("GUEST_MODE_ENABLED", "false").strip().lower()
        in {"1", "true", "yes"}
    )


def _guest_allowed_documents() -> set[str]:
    """
    Guest queries are restricted to this explicit allow-list, not the
    full live knowledge base. This is deliberate: this endpoint has no
    login at all, so anyone on the internet can hit it. If this project
    is ever used for real internal documents alongside the public demo
    ones, an unrestricted guest endpoint would quietly leak them to
    anyone who found the URL. Requiring an explicit allow-list means a
    real document only becomes guest-visible if someone deliberately
    adds its exact filename here — never by default.
    """

    raw = os.getenv("GUEST_ALLOWED_DOCUMENTS", "")

    return {
        name.strip()
        for name in raw.split(",")
        if name.strip()
    }


class GuestAskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


@router.post(
    "/guest/ask",
    response_model=AskResponse
)
def guest_ask_question(payload: GuestAskRequest, request: Request):
    """
    Same retrieval -> confidence -> generation pipeline as POST /ask,
    but with no login required, no history/session recording (there is
    no account to attach it to), a much stricter per-IP rate limit, and
    results restricted to an explicit allow-list of public demo
    documents rather than the whole knowledge base.

    Intended for a "try it without logging in" link on the landing
    page — e.g. for people evaluating the project (recruiters,
    portfolio reviewers) without needing a shared demo account.
    """

    if not _guest_mode_enabled():
        raise HTTPException(
            status_code=404,
            detail="Not found.",
        )

    allowed_documents = _guest_allowed_documents()

    if not allowed_documents:
        # Fail loud, not open: guest mode is on but nothing has been
        # explicitly allow-listed yet, so there is nothing safe to
        # answer from. This is a configuration gap, not "show
        # everything" — silently falling back to the full knowledge
        # base here is exactly the leak this design is meant to avoid.
        log_error(
            "GUEST_MODE_ENABLED is true but GUEST_ALLOWED_DOCUMENTS "
            "is empty — refusing to answer."
        )
        raise HTTPException(
            status_code=503,
            detail="Guest mode is not fully configured yet.",
        )

    rate_limit_guest_ask(request)

    query = validate_single_question(payload.query)

    log_info(f"/guest/ask — ip={request.client.host if request.client else 'unknown'}")

    try:
        search_query = rewrite_query(query)

        # The allow-list is pushed into the retrieval query itself
        # (document_names=...) rather than filtered out of the results
        # afterwards. Filtering after the fact meant the top-10 pool
        # was chosen from the *entire* knowledge base first — if none
        # of an allowed document's chunks happened to rank in that
        # unfiltered top-10, a guest got "no relevant information"
        # even when the allowed document genuinely had a good answer.
        # Scoping the query itself means the top-10 pool is always
        # drawn only from documents the guest is allowed to see (P3-01).
        candidates = hybrid_search(
            search_query,
            top_k=10,
            document_names=allowed_documents,
        )

        reranked = rerank(search_query, candidates, top_k=5)

        normalized = build_retrieval_response(query, reranked)

        reranked_results = [
            chunk.model_dump()
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

        if confidence_info["confidence"] == "Low" or not relevant_chunks:
            answer = NO_MATCH_MESSAGE
            sources = []

            if not relevant_chunks:
                confidence_info = {
                    **confidence_info,
                    "confidence": "Low",
                    "supporting_chunks": 0,
                }

        else:
            context = get_context(relevant_chunks)
            answer = generate_answer(query, context)

            if is_no_information_answer(answer):
                confidence_info = {
                    **confidence_info,
                    "confidence": "Low",
                    "supporting_chunks": 0,
                }
                sources = []
            else:
                sources = _build_sources(relevant_chunks)

    except LLMServiceError as exc:
        log_error(f"Guest ask LLM error: {exc.category}")
        raise _build_llm_http_exception(exc) from exc

    except HTTPException:
        raise

    except Exception as exc:
        # Previously only LLMServiceError was caught here — any other
        # unexpected failure (retrieval, reranking, confidence scoring)
        # fell through uncaught to FastAPI's default handler, which
        # skips this project's structured logging and, depending on
        # debug settings, can leak an internal traceback to the caller
        # (P3-03). Mirrors the equivalent broad catch in ask.py.
        log_error(f"/guest/ask failed — type={type(exc).__name__}")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate answer.",
        ) from exc

    return AskResponse(
        question=query,
        rewritten_query=search_query,
        answer=answer,
        sources=sources,
        confidence=confidence_info["confidence"],
        top_relevance_score=confidence_info.get("top_score"),
        supporting_chunks=confidence_info.get("supporting_chunks", 0),
        conversation_id="guest",
    )
