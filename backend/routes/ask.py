from fastapi import APIRouter, HTTPException
from datetime import datetime

from backend.services.logging_service import log_info, log_error
from backend.services.hybrid_retrieval_service import hybrid_search
from backend.services.rerank_service import rerank
from backend.services.retrieval_contract import build_retrieval_response
from backend.services.retrieval_service import get_context
from backend.services.llm_service import generate_answer
from backend.services.history_service import load_history, save_history
from backend.services.confidence_service import (
    calculate_confidence,
    filter_relevant_chunks
)

router = APIRouter()

NO_MATCH_MESSAGE = (
    "I couldn't find relevant information in the knowledge base "
    "to answer this question confidently."
)


@router.get("/ask")
def ask_question(query: str, document_name: str | None = None):

    try:

        log_info(f"Question Received: {query}")

        candidates = hybrid_search(
            query,
            top_k=10,
            document_name=document_name
        )

        reranked = rerank(query, candidates, top_k=5)

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

            log_info("Low confidence — skipped LLM call, returned abstain message.")

        else:

            relevant_chunks = filter_relevant_chunks(reranked_results)

            context = get_context(relevant_chunks)

            answer = generate_answer(query, context)

        history = load_history()

        history.append({
            "question": query,
            "answer": answer,
            "confidence": confidence_info["confidence"],
            "created_at": datetime.now().isoformat()
        })

        save_history(history)

        log_info("Answer generated successfully.")

        return {
            "question": query,
            "answer": answer,
            "sources": sources,
            "confidence": confidence_info["confidence"],
            "top_relevance_score": confidence_info["top_score"],
            "supporting_chunks": confidence_info["supporting_chunks"]
        }

    except Exception as e:

        log_error(str(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to generate answer."
        )