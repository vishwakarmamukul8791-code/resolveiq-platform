import os

from backend.services.faiss_service import load_faiss_index
from backend.services.vector_store import load_metadata
from backend.services.document_registry import load_registry
from backend.services.logging_service import (
    log_info,
    log_error
)

def get_health_status():

    health = {}

    # FAISS
    try:
        load_faiss_index()
        health["faiss_index"] = "Loaded"
    except Exception as e:
        log_error(str(e))
        health["faiss_index"] = "Missing"

    # Metadata
    try:
        load_metadata()
        health["metadata"] = "Loaded"
    except Exception as e:
        log_error(str(e))
        health["metadata"] = "Missing"

    # Registry
    try:
        load_registry()
        health["registry"] = "Loaded"
    except Exception as e:
        log_error(str(e))
        health["registry"] = "Missing"

    # Gemini API
    if os.getenv("GEMINI_API_KEY"):
        health["gemini_api"] = "Configured"
    else:
        health["gemini_api"] = "Missing"


    # JWT secret (required for auth)
    if os.getenv("JWT_SECRET_KEY"):
        health["jwt_secret"] = "Configured"
    else:
        health["jwt_secret"] = "Missing"    

    if (
        health["faiss_index"] == "Loaded"
        and health["metadata"] == "Loaded"
        and health["registry"] == "Loaded"
        and health["gemini_api"] == "Configured"
        and health["jwt_secret"] == "Configured"   # ← this line was missing
    ):
        health["status"] = "Healthy"
    else:
        health["status"] = "Unhealthy"

    return health