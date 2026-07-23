from backend.services.vector_store import load_metadata
from backend.services.faiss_service import (
    create_faiss_index,
    save_faiss_index
)
from backend.services.embedding_service import generate_embeddings


def rebuild_index():

    metadata = load_metadata()

    if not metadata:
        return

    chunks = []

    for record in metadata:
        chunks.append(record["chunk"])

    embeddings = generate_embeddings(chunks)

    index = create_faiss_index(embeddings)

    save_faiss_index(index)