from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.services.health_service import get_health_status

router = APIRouter()


@router.get("/health/live")
def liveness():
    """Process-only probe; external dependencies are checked by /health."""

    return {"status": "alive"}


@router.get("/health")
def health():
    """
    Returns the same health payload either way, but the HTTP status code
    now actually reflects it: 200 when every required component is
    healthy, 503 otherwise. Previously this always returned 200 even
    when `status` in the body said "Unhealthy" — automated monitors
    (Render's own healthcheck, uptime checkers, load balancers) that
    only look at the status code, not the body, would report this
    service as up even while the FAISS index was missing or the Gemini
    key was unset.
    """

    status = get_health_status()

    return JSONResponse(
        status_code=200 if status.get("status") == "Healthy" else 503,
        content=status,
    )
