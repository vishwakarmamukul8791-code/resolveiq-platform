from fastapi import APIRouter

from backend.services.stats_service import (
    get_stats
)

router = APIRouter()


@router.get("/stats")
def stats():

    return get_stats()