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

from backend.services.json_storage import (
    load_json_list,
    save_json,
    synchronized_storage,
)
from backend.services.storage_paths import data_path

HISTORY_PATH = data_path("history", "chat_history.json")


def load_history():
    return load_json_list(HISTORY_PATH)


def save_history(history):
    save_json(HISTORY_PATH, history)


@synchronized_storage(HISTORY_PATH)
def append_history(entry):
    history = load_history()
    history.append(entry)
    save_history(history)


def get_user_history(username: str):
    """Returns only this user's entries, most recent first."""

    history = load_history()

    user_entries = [h for h in history if h.get("username") == username]

    return sorted(user_entries, key=lambda h: h["created_at"], reverse=True)


def _conversation_key(entry: dict) -> str:
    """
    Groups messages into one thread. Every entry written by ask.py now
    carries a conversation_id (all messages asked in the same workspace
    session share one). Entries saved before this existed have no
    conversation_id — each of those is simply its own one-message thread,
    keyed by its own entry id, so old history keeps working unchanged.
    """

    return entry.get("conversation_id") or entry["id"]


def get_user_conversations(username: str):
    """
    One row per conversation (thread), not per question — this is what the
    sidebar lists. Title is the first question asked in the thread; the
    displayed timestamp is the most recent message, so an active thread
    sorts to the top the same way a chat app would.
    """

    entries = get_user_history(username)

    groups = {}
    order = []

    for entry in entries:
        key = _conversation_key(entry)

        if key not in groups:
            groups[key] = []
            order.append(key)

        groups[key].append(entry)

    conversations = []

    for key in order:
        messages = sorted(groups[key], key=lambda h: h["created_at"])

        conversations.append({
            "id": key,
            "question": messages[0]["question"],
            "pinned": any(m.get("pinned") for m in messages),
            "created_at": messages[-1]["created_at"],
            "message_count": len(messages)
        })

    conversations.sort(key=lambda c: c["created_at"], reverse=True)

    return conversations


def get_conversation_entries(conversation_id: str, username: str):
    """
    Full message list for one thread, oldest first (reading order),
    ownership-checked. Returns None if the thread doesn't exist or
    doesn't belong to this user — treated as 404 by the route.
    """

    history = load_history()

    matches = [
        entry for entry in history
        if entry.get("username") == username
        and _conversation_key(entry) == conversation_id
    ]

    if not matches:
        return None

    return sorted(matches, key=lambda h: h["created_at"])


@synchronized_storage(HISTORY_PATH)
def toggle_pin_conversation(conversation_id: str, username: str):
    """
    Pins/unpins an entire thread at once — every message in it gets the
    same pinned value, so the sidebar's single row for the thread reflects
    one consistent state. Returns the new pinned value, or None if the
    thread doesn't exist / isn't owned by this user.
    """

    history = load_history()

    new_state = None

    for entry in history:
        if (
            entry.get("username") == username
            and _conversation_key(entry) == conversation_id
        ):
            if new_state is None:
                new_state = not entry.get("pinned", False)
            entry["pinned"] = new_state

    if new_state is not None:
        save_history(history)

    return new_state


@synchronized_storage(HISTORY_PATH)
def delete_user_history(username: str):
    """Removes ALL of this user's entries, leaves everyone else's intact."""

    history = load_history()

    remaining = [h for h in history if h.get("username") != username]

    removed_count = len(history) - len(remaining)

    save_history(remaining)

    return removed_count


@synchronized_storage(HISTORY_PATH)
def delete_conversation(conversation_id: str, username: str):
    """
    Removes every message in one thread, ownership-checked. Returns True
    if anything was deleted, False if the thread wasn't found / not owned
    by this user.
    """

    history = load_history()

    remaining = [
        entry for entry in history
        if not (
            entry.get("username") == username
            and _conversation_key(entry) == conversation_id
        )
    ]

    removed_count = len(history) - len(remaining)

    save_history(remaining)

    return removed_count > 0
