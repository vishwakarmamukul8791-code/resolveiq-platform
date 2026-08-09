import numpy as np

from backend.config import TOP_K
from backend.services.embedding_service import generate_embeddings
from backend.services.faiss_service import load_faiss_index
from backend.services.persistence_config import is_supabase_backend
from backend.services.reindex_service import rebuild_index
from backend.services.vector_store import load_metadata


def _search_index(index, query_embedding, top_k):
    search_count = min(top_k, index.ntotal)

    distances, indices = index.search(
        query_embedding,
        search_count
    )

    return [
        (int(idx), float(distance))
        for idx, distance in zip(indices[0], distances[0])
        if idx >= 0
    ]


def _search_scoped(
    index,
    query_embedding,
    metadata,
    allowed_names,
    top_k
):
    """
    Restrict vectors to the allowed document name(s) before calculating
    top-k. Local FAISS positions are mapped back to global metadata
    positions. allowed_names is a set — this covers both the
    single-document scope (ask.py's document_name filter) and a
    multi-document allow-list (guest.py) with the same code path.
    """
    global_metadata_indices = [
        index_position
        for index_position, record in enumerate(metadata)
        if record["document_name"] in allowed_names
    ]

    if not global_metadata_indices:
        return []

    scoped_vectors = np.vstack([
        index.reconstruct(index_position)
        for index_position in global_metadata_indices
    ])

    scoped_vectors = np.ascontiguousarray(
        scoped_vectors,
        dtype="float32"
    )

    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError(
            "Local retrieval requires the faiss-cpu package."
        ) from exc

    scoped_index = faiss.IndexFlatL2(index.d)
    scoped_index.add(scoped_vectors)

    local_matches = _search_index(
        scoped_index,
        query_embedding,
        top_k
    )

    return [
        (
            global_metadata_indices[local_index],
            distance
        )
        for local_index, distance in local_matches
    ]


def search_similar_chunks(
    query,
    document_name=None,
    document_names=None,
    top_k=None
):
    if top_k is None:
        top_k = TOP_K

    if top_k <= 0:
        return [], []

    if document_names is not None and not document_names:
        # An explicit empty allow-list means nothing is visible —
        # short-circuit rather than run an unscoped search.
        return [], []

    if is_supabase_backend():
        from backend.services.pgvector_service import search_pgvector

        query_embedding = np.ascontiguousarray(
            generate_embeddings([query]),
            dtype="float32",
        )

        return search_pgvector(
            query_embedding,
            top_k=top_k,
            document_name=document_name,
            document_names=document_names,
        )

    metadata = load_metadata()

    if not metadata:
        return [], []

    allowed_names = None

    if document_names is not None:
        allowed_names = set(document_names)
    elif document_name is not None:
        allowed_names = {document_name}

    # Avoid embedding generation for a nonexistent/empty document scope.
    if allowed_names is not None:
        scope_has_matches = any(
            record["document_name"] in allowed_names
            for record in metadata
        )

        if not scope_has_matches:
            return [], []

    index = load_faiss_index()

    if index is None or index.ntotal != len(metadata):
        index = rebuild_index()

    if index is None:
        return [], []

    if index.ntotal != len(metadata):
        raise RuntimeError(
            "Unable to restore FAISS/metadata consistency: "
            f"vectors={index.ntotal}, metadata={len(metadata)}"
        )

    query_embedding = np.ascontiguousarray(
        generate_embeddings([query]),
        dtype="float32"
    )

    if (
        query_embedding.ndim != 2
        or query_embedding.shape[0] != 1
        or query_embedding.shape[1] != index.d
    ):
        raise RuntimeError(
            "Query embedding dimension does not match FAISS index."
        )

    if allowed_names is None:
        matches = _search_index(
            index,
            query_embedding,
            top_k
        )
    else:
        matches = _search_scoped(
            index,
            query_embedding,
            metadata,
            allowed_names,
            top_k
        )

    results = []
    valid_distances = []

    for metadata_index, distance in matches:
        if metadata_index >= len(metadata):
            continue

        result = metadata[metadata_index].copy()
        result["distance"] = distance

        results.append(result)
        valid_distances.append(distance)

    return results, valid_distances


def get_context(results):
    return "\n\n".join(
        result["chunk"]
        for result in results
    )
