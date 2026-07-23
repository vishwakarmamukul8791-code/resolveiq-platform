from backend.services.retrieval_service import search_similar_chunks
from backend.services.bm25_service import search_bm25

RRF_CONSTANT = 60


def reciprocal_rank_fusion(semantic_results, bm25_results, top_k=5):

    scores = {}
    chunk_lookup = {}

    for rank, result in enumerate(semantic_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (RRF_CONSTANT + rank)
        chunk_lookup[chunk_id] = result

    for rank, result in enumerate(bm25_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (RRF_CONSTANT + rank)
        chunk_lookup[chunk_id] = result

    fused = []

    for chunk_id, score in scores.items():
        entry = chunk_lookup[chunk_id].copy()
        entry["rrf_score"] = score
        fused.append(entry)

    fused.sort(key=lambda x: x["rrf_score"], reverse=True)

    return fused[:top_k]


def hybrid_search(query, top_k=5, candidate_pool_size=10, document_name=None):

    semantic_results, _ = search_similar_chunks(
        query,
        document_name=document_name,
        top_k=candidate_pool_size
    )

    bm25_results = search_bm25(
        query,
        top_k=candidate_pool_size,
        document_name=document_name
    )

    return reciprocal_rank_fusion(semantic_results, bm25_results, top_k=top_k)