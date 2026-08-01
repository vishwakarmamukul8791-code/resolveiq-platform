import os

from backend.services.document_registry import load_registry
from backend.services.faiss_service import load_faiss_index
from backend.services.logging_service import log_error
from backend.services.vector_store import load_metadata


def get_health_status():
    health = {}

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
        health["faiss_index"] = "Missing"

    # Metadata store
    try:
        load_metadata()
        health["metadata"] = "Loaded"

    except Exception as exc:
        log_error(
            "Metadata health check failed: "
            f"{type(exc).__name__}"
        )
        health["metadata"] = "Missing"

    # Document registry
    try:
        load_registry()
        health["registry"] = "Loaded"

    except Exception as exc:
        log_error(
            "Registry health check failed: "
            f"{type(exc).__name__}"
        )
        health["registry"] = "Missing"

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
        health["gemini_api"] == "Configured",
        health["jwt_secret"] == "Configured",
    )

    health["status"] = (
        "Healthy"
        if all(required_states)
        else "Unhealthy"
    )

    return health