from fastapi import APIRouter

from backend.services.history_service import (
    load_history
)

router = APIRouter()


@router.get("/history")
def get_history():

    history = load_history()

    return {
        "total_chats": len(history),
        "history": history
    }