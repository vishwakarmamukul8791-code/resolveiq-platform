from fastapi import APIRouter, Depends

from backend.services.auth_service import require_password_reset_complete
from backend.services.document_registry import (
    load_registry
)

router = APIRouter()


@router.get("/documents")
def get_documents(
    current_user: dict = Depends(require_password_reset_complete),
):

    registry = load_registry()

    return {
        "total_documents": len(registry),
        "documents": registry
    }
