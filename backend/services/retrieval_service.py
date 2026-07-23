from backend.services.embedding_service import generate_embeddings
from backend.services.faiss_service import load_faiss_index
from backend.services.vector_store import load_metadata
from backend.config import TOP_K


def search_similar_chunks(
    query,
    document_name=None,
    top_k=None
):

    if top_k is None:
        top_k = TOP_K

    query_embedding = generate_embeddings(
        [query]
    )

    index = load_faiss_index()

    if index is None:
        return [], []

    distances, indices = index.search(
        query_embedding,
        top_k
    )

    metadata = load_metadata()

    results = []
    valid_distances = []

    for idx, distance in zip(
        indices[0],
        distances[0]
    ):

        if idx < 0:
            continue

        if idx >= len(metadata):
            continue

        chunk = metadata[idx]

        if document_name is not None:

            if chunk["document_name"] != document_name:
                continue

        result = chunk.copy()

        result["distance"] = float(distance)

        results.append(result)

        valid_distances.append(
            float(distance)
        )

    return results, valid_distances


def get_context(results):

    context = ""

    for result in results:

        context += result["chunk"]

        context += "\n\n"

    return context