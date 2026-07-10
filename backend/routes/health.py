from fastapi import APIRouter

from backend.services.health_service import get_health_status

router = APIRouter()


@router.get("/health")
def health():

    return get_health_status()