from fastapi import FastAPI
from backend.routes.upload import router as upload_router
from backend.routes.process import router as process_router
from backend.routes.search import router as search_router
from backend.routes.ask import router as ask_router
from backend.routes.documents import (
    router as documents_router
)

from backend.routes.document_details import (
    router as document_details_router
)

from backend.routes.delete_document import (
    router as delete_document_router
)

from backend.routes.history import (
    router as history_router
)

from backend.routes.delete_history import (
    router as delete_history_router
)



app = FastAPI()
app.include_router(upload_router)
app.include_router(process_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(documents_router)
app.include_router(document_details_router)
app.include_router( delete_document_router)
app.include_router(history_router)
app.include_router(delete_history_router)


# @app.get("/")
# def home():
#     return {"message": "Incident Resolution Assistant Running"}