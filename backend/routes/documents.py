from fastapi import APIRouter, Depends

from backend.services.auth_service import get_current_user
from backend.services.document_registry import (
    load_registry
)

router = APIRouter()


@router.get("/documents")
def get_documents(current_user: dict = Depends(get_current_user)):

    registry = load_registry()

    return {
        "total_documents": len(registry),
        "documents": registry
    }