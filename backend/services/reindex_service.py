from backend.services.embedding_service import generate_embeddings
from backend.services.faiss_service import (
    create_faiss_index,
    delete_faiss_index,
    save_faiss_index
)
from backend.services.vector_store import load_metadata


def build_index_from_metadata(metadata):
    """
    Build a FAISS index in memory without modifying the persisted index.
    Metadata order is preserved because FAISS position i must correspond
    exactly to metadata record i.
    """
    if not metadata:
        return None

    chunks = [record["chunk"] for record in metadata]
    embeddings = generate_embeddings(chunks)

    index = create_faiss_index(embeddings)

    if index.ntotal != len(metadata):
        raise RuntimeError(
            "FAISS/metadata count mismatch during index build: "
            f"vectors={index.ntotal}, metadata={len(metadata)}"
        )

    return index


def persist_rebuilt_index(index):
    if index is None:
        delete_faiss_index()
    else:
        save_faiss_index(index)


def rebuild_index():
    metadata = load_metadata()

    # Build completely before modifying the persisted index.
    index = build_index_from_metadata(metadata)
    persist_rebuilt_index(index)

    return index
