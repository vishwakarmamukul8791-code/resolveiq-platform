from fastapi import APIRouter, HTTPException, Depends, Header
from datetime import datetime
from typing import Optional

from backend.services.logging_service import log_info, log_error
from backend.services.query_rewrite_service import rewrite_query
from backend.services.hybrid_retrieval_service import hybrid_search
from backend.services.rerank_service import rerank
from backend.services.retrieval_contract import build_retrieval_response
from backend.services.retrieval_service import get_context
from backend.services.llm_service import generate_answer
from backend.services.history_service import load_history, save_history
from backend.services.session_service import record_question
from backend.services.confidence_service import (
    calculate_confidence,
    filter_relevant_chunks
)
from backend.services.auth_service import get_current_user
import uuid

router = APIRouter()

NO_MATCH_MESSAGE = (
    "I couldn't find relevant information in the knowledge base "
    "to answer this question confidently."
)


@router.get("/ask")
def ask_question(
    query: str,
    document_name: str | None = None,
    x_session_id: Optional[str] = Header(default=None),
    current_user: dict = Depends(get_current_user)
):
    """
    The core RAG endpoint. Now requires authentication.

    session_id is passed as the X-Session-Id header (set by the frontend
    at login). Used to track per-engineer question counts and confidence
    breakdown in the admin analytics.

    username comes from the JWT via get_current_user — not from the request
    body, so it can't be spoofed by the caller.

    Interview answer: "Why header for session_id and not query param?"
    Query params end up in server logs and browser history. Session IDs
    are opaque identifiers — they belong in headers, same reason auth
    tokens go in Authorization header rather than ?token=... in the URL.
    """

    try:

        username = current_user["username"]

        log_info(f"/ask — user={username} session={x_session_id[:8] if x_session_id else 'none'}")

        search_query = rewrite_query(query)
        # search_query = query

        candidates = hybrid_search(
            search_query,
            top_k=10,
            document_name=document_name
        )

        reranked = rerank(search_query, candidates, top_k=5)

        normalized = build_retrieval_response(query, reranked)

        reranked_results = [chunk.dict() for chunk in normalized.results]

        confidence_info = calculate_confidence(reranked_results)

        sources = []
        seen_source_keys = set()

        for result in reranked_results:

            source_key = (
                result["document_name"],
                result.get("page_number")
            )

            if source_key not in seen_source_keys:
                seen_source_keys.add(source_key)
                sources.append({
                    "document_name": result["document_name"],
                    "page_number": result.get("page_number"),
                    "source_location": result.get("source_location")
                })

        if confidence_info["confidence"] == "Low":

            answer = NO_MATCH_MESSAGE
            sources = []

            log_info(f"Low confidence — LLM skipped for user={username}")

        else:

            relevant_chunks = filter_relevant_chunks(reranked_results)
            context = get_context(relevant_chunks)
            answer = generate_answer(query, context)

        # Record to session analytics BEFORE saving history
        record_question(x_session_id, confidence_info["confidence"])

        history = load_history()

        history.append({
            "id": str(uuid.uuid4()),
            "pinned": False,
            "username": username,
            "session_id": x_session_id,
            "question": query,
            "rewritten_query": search_query,
            "answer": answer,
            "confidence": confidence_info["confidence"],
            "sources": [s["document_name"] for s in sources],
            "created_at": datetime.now().isoformat()
        })

        save_history(history)

        log_info(f"Answer generated — user={username} confidence={confidence_info['confidence']}")

        return {
            "question": query,
            "rewritten_query": search_query,
            "answer": answer,
            "sources": sources,
            "confidence": confidence_info["confidence"],
            "top_relevance_score": confidence_info["top_score"],
            "supporting_chunks": confidence_info["supporting_chunks"]
        }

    except HTTPException:
        raise

    except Exception as e:

        log_error(str(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to generate answer."
        )