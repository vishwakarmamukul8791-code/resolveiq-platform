import os

from backend.services.document_registry import load_registry
from backend.services.document_registry import REGISTRY_PATH
from backend.services.faiss_service import load_faiss_index
from backend.services.logging_service import log_error
from backend.services.persistence_config import is_supabase_backend
from backend.services.storage_paths import DATA_DIR
from backend.services.vector_store import METADATA_PATH, load_metadata


def get_health_status():
    if is_supabase_backend():
        return _get_supabase_health_status()

    health = {}
    index = None
    metadata = None

    # FAISS index
    try:
        index = load_faiss_index()

        health["faiss_index"] = (
            "Loaded"
            if index is not None
            else "Missing"
        )

    except Exception as exc:
        log_error(
            "FAISS health check failed: "
            f"{type(exc).__name__}"
        )
        health["faiss_index"] = "Corrupt"

    # Metadata store
    try:
        if not METADATA_PATH.is_file():
            health["metadata"] = "Missing"
        else:
            metadata = load_metadata()
            health["metadata"] = "Loaded"

    except Exception as exc:
        log_error(
            "Metadata health check failed: "
            f"{type(exc).__name__}"
        )
        health["metadata"] = "Corrupt"

    # Document registry
    try:
        if not REGISTRY_PATH.is_file():
            health["registry"] = "Missing"
        else:
            load_registry()
            health["registry"] = "Loaded"

    except Exception as exc:
        log_error(
            "Registry health check failed: "
            f"{type(exc).__name__}"
        )
        health["registry"] = "Corrupt"

    if index is not None and metadata is not None:
        health["index_consistency"] = (
            "In sync"
            if index.ntotal == len(metadata)
            else "Out of sync"
        )
    else:
        health["index_consistency"] = "Unknown"

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        health["data_directory"] = (
            "Writable"
            if os.access(DATA_DIR, os.W_OK)
            else "Read only"
        )
    except OSError:
        health["data_directory"] = "Unavailable"

    # Required configuration
    health["gemini_api"] = (
        "Configured"
        if os.getenv("GEMINI_API_KEY")
        else "Missing"
    )

    health["jwt_secret"] = (
        "Configured"
        if os.getenv("JWT_SECRET_KEY")
        else "Missing"
    )

    required_states = (
        # A brand-new deployment with zero documents processed yet has
        # no FAISS index or metadata file — that's "Missing", which is
        # a perfectly valid, healthy state, not a failure. Only "Corrupt"
        # (a real read/parse error) should ever fail health. Same logic
        # for index_consistency: "Unknown" just means there's nothing to
        # compare yet (fresh install); only an actual mismatch between
        # an existing index and existing metadata ("Out of sync") is a
        # real problem.
        health["faiss_index"] != "Corrupt",
        health["metadata"] != "Corrupt",
        health["registry"] != "Corrupt",
        health["index_consistency"] != "Out of sync",
        health["data_directory"] == "Writable",
        health["gemini_api"] == "Configured",
        health["jwt_secret"] == "Configured",
    )

    health["status"] = (
        "Healthy"
        if all(required_states)
        else "Unhealthy"
    )

    return health


def _get_supabase_health_status():
    from backend.services.database_service import database_is_reachable
    from backend.services.pgvector_service import count_chunks

    health = {}
    database_ready = database_is_reachable()

    health["database"] = (
        "Connected" if database_ready else "Unavailable"
    )
    health["object_storage"] = (
        "Configured"
        if (
            os.getenv("SUPABASE_URL")
            and os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            and os.getenv(
                "SUPABASE_STORAGE_BUCKET",
                "resolveiq-documents",
            )
        )
        else "Missing"
    )

    if database_ready:
        try:
            # A lightweight count(*) confirms the chunks table is
            # reachable and readable without transferring every chunk's
            # text over the network. Embeddings live in the same row as
            # their chunk metadata in Supabase mode (unlike local FAISS
            # mode, where a genuinely separate index file can drift out
            # of sync with metadata.json), so there's no independent
            # "vector count" to compare this against — the two can't
            # drift apart, they're the same table.
            count_chunks()
            load_registry()
            health["vector_store"] = "Loaded"
            health["registry"] = "Loaded"
            health["index_consistency"] = "In sync"
        except Exception as exc:
            log_error(
                "Supabase persistence health check failed: "
                f"{type(exc).__name__}"
            )
            health["vector_store"] = "Unavailable"
            health["registry"] = "Unavailable"
            health["index_consistency"] = "Unknown"
    else:
        health["vector_store"] = "Unavailable"
        health["registry"] = "Unavailable"
        health["index_consistency"] = "Unknown"

    health["gemini_api"] = (
        "Configured" if os.getenv("GEMINI_API_KEY") else "Missing"
    )
    health["jwt_secret"] = (
        "Configured" if os.getenv("JWT_SECRET_KEY") else "Missing"
    )

    required_states = (
        health["database"] == "Connected",
        health["object_storage"] == "Configured",
        health["vector_store"] == "Loaded",
        health["registry"] == "Loaded",
        health["index_consistency"] == "In sync",
        health["gemini_api"] == "Configured",
        health["jwt_secret"] == "Configured",
    )
    health["status"] = "Healthy" if all(required_states) else "Unhealthy"

    return health
