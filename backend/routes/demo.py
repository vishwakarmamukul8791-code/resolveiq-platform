"""Public, read-only recruiter demo metadata.

This router deliberately does *not* proxy the authenticated admin API.
It exposes only information that is safe for an unauthenticated portfolio
viewer: the explicitly allow-listed public demo document names, a sanitized
health/config snapshot, documented retrieval evaluation metrics, and a list
of capabilities that exist behind the real admin role.

Real engineer accounts, sessions, history, credentials, private document
metadata, upload/delete actions, and password-management actions remain
behind the existing authenticated admin routes.
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.services.health_service import get_health_status
from backend.services.document_registry import load_registry
from backend.services.logging_service import log_error
from backend.services.stats_service import get_stats

router = APIRouter(prefix="/demo", tags=["Public Demo"])

_TRUE_VALUES = {"1", "true", "yes"}


def _demo_enabled() -> bool:
    return os.getenv("GUEST_MODE_ENABLED", "false").strip().lower() in _TRUE_VALUES


def _allowed_documents() -> list[str]:
    raw = os.getenv("GUEST_ALLOWED_DOCUMENTS", "")
    return sorted({name.strip() for name in raw.split(",") if name.strip()})


def _require_demo() -> list[str]:
    if not _demo_enabled():
        raise HTTPException(status_code=404, detail="Not found.")

    allowed = _allowed_documents()
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail="Public demo is enabled but no demo documents are allow-listed.",
        )

    return allowed


def _available_demo_documents(allowed: list[str]) -> list[str]:
    """Return only allow-listed documents that currently exist in the registry.

    This keeps the public demo count/list synchronized with real document
    lifecycle changes while preserving the explicit public allow-list.
    A newly uploaded document is not exposed automatically; it must also be
    intentionally added to GUEST_ALLOWED_DOCUMENTS.
    """
    try:
        registry = load_registry()
    except Exception as exc:
        log_error(
            "Public demo registry snapshot failed — "
            f"type={type(exc).__name__}"
        )
        return []

    registered = {
        str(item.get("document_name", "")).strip()
        for item in registry
        if isinstance(item, dict) and item.get("document_name")
    }

    return sorted(name for name in allowed if name in registered)


def _safe_health_snapshot() -> dict:
    """Return operational state only; never configuration values or secrets."""

    try:
        raw = get_health_status()
    except Exception as exc:  # demo UI must not leak an internal error
        log_error(f"Public demo health snapshot failed — type={type(exc).__name__}")
        return {"status": "Unavailable"}

    safe_keys = (
        "status",
        "database",
        "object_storage",
        "vector_store",
        "registry",
        "index_consistency",
        "faiss_index",
        "metadata",
    )
    return {key: raw[key] for key in safe_keys if key in raw}


def _safe_retrieval_config() -> dict:
    """Expose architecture-level settings, not corpus/private-data counts."""

    try:
        raw = get_stats()
    except Exception as exc:
        log_error(f"Public demo stats snapshot failed — type={type(exc).__name__}")
        return {}

    safe_keys = (
        "embedding_model",
        "embedding_provider",
        "embedding_dimension",
        "vector_database",
        "top_k",
        "chunk_size",
        "chunk_overlap",
        "reranker_enabled",
        "query_rewrite_enabled",
    )
    return {key: raw[key] for key in safe_keys if key in raw}


@router.get("/context")
def get_public_demo_context():
    """Sanitized context used by the recruiter-facing admin preview."""

    allowed = _require_demo()
    available = _available_demo_documents(allowed)

    documents = [
        {
            "name": name,
            "type": Path(name).suffix.lstrip(".").upper() or "FILE",
            "visibility": "Public demo only",
            "status": "Available to guest RAG",
        }
        for name in available
    ]

    return {
        "mode": "public-demo-read-only",
        "documents": documents,
        "document_count": len(documents),
        "health": _safe_health_snapshot(),
        "retrieval_config": _safe_retrieval_config(),
        "evaluation_snapshot": {
            "semantic_hit_at_1": 0.905,
            "bm25_hit_at_1": 0.857,
            "hybrid_hit_at_1": 0.905,
            "hybrid_hit_at_5": 1.0,
            "label": "Documented retrieval evaluation snapshot",
        },
        "admin_capabilities": [
            {
                "name": "Engineer management",
                "description": "Create engineers, enable/disable access, and reset temporary passwords.",
                "demo_access": "Preview only",
            },
            {
                "name": "Document lifecycle",
                "description": "Upload, process, inspect, and delete knowledge-base documents.",
                "demo_access": "Public document metadata only",
            },
            {
                "name": "RAG insights",
                "description": "Confidence distribution, knowledge gaps, source usage, and retrieval evaluation.",
                "demo_access": "Sanitized evaluation preview",
            },
            {
                "name": "System health",
                "description": "Operational health and retrieval-stack configuration.",
                "demo_access": "Sanitized live status",
            },
        ],
        "security": {
            "real_admin_auth_required": True,
            "destructive_actions_enabled": False,
            "engineer_identity_exposed": False,
            "private_documents_exposed": False,
            "credentials_exposed": False,
        },
    }
