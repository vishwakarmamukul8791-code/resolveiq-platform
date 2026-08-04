from backend.services.vector_store import load_metadata
from backend.services.document_registry import load_registry
from backend.services.faiss_service import load_faiss_index
from backend.services.embedding_service import (
    EMBEDDING_DIMENSION,
    EMBEDDING_PROVIDER,
    get_embedding_model_name,
)
from backend.services.query_rewrite_service import is_query_rewrite_enabled
from backend.services.rerank_service import is_cross_encoder_enabled

from backend.config import (
    VECTOR_DATABASE,
    TOP_K,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


def get_stats():

    metadata = load_metadata()

    registry = load_registry()

    index_readable = True

    try:
        index = load_faiss_index()
        total_vectors = 0 if index is None else index.ntotal
    except Exception:
        index_readable = False
        index = None
        total_vectors = 0

    index_metadata_in_sync = (
        index_readable
        and (
            (index is None and not metadata)
            or (
                index is not None
                and index.ntotal == len(metadata)
            )
        )
    )

    stats = {

        "total_documents": len(registry),

        "total_chunks": len(metadata),

        "total_vectors": total_vectors,

        "index_metadata_in_sync": index_metadata_in_sync,

        "embedding_model": get_embedding_model_name(),

        "embedding_provider": EMBEDDING_PROVIDER,

        "embedding_dimension": EMBEDDING_DIMENSION,

        "vector_database": VECTOR_DATABASE,

        "top_k": TOP_K,

        "chunk_size": CHUNK_SIZE,

        "chunk_overlap": CHUNK_OVERLAP,

        "reranker_enabled": is_cross_encoder_enabled(),

        "query_rewrite_enabled": is_query_rewrite_enabled()

    }

    return stats
