"""
Session tracking for the admin analytics dashboard.

One session record is created per login. It tracks:
  - who logged in and when
  - how long they stayed (login_time -> logout_time)
  - how many questions they asked
  - confidence breakdown of those questions (High/Medium/Low)

This is what feeds:
  - GET /admin/sessions   (session log table + Excel export)
  - GET /admin/engineers  (per-engineer aggregate stats)
  - GET /admin/analytics  (confidence distribution charts)

Storage: data/sessions.json — a flat list of session records.
Sessions are stored separately from conversation history because they have
different data structures and query patterns.

The current JSON-based storage is suitable for a single local instance.
A database would be required for higher write volume, concurrency, or
multiple backend instances.
Admin needs session-level aggregates (total time, question count per
engineer) AND history-level detail (exact questions asked) as separate
API calls. Mixing them forces every query to filter/aggregate over
one bloated file instead of reading the right one directly.
"""

import uuid
from datetime import datetime, timezone

from backend.services.json_storage import (
    load_json_list,
    save_json,
    synchronized_storage,
)
from backend.services.storage_paths import data_path


SESSIONS_PATH = data_path("sessions.json")


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        # Existing production records were written as naive UTC on Render.
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def _load_sessions():
    return load_json_list(SESSIONS_PATH)


def _save_sessions(sessions):
    save_json(SESSIONS_PATH, sessions)


@synchronized_storage(SESSIONS_PATH)
def create_session(username: str) -> str:
    """
    Called by POST /auth/login on every successful login.
    Returns the session_id — stored in the JWT response so the
    frontend can pass it to /ask for per-question tracking.
    """

    sessions = _load_sessions()

    session_id = str(uuid.uuid4())

    sessions.append({
        "session_id": session_id,
        "username": username,
        "login_time": _utc_now().isoformat(),
        "logout_time": None,
        "duration_minutes": None,
        "questions_asked": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0
    })

    _save_sessions(sessions)

    return session_id


@synchronized_storage(SESSIONS_PATH)
def close_session(session_id: str, username: str) -> bool:
    """
    Called by POST /auth/logout.
    Records logout_time and calculates duration_minutes.
    """

    sessions = _load_sessions()

    found = False

    for session in sessions:
        if (
            session["session_id"] == session_id
            and session["username"] == username
        ):
            found = True

            if session.get("logout_time"):
                break

            logout_time = _utc_now()
            login_time = _parse_timestamp(session["login_time"])
            duration = (logout_time - login_time).total_seconds() / 60

            session["logout_time"] = logout_time.isoformat()
            session["duration_minutes"] = round(max(duration, 0), 1)
            break

    _save_sessions(sessions)

    return found


@synchronized_storage(SESSIONS_PATH)
def record_question(
    session_id: str,
    confidence: str,
    username: str,
) -> bool:
    """
    Called by POST /ask after every successful response.
    Increments the question counter and the appropriate confidence bucket.

    confidence is one of: "High", "Medium", "Low"
    """

    if not session_id:
        return False

    sessions = _load_sessions()

    found = False

    for session in sessions:
        if (
            session["session_id"] == session_id
            and session["username"] == username
            and not session.get("logout_time")
        ):
            found = True
            session["questions_asked"] += 1

            if confidence == "High":
                session["high_confidence"] += 1
            elif confidence == "Medium":
                session["medium_confidence"] += 1
            else:
                session["low_confidence"] += 1

            break

    _save_sessions(sessions)

    return found


def get_all_sessions(username: str = None):
    """
    Returns all sessions, optionally filtered by username.
    Used by GET /admin/sessions.
    """

    sessions = _load_sessions()

    if username:
        sessions = [s for s in sessions if s["username"] == username]

    return sorted(sessions, key=lambda s: s["login_time"], reverse=True)


def get_engineer_aggregates():
    """
    Returns per-engineer aggregate stats across all their sessions.
    Used by GET /admin/engineers to populate the employee table.

    Columns: username, total_sessions, total_questions,
             high_confidence, medium_confidence, low_confidence,
             total_minutes, last_session
    """

    sessions = _load_sessions()

    aggregates = {}

    for session in sessions:
        username = session["username"]

        if username not in aggregates:
            aggregates[username] = {
                "username": username,
                "total_sessions": 0,
                "total_questions": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "total_minutes": 0.0,
                "last_session": None
            }

        agg = aggregates[username]
        agg["total_sessions"] += 1
        agg["total_questions"] += session.get("questions_asked", 0)
        agg["high_confidence"] += session.get("high_confidence", 0)
        agg["medium_confidence"] += session.get("medium_confidence", 0)
        agg["low_confidence"] += session.get("low_confidence", 0)
        agg["total_minutes"] += session.get("duration_minutes") or 0.0

        login_time = session["login_time"]
        if agg["last_session"] is None or login_time > agg["last_session"]:
            agg["last_session"] = login_time

    for agg in aggregates.values():
        agg["total_minutes"] = round(agg["total_minutes"], 1)

    return list(aggregates.values())
