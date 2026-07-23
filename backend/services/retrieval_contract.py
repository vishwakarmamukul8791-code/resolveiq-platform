from pydantic import BaseModel
from typing import Optional, List


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_name: str
    chunk: str
    page_number: Optional[int] = None
    source_location: Optional[str] = None
    relevance_score: float
    rank: int


class RetrievalResponse(BaseModel):
    query: str
    method: str
    results: List[RetrievedChunk]


def _normalize_one(raw_result: dict) -> dict:

    if "rerank_score" in raw_result:
        return {
            "relevance_score": raw_result["rerank_score"],
            "method": "reranked"
        }

    if "rrf_score" in raw_result:
        return {
            "relevance_score": raw_result["rrf_score"],
            "method": "hybrid"
        }

    if "bm25_score" in raw_result:
        return {
            "relevance_score": raw_result["bm25_score"],
            "method": "bm25"
        }

    if "distance" in raw_result:
        return {
            "relevance_score": 1 / (1 + raw_result["distance"]),
            "method": "semantic"
        }

    return {
        "relevance_score": 0.0,
        "method": "unknown"
    }


def build_retrieval_response(query: str, raw_results: list) -> RetrievalResponse:

    method = "unknown"
    chunks = []

    for rank, raw_result in enumerate(raw_results, start=1):

        normalized = _normalize_one(raw_result)

        method = normalized["method"]

        chunks.append(RetrievedChunk(
            chunk_id=raw_result["chunk_id"],
            document_name=raw_result["document_name"],
            chunk=raw_result["chunk"],
            page_number=raw_result.get("page_number"),
            source_location=raw_result.get("source_location"),
            relevance_score=normalized["relevance_score"],
            rank=rank
        ))

    return RetrievalResponse(
        query=query,
        method=method,
        results=chunks
    )