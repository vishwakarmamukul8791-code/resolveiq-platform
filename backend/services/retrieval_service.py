from backend.services.embedding_service import generate_embeddings
from backend.services.faiss_service import load_faiss_index
from backend.services.vector_store import load_metadata
from backend.config import TOP_K

def search_similar_chunks(
    query,
    document_name=None
):

    query_embedding = generate_embeddings(
        [query]
    )

    index = load_faiss_index()

    distances, indices = index.search(
    query_embedding,
    TOP_K
)

    metadata = load_metadata()

    results = []

    for idx, distance in zip(indices[0], distances[0]):

        if idx >= len(metadata):
            continue

        chunk = metadata[idx]

        if document_name is not None:
            if chunk["document_name"] != document_name:
                continue

        result = chunk.copy()
        result["distance"] = float(distance)

        results.append(result)

    return results

def get_context(results):

    context = ""

    for result in results:

        context += result["chunk"]
        context += "\n\n"

    return context