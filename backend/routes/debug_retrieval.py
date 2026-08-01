from fastapi import APIRouter, Depends, HTTPException

from backend.services.auth_service import require_admin
from backend.services.logging_service import log_info, log_error
from backend.services.query_rewrite_service import rewrite_query
from backend.services.retrieval_service import search_similar_chunks
from backend.services.bm25_service import search_bm25
from backend.services.hybrid_retrieval_service import hybrid_search
from backend.services.rerank_service import rerank
from backend.services.retrieval_contract import build_retrieval_response
from backend.services.confidence_service import calculate_confidence

router = APIRouter()

DEBUG_TOP_K = 5
CANDIDATE_POOL_SIZE = 10


def _format_results(raw_results):
    """
    Compact debug view of a raw result list: rank, chunk identity, and
    whichever score field that method actually produced — left in its
    NATIVE scale (raw distance / bm25_score / rrf_score / rerank_score),
    not normalized. Seeing the real, incomparable scales side by side is
    the purpose of this debug view. Distance normalization still
    happens downstream in build_retrieval_response for confidence, but
    hiding the raw numbers here would defeat the purpose of this endpoint.
    """

    formatted = []

    for rank, result in enumerate(raw_results, start=1):

        score_field = next(
            (
                key for key in (
                    "rerank_score", "rrf_score", "bm25_score", "distance"
                )
                if key in result
            ),
            None
        )

        formatted.append({
            "rank": rank,
            "chunk_id": result["chunk_id"],
            "document_name": result["document_name"],
            "page_number": result.get("page_number"),
            "score_type": score_field,
            "score": round(result[score_field], 4) if score_field is not None else None,
            "chunk_preview": result["chunk"][:200]
        })

    return formatted


@router.get("/debug/retrieval")
def debug_retrieval(
    query: str,
    document_name: str | None = None,
    rewritten_query: str | None = None,
    current_user: dict = Depends(require_admin)
):
    """
    Admin-facing view of retrieval internals for a single query — shows
    what each retrieval method actually returned and why /ask would have
    landed on the confidence level it did.

    Mirrors ask.py's real path exactly: rewrite -> hybrid(pool=10) ->
    rerank(top=5) -> confidence. semantic and bm25 are also run standalone
    (top=5 each) purely for comparison, so you can see whether a given
    answer came from BM25 catching an exact code, semantic catching a
    paraphrase, or genuinely needed both.

    rewrite_query() calls Gemini and is NOT deterministic — two calls with
    the same original query can produce two different rewrites, which then
    cascade into different retrieval results and different confidence
    scores. That means this endpoint, on its own, can't reliably reproduce
    a SPECIFIC past /ask response just by re-submitting the same original
    query. To actually debug a past /ask answer: pull that request's
    "rewritten_query" from history.json and
    pass it in via the optional rewritten_query param below — that skips
    the live rewrite entirely and replays retrieval exactly as it happened
    that time. Omit it to explore a query fresh instead.

    NOTE: hybrid_search is called ONCE with top_k=10 and reused for both
    the "hybrid_rrf" display (first 5) and as the reranker's input pool.
    RRF's ranking only depends on candidate_pool_size, not top_k, so the
    top 5 of a top-10 fetch are identical to a top-5 fetch — calling it
    twice would just be two redundant FAISS + BM25 round trips for the
    same answer.
    """

    try:

        log_info(f"[debug] Retrieval debug requested for: {query}")

        if rewritten_query is not None and rewritten_query.strip():

            search_query = rewritten_query.strip()

            rewrite_source = "supplied"

            log_info(
                f"[debug] Using supplied rewritten_query (skipping live "
                f"rewrite): {search_query}"
            )

        else:

            search_query = rewrite_query(query)

            rewrite_source = "live"

        semantic_results, _ = search_similar_chunks(
            search_query,
            document_name=document_name,
            top_k=DEBUG_TOP_K
        )

        bm25_results = search_bm25(
            search_query,
            top_k=DEBUG_TOP_K,
            document_name=document_name
        )

        hybrid_pool = hybrid_search(
            search_query,
            top_k=CANDIDATE_POOL_SIZE,
            candidate_pool_size=CANDIDATE_POOL_SIZE,
            document_name=document_name
        )

        reranked_results = rerank(search_query, hybrid_pool, top_k=DEBUG_TOP_K)

        normalized = build_retrieval_response(search_query, reranked_results)
        normalized_results = [chunk.dict() for chunk in normalized.results]

        confidence_info = calculate_confidence(normalized_results)

        log_info(
            f"[debug] confidence={confidence_info['confidence']} "
            f"top_score={confidence_info['top_score']}"
        )

        return {
            "original_query": query,
            "rewritten_query": search_query,
            "rewrite_source": rewrite_source,
            "query_was_rewritten": search_query.strip().lower() != query.strip().lower(),
            "methods": {
                "semantic": _format_results(semantic_results),
                "bm25": _format_results(bm25_results),
                "hybrid_rrf": _format_results(hybrid_pool[:DEBUG_TOP_K]),
                "hybrid_reranked": _format_results(reranked_results)
            },
            "final_confidence": confidence_info
        }

    except Exception as e:

        log_error(f"[debug] Retrieval debug failed: {e}")

        raise HTTPException(
            status_code=500,
            detail="Unable to run retrieval debug."
        )