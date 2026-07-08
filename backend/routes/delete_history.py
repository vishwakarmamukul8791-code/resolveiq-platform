from fastapi import APIRouter
from backend.services.history_service import (
    save_history
)

router = APIRouter()


@router.delete("/history")
def delete_history():

    save_history([])

    return {
        "message": "Chat history deleted successfully"
    }