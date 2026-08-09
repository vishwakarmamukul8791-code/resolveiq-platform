import re
from threading import Lock

from rank_bm25 import BM25Okapi

from backend.services.vector_store import load_metadata

# ─────────────────────────────────────────────
# In-memory cache for the unscoped (whole-corpus) BM25 index.
#
# Previously search_bm25() called load_metadata() and rebuilt a fresh
# BM25Okapi (full tokenization + IDF statistics over every chunk) on
# every single call — including every /ask, /guest/ask, /search-bm25 and
# /search-hybrid request, whether or not the corpus had changed since the
# last call. That cost is O(corpus size) per request and was paid
# identically by repeat queries against an unchanged corpus.
#
# We cache the built BM25Okapi object (and the metadata order it was
# built from) keyed by a cheap "corpus signature" — a hash of the
# chunk_ids currently in metadata. If the signature matches what we
# cached last time, the corpus hasn't changed (no chunk added/removed)
# and we can safely reuse the cached index. The signature check still
# costs one load_metadata() call (unavoidable without a push-based
# invalidation hook from process.py/delete_document.py — see
# invalidate_cache() below for a cheaper opt-in path to that), but it
# skips the expensive tokenize + BM25Okapi(...) rebuild, which is the
# dominant cost at any real corpus size.
#
# Only the unscoped case (document_name=None) is cached. Document-scoped
# search (used far less often, and only ever over a single document's
# chunks — a small subset) still builds fresh each call; caching every
# possible document_name would add unbounded cache entries for little
# benefit.
# ─────────────────────────────────────────────

_cache_lock = Lock()
_cache = {
    "signature": None,
    "bm25": None,
    "metadata": None,
}


def _tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def _corpus_signature(metadata: list) -> int:
    """Cheap fingerprint that changes iff the set of chunks changed."""
    return hash(tuple(record["chunk_id"] for record in metadata))


def invalidate_cache() -> None:
    """
    Explicitly drop the cached BM25 index. Not required for correctness
    (the signature check in _get_or_build already detects any change to
    the chunk set) but cheap to call from process.py / delete_document.py
    right after a commit so the *next* search doesn't even pay for a
    metadata reload + signature hash before finding out it's stale —
    it just rebuilds immediately on next use.
    """

    with _cache_lock:
        _cache["signature"] = None
        _cache["bm25"] = None
        _cache["metadata"] = None


def _get_or_build_global_index():
    metadata = load_metadata()
    signature = _corpus_signature(metadata)

    with _cache_lock:
        if _cache["signature"] == signature and _cache["bm25"] is not None:
            return _cache["bm25"], _cache["metadata"]

        tokenized_chunks = [_tokenize(record["chunk"]) for record in metadata]
        bm25 = BM25Okapi(tokenized_chunks) if tokenized_chunks else None

        _cache["signature"] = signature
        _cache["bm25"] = bm25
        _cache["metadata"] = metadata

        return bm25, metadata


def search_bm25(
    query: str,
    top_k: int = 5,
    document_name: str = None,
    document_names=None,
):
    tokenized_query = _tokenize(query)

    if not tokenized_query:
        return []

    if document_names is not None and not document_names:
        return []

    if document_name is None and document_names is None:
        bm25, metadata = _get_or_build_global_index()

        if bm25 is None:
            return []
    else:
        if document_names is not None:
            allowed_names = set(document_names)
            metadata = [
                record for record in load_metadata()
                if record["document_name"] in allowed_names
            ]
        else:
            metadata = [
                record for record in load_metadata()
                if record["document_name"] == document_name
            ]

        if not metadata:
            return []

        tokenized_chunks = [_tokenize(record["chunk"]) for record in metadata]
        bm25 = BM25Okapi(tokenized_chunks)

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
