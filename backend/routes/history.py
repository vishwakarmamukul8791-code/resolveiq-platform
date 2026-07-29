from fastapi import APIRouter, HTTPException, Depends

from backend.services.logging_service import log_info, log_error
from backend.services.history_service import get_user_history, toggle_pin
from backend.services.auth_service import get_current_user

router = APIRouter()


@router.get("/history")
def get_history(current_user: dict = Depends(get_current_user)):
    """
    Returns ONLY the calling user's own investigations, most recent first.
    username comes from the JWT, never from a query param — an engineer
    cannot pass someone else's username to see their history.

    Admin cross-engineer visibility is a separate endpoint:
    GET /admin/history/{username} in admin.py.
    """

    history = get_user_history(current_user["username"])

    return {
        "total_chats": len(history),
        "history": history
    }


@router.patch("/history/{entry_id}/pin")
def pin_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    """
    Toggles the pinned flag on one of the caller's own investigations.
    Ownership is checked in history_service.toggle_pin — if the entry
    belongs to someone else, this returns 404, not someone else's data.
    """

    try:

        updated = toggle_pin(entry_id, current_user["username"])

        if updated is None:
            raise HTTPException(status_code=404, detail="Investigation not found.")

        log_info(f"Pin toggled: {entry_id} -> {updated['pinned']} by {current_user['username']}")

        return {"id": updated["id"], "pinned": updated["pinned"]}

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Pin toggle failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pin status.")