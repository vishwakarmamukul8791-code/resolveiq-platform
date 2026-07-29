"""
Admin-only routes. Every endpoint here requires Depends(require_admin).

Covers:
  - Engineer account management (create, list, enable/disable, reset password)
  - Session log (for the activity table + Excel export)
  - Analytics (per-engineer stats, confidence breakdown, knowledge gaps)
  - Source analytics (which documents are cited most)
"""

from collections import Counter
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.services.logging_service import log_info, log_error
from backend.services.auth_service import (
    require_admin,
    create_user,
    list_engineers,
    set_active_status,
    admin_reset_password,
    get_user
)
from backend.services.session_service import (
    get_all_sessions,
    get_engineer_aggregates
)
from backend.services.history_service import load_history, get_user_history

import secrets

router = APIRouter(prefix="/admin", tags=["Admin"])

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_engineer_only_history():
    """
    Returns history entries authored by engineers only — excludes any
    questions asked by admin accounts.

    Why this matters: admin can log in and use /ask too (useful for
    testing/verifying the system), but those test queries shouldn't
    pollute the analytics that are meant to reflect actual engineer
    productivity and real knowledge gaps. Filtering here, once, in a
    shared helper — not duplicated per endpoint — means the exclusion
    rule lives in exactly one place.
    """

    engineer_usernames = {e["username"] for e in list_engineers()}

    history = load_history()

    return [h for h in history if h.get("username") in engineer_usernames]


class CreateEngineerRequest(BaseModel):
    username: str
    full_name: str | None = None


class SetActiveRequest(BaseModel):
    username: str
    is_active: bool


class ResetPasswordRequest(BaseModel):
    username: str


@router.post("/create-engineer")
def create_engineer(
    payload: CreateEngineerRequest,
    current_user: dict = Depends(require_admin)
):
    try:
        temp_password = secrets.token_urlsafe(12)

        create_user(payload.username, temp_password, role="engineer")

        log_info(f"Engineer created: {payload.username} by admin={current_user['username']}")

        return {
            "username": payload.username,
            "temp_password": temp_password,
            "message": (
                f"Account created. Share this temporary password with "
                f"{payload.username} — it will not be shown again."
            )
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_error(f"Create engineer failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create engineer account.")


@router.get("/engineers")
def get_engineers(current_user: dict = Depends(require_admin)):
    try:
        engineers = list_engineers()

        aggregates = {
            agg["username"]: agg
            for agg in get_engineer_aggregates()
        }

        result = []

        for eng in engineers:
            agg = aggregates.get(eng["username"], {})

            result.append({
                "username": eng["username"],
                "role": eng["role"],
                "is_active": eng["is_active"],
                "must_reset_password": eng["must_reset_password"],
                "created_at": eng["created_at"],
                "last_login": eng["last_login"],
                "total_sessions": agg.get("total_sessions", 0),
                "total_questions": agg.get("total_questions", 0),
                "high_confidence": agg.get("high_confidence", 0),
                "medium_confidence": agg.get("medium_confidence", 0),
                "low_confidence": agg.get("low_confidence", 0),
                "total_minutes": agg.get("total_minutes", 0.0)
            })

        return {"engineers": result, "total": len(result)}

    except Exception as e:
        log_error(f"Get engineers failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve engineers.")


@router.post("/set-active")
def set_engineer_active(
    payload: SetActiveRequest,
    current_user: dict = Depends(require_admin)
):
    try:
        set_active_status(payload.username, payload.is_active)

        action = "enabled" if payload.is_active else "disabled"

        log_info(f"Account {action}: {payload.username} by admin={current_user['username']}")

        return {
            "username": payload.username,
            "is_active": payload.is_active,
            "message": f"Account {action} successfully."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_error(f"Set active failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update account status.")


@router.post("/reset-engineer-password")
def reset_engineer_password(
    payload: ResetPasswordRequest,
    current_user: dict = Depends(require_admin)
):
    try:
        new_temp = admin_reset_password(payload.username)

        log_info(f"Password reset for: {payload.username} by admin={current_user['username']}")

        return {
            "username": payload.username,
            "temp_password": new_temp,
            "message": (
                f"Password reset. Share this temporary password with "
                f"{payload.username} — it will not be shown again."
            )
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_error(f"Password reset failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password.")


@router.get("/sessions")
def get_sessions(
    username: str | None = None,
    current_user: dict = Depends(require_admin)
):
    try:
        sessions = get_all_sessions(username=username)
        return {"sessions": sessions, "total": len(sessions)}

    except Exception as e:
        log_error(f"Get sessions failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions.")


@router.get("/analytics")
def get_analytics(current_user: dict = Depends(require_admin)):
    """
    Platform-wide analytics for the AI Usage Analytics tab.
    Admin-authored test queries are excluded — see _get_engineer_only_history().
    """

    try:
        history = _get_engineer_only_history()

        total = len(history)

        if total == 0:
            return {
                "total_questions": 0,
                "confidence_distribution": {"High": 0, "Medium": 0, "Low": 0},
                "corpus_coverage_score": None,
                "per_engineer": []
            }

        confidence_counts = Counter(
            h.get("confidence", "Low") for h in history
        )

        high = confidence_counts.get("High", 0)
        medium = confidence_counts.get("Medium", 0)
        low = confidence_counts.get("Low", 0)

        corpus_coverage_score = round(high / total * 100, 1) if total > 0 else 0

        per_engineer_counter = Counter(
            h.get("username", "unknown") for h in history
        )

        per_engineer = [
            {"username": username, "questions": count}
            for username, count in per_engineer_counter.most_common()
        ]

        return {
            "total_questions": total,
            "confidence_distribution": {
                "High": high,
                "Medium": medium,
                "Low": low,
                "High_pct": round(high / total * 100, 1),
                "Medium_pct": round(medium / total * 100, 1),
                "Low_pct": round(low / total * 100, 1)
            },
            "corpus_coverage_score": corpus_coverage_score,
            "per_engineer": per_engineer
        }

    except Exception as e:
        log_error(f"Analytics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics.")


@router.get("/knowledge-gaps")
def get_knowledge_gaps(current_user: dict = Depends(require_admin)):
    """
    Knowledge Gap Tracker — Low-confidence queries grouped and counted.
    Admin-authored test queries are excluded.
    """

    try:
        history = _get_engineer_only_history()

        low_confidence_questions = [
            h["question"]
            for h in history
            if h.get("confidence") == "Low"
        ]

        total_low = len(low_confidence_questions)
        total_questions = len(history)

        gap_counter = Counter(low_confidence_questions)

        gaps = [
            {"question": question, "count": count}
            for question, count in gap_counter.most_common(20)
        ]

        return {
            "total_unanswered": total_low,
            "total_questions": total_questions,
            "unanswered_rate": round(total_low / total_questions * 100, 1) if total_questions > 0 else 0,
            "top_gaps": gaps
        }

    except Exception as e:
        log_error(f"Knowledge gaps failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge gaps.")


@router.get("/source-analytics")
def get_source_analytics(current_user: dict = Depends(require_admin)):
    """
    Which documents are cited most in answers.
    Admin-authored test queries are excluded.
    """

    try:
        history = _get_engineer_only_history()

        all_sources = []

        for h in history:
            sources = h.get("sources", [])
            if isinstance(sources, list):
                all_sources.extend(sources)

        source_counter = Counter(all_sources)

        total_citations = sum(source_counter.values())

        source_analytics = [
            {
                "document_name": doc,
                "citations": count,
                "citation_pct": round(count / total_citations * 100, 1) if total_citations > 0 else 0
            }
            for doc, count in source_counter.most_common()
        ]

        return {
            "total_citations": total_citations,
            "sources": source_analytics
        }

    except Exception as e:
        log_error(f"Source analytics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve source analytics.")


@router.get("/system-health")
def get_system_health(current_user: dict = Depends(require_admin)):
    try:
        from backend.services.health_service import get_health
        from backend.services.stats_service import get_stats

        return {
            "health": get_health(),
            "stats": get_stats()
        }

    except Exception as e:
        log_error(f"System health failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health.")


@router.get("/history/{username}")
def get_engineer_history(username: str, current_user: dict = Depends(require_admin)):
    """
    Admin views one engineer's full investigation transcript.
    """

    try:
        history = get_user_history(username)

        return {
            "username": username,
            "total_chats": len(history),
            "history": history
        }

    except Exception as e:
        log_error(f"Get engineer history failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history.")