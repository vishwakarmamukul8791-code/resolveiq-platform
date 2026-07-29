"""
Chat history storage — one entry per /ask call.

Every entry belongs to exactly one username (set server-side from the JWT
in ask.py, never client-supplied). All read/write access in history.py and
delete_history.py is scoped to the calling user's own username — an
engineer can only ever see or delete their own investigations.

Cross-engineer visibility for admin oversight is a SEPARATE, explicit
admin-only endpoint (GET /admin/history/{username} in admin.py) — not a
side effect of relaxing the filter here. Keeping "my own data" and "admin
oversight" as two different code paths makes the access boundary obvious
by reading the route, not something you have to infer from a query param.
"""

import json
import os

HISTORY_PATH = "data/history/chat_history.json"


def load_history():

    if not os.path.exists(HISTORY_PATH):
        return []

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError:
        return []


def save_history(history):

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)

    with open(HISTORY_PATH, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)


def get_user_history(username: str):
    """Returns only this user's entries, most recent first."""

    history = load_history()

    user_entries = [h for h in history if h.get("username") == username]

    return sorted(user_entries, key=lambda h: h["created_at"], reverse=True)


def toggle_pin(entry_id: str, username: str):
    """
    Flips the pinned flag on one entry. Ownership-checked — a user can
    only pin/unpin their OWN entries, enforced here (not just in the route)
    so the guarantee holds even if this function is called from elsewhere
    later.

    Returns the updated entry, or None if not found / not owned by username.
    """

    history = load_history()

    updated_entry = None

    for entry in history:
        if entry.get("id") == entry_id:
            if entry.get("username") != username:
                return None  # exists, but not this user's — treat as not found
            entry["pinned"] = not entry.get("pinned", False)
            updated_entry = entry

    if updated_entry is not None:
        save_history(history)

    return updated_entry


def delete_user_history(username: str):
    """Removes ALL of this user's entries, leaves everyone else's intact."""

    history = load_history()

    remaining = [h for h in history if h.get("username") != username]

    removed_count = len(history) - len(remaining)

    save_history(remaining)

    return removed_count


def delete_single_entry(entry_id: str, username: str):
    """
    Removes one entry, ownership-checked. Returns True if deleted,
    False if not found or not owned by this user.
    """

    history = load_history()

    entry = next(
        (h for h in history if h.get("id") == entry_id),
        None
    )

    if entry is None or entry.get("username") != username:
        return False

    remaining = [h for h in history if h.get("id") != entry_id]

    save_history(remaining)

    return True