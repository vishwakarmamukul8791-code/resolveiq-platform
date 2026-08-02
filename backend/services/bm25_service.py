import re
from rank_bm25 import BM25Okapi

from backend.services.vector_store import load_metadata


def _tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def search_bm25(query: str, top_k: int = 5, document_name: str = None):

    metadata = load_metadata()

    if document_name is not None:
        metadata = [
            record for record in metadata
            if record["document_name"] == document_name
        ]

    if not metadata:
        return []

    tokenized_chunks = [
        _tokenize(record["chunk"]) for record in metadata
    ]

    bm25 = BM25Okapi(tokenized_chunks)

    tokenized_query = _tokenize(query)

    if not tokenized_query:
        return []

    scores = bm25.get_scores(tokenized_query)

    results = []

    for idx, score in enumerate(scores):

        if score <= 0:
            continue

        results.append({
            "chunk_id": metadata[idx]["chunk_id"],
            "document_name": metadata[idx]["document_name"],
            "chunk": metadata[idx]["chunk"],
            "page_number": metadata[idx].get("page_number"),
            "source_location": metadata[idx].get("source_location"),
            "bm25_score": float(score)
        })

    results.sort(key=lambda x: x["bm25_score"], reverse=True)

    return results[:top_k]
