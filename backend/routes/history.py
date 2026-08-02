from fastapi import APIRouter, HTTPException, Depends

from backend.services.logging_service import log_info, log_error
from backend.services.history_service import (
    get_user_conversations,
    get_conversation_entries,
    toggle_pin_conversation
)
from backend.services.auth_service import require_password_reset_complete

router = APIRouter()


@router.get("/history")
def get_history(
    current_user: dict = Depends(require_password_reset_complete),
):
    """
    Returns ONLY the calling user's own investigations, one row per
    conversation thread (not per question) — most recently active thread
    first. username comes from the JWT, never from a query param — an
    engineer cannot pass someone else's username to see their history.

    Admin cross-engineer visibility is a separate endpoint, and stays
    message-level rather than thread-level for full audit detail:
    GET /admin/history/{username} in admin.py.
    """

    conversations = get_user_conversations(current_user["username"])

    return {
        "total_chats": len(conversations),
        "history": conversations
    }


@router.get("/history/{conversation_id}")
def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_password_reset_complete)
):
    """
    Full message list for one thread, oldest first — powers the workspace
    view when an engineer picks a past investigation from the sidebar so
    the whole conversation loads, not just its first question.
    """

    messages = get_conversation_entries(
        conversation_id,
        current_user["username"]
    )

    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return {
        "conversation_id": conversation_id,
        "messages": messages
    }


@router.patch("/history/{entry_id}/pin")
def pin_entry(
    entry_id: str,
    current_user: dict = Depends(require_password_reset_complete),
):
    """
    Toggles the pinned flag on an entire conversation thread at once.
    Ownership is checked in history_service.toggle_pin_conversation — if
    the thread belongs to someone else, this returns 404, not someone
    else's data.
    """

    try:

        new_state = toggle_pin_conversation(entry_id, current_user["username"])

        if new_state is None:
            raise HTTPException(status_code=404, detail="Investigation not found.")

        log_info(f"Pin toggled: {entry_id} -> {new_state} by {current_user['username']}")

        return {"id": entry_id, "pinned": new_state}

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Pin toggle failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pin status.")
