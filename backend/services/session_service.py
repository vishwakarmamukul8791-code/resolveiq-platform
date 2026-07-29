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
No database needed at this scale. If sessions grow beyond ~50k records,
this file approach would need replacing with SQLite or Postgres.
That's a known, intentional tradeoff for the current version.

Interview answer: "Why not store sessions in the same file as history?"
Sessions and history have different shapes and different query patterns.
Admin needs session-level aggregates (total time, question count per
engineer) AND history-level detail (exact questions asked) as separate
API calls. Mixing them forces every query to filter/aggregate over
one bloated file instead of reading the right one directly.
"""

import json
import os
import uuid
from datetime import datetime

SESSIONS_PATH = "data/sessions.json"


def _load_sessions():

    if not os.path.exists(SESSIONS_PATH):
        return []

    try:
        with open(SESSIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError:
        return []


def _save_sessions(sessions):

    os.makedirs(os.path.dirname(SESSIONS_PATH), exist_ok=True)

    with open(SESSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=4)


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
        "login_time": datetime.now().isoformat(),
        "logout_time": None,
        "duration_minutes": None,
        "questions_asked": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0
    })

    _save_sessions(sessions)

    return session_id


def close_session(session_id: str):
    """
    Called by POST /auth/logout.
    Records logout_time and calculates duration_minutes.
    """

    sessions = _load_sessions()

    for session in sessions:
        if session["session_id"] == session_id:
            logout_time = datetime.now()
            login_time = datetime.fromisoformat(session["login_time"])
            duration = (logout_time - login_time).total_seconds() / 60

            session["logout_time"] = logout_time.isoformat()
            session["duration_minutes"] = round(duration, 1)

    _save_sessions(sessions)


def record_question(session_id: str, confidence: str):
    """
    Called by POST /ask after every successful response.
    Increments the question counter and the appropriate confidence bucket.

    confidence is one of: "High", "Medium", "Low"
    """

    if not session_id:
        return

    sessions = _load_sessions()

    for session in sessions:
        if session["session_id"] == session_id:
            session["questions_asked"] += 1

            if confidence == "High":
                session["high_confidence"] += 1
            elif confidence == "Medium":
                session["medium_confidence"] += 1
            else:
                session["low_confidence"] += 1

    _save_sessions(sessions)


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