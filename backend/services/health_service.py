import os

from backend.services.document_registry import load_registry
from backend.services.document_registry import REGISTRY_PATH
from backend.services.faiss_service import load_faiss_index
from backend.services.logging_service import log_error
from backend.services.storage_paths import DATA_DIR
from backend.services.vector_store import METADATA_PATH, load_metadata


def get_health_status():
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
        health["faiss_index"] == "Loaded",
        health["metadata"] == "Loaded",
        health["registry"] == "Loaded",
        health["index_consistency"] == "In sync",
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
