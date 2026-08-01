import faiss
import numpy as np

from backend.config import TOP_K
from backend.services.embedding_service import generate_embeddings
from backend.services.faiss_service import load_faiss_index
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


def _search_document_scope(
    index,
    query_embedding,
    metadata,
    document_name,
    top_k
):
    """
    Restrict vectors to the selected document before calculating top-k.
    Local FAISS positions are mapped back to global metadata positions.
    """
    global_metadata_indices = [
        index_position
        for index_position, record in enumerate(metadata)
        if record["document_name"] == document_name
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
    top_k=None
):
    if top_k is None:
        top_k = TOP_K

    if top_k <= 0:
        return [], []

    metadata = load_metadata()

    if not metadata:
        return [], []

    # Avoid embedding generation for a nonexistent document scope.
    if document_name is not None:
        document_exists = any(
            record["document_name"] == document_name
            for record in metadata
        )

        if not document_exists:
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

    if document_name is None:
        matches = _search_index(
            index,
            query_embedding,
            top_k
        )
    else:
        matches = _search_document_scope(
            index,
            query_embedding,
            metadata,
            document_name,
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
