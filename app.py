import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.upload import router as upload_router
from backend.routes.process import router as process_router
from backend.routes.search import router as search_router
from backend.routes.ask import router as ask_router
from backend.routes.documents import router as documents_router
from backend.routes.document_details import router as document_details_router
from backend.routes.delete_document import router as delete_document_router
from backend.routes.history import router as history_router
from backend.routes.delete_history import router as delete_history_router
from backend.routes.stats import router as stats_router
from backend.routes.health import router as health_router
from backend.routes.debug_retrieval import router as debug_retrieval_router
from backend.routes.auth import router as auth_router
from backend.routes.admin import router as admin_router
from backend.services.auth_service import bootstrap_admin_from_env

is_production = (
    os.getenv("ENVIRONMENT", "development").strip().lower()
    == "production"
)

enable_debug_routes = (
    os.getenv("ENABLE_DEBUG_ROUTES", "false").strip().lower()
    in {"1", "true", "yes"}
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_admin_from_env()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="ResolveIQ — AI-Powered Incident Resolution Platform",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# Allow the React dev server (port 5173) plus any deployed frontend origin(s)
# supplied via FRONTEND_ORIGIN, e.g.:
#   FRONTEND_ORIGIN=https://resolveiq.yourdomain.com
# Comma-separate multiple origins if you deploy more than one frontend.
_extra_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "").split(",")
    if origin.strip()
]

_local_origins = [] if is_production else [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *_local_origins,
        *_extra_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(process_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(documents_router)
app.include_router(document_details_router)
app.include_router(delete_document_router)
app.include_router(history_router)
app.include_router(delete_history_router)
app.include_router(stats_router)
app.include_router(health_router)
if enable_debug_routes and not is_production:
    app.include_router(debug_retrieval_router)
app.include_router(auth_router)
app.include_router(admin_router)
