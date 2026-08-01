from fastapi import APIRouter, HTTPException, Depends

from backend.services.logging_service import log_info, log_error
from backend.services.history_service import delete_user_history, delete_conversation
from backend.services.auth_service import get_current_user

router = APIRouter()


@router.delete("/history")
def delete_all_history(current_user: dict = Depends(get_current_user)):
    """
    Deletes ONLY the calling user's own investigations. This used to wipe
    the entire file for every engineer — now scoped to username from the
    JWT, same ownership pattern as GET /history.
    """

    removed_count = delete_user_history(current_user["username"])

    log_info(f"History cleared: {removed_count} entries for {current_user['username']}")

    return {"message": f"Deleted {removed_count} investigation(s) from your history."}


@router.delete("/history/{entry_id}")
def delete_one_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes an entire conversation thread (all its messages), ownership-checked."""

    try:

        deleted = delete_conversation(entry_id, current_user["username"])

        if not deleted:
            raise HTTPException(status_code=404, detail="Investigation not found.")

        log_info(f"Conversation deleted: {entry_id} by {current_user['username']}")

        return {"message": "Investigation deleted."}

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Delete entry failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete investigation.")