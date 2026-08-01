from fastapi import APIRouter, Depends

from backend.services.auth_service import require_admin
from backend.services.retrieval_service import (
    search_similar_chunks
)
from backend.services.bm25_service import search_bm25

from backend.services.hybrid_retrieval_service import hybrid_search

from backend.services.rerank_service import rerank


from backend.services.retrieval_contract import build_retrieval_response


router = APIRouter()

# These four endpoints are evaluation/debugging baselines (see README) that
# expose raw chunk text from the knowledge base — admin-only, same as
# /debug/retrieval, not the general engineer-facing /ask path.


@router.get("/search")
def search(query: str, current_user: dict = Depends(require_admin)):

    results, distances = search_similar_chunks(query)

    return build_retrieval_response(query, results)


@router.get("/search-bm25")
def search_bm25_endpoint(query: str, current_user: dict = Depends(require_admin)):

    results = search_bm25(query)

    return build_retrieval_response(query, results)


@router.get("/search-hybrid")
def search_hybrid_endpoint(query: str, current_user: dict = Depends(require_admin)):

    results = hybrid_search(query)

    return build_retrieval_response(query, results)


@router.get("/search-reranked")
def search_reranked_endpoint(query: str, current_user: dict = Depends(require_admin)):

    candidates = hybrid_search(query, top_k=10)

    results = rerank(query, candidates, top_k=5)

    return build_retrieval_response(query, results)