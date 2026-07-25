from fastapi import APIRouter, HTTPException   
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


app = FastAPI(title="Intelligent Incident Resolution Assistant")

# Allow the React dev server (port 5173) and any production frontend origin
# to call the API. Update origins before production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
app.include_router(debug_retrieval_router)
app.include_router(auth_router)