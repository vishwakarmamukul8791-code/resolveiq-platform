from backend.services.vector_store import load_metadata
from backend.services.document_registry import load_registry
from backend.services.faiss_service import load_faiss_index

from backend.config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    VECTOR_DATABASE,
    TOP_K,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


def get_stats():

    metadata = load_metadata()

    registry = load_registry()

    try:
        index = load_faiss_index()
        total_vectors = index.ntotal
    except Exception:
        total_vectors = 0

    stats = {

        "total_documents": len(registry),

        "total_chunks": len(metadata),

        "total_vectors": total_vectors,

        "index_metadata_in_sync": total_vectors == len(metadata),

        "embedding_model": EMBEDDING_MODEL,

        "embedding_dimension": EMBEDDING_DIMENSION,

        "vector_database": VECTOR_DATABASE,

        "top_k": TOP_K,

        "chunk_size": CHUNK_SIZE,

        "chunk_overlap": CHUNK_OVERLAP

    }

    return stats