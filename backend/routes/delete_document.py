from fastapi import APIRouter, HTTPException

from backend.services.document_registry import (
    load_registry,
    save_registry
)

from backend.services.vector_store import (
    load_metadata,
    save_metadata
)

import os
from backend.services.reindex_service import (
    rebuild_index
)

router = APIRouter()


@router.delete("/document/{filename}")
def delete_document(filename: str):

    # Delete raw file
    file_path = f"data/raw/{filename}"

    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete registry entry
    registry = load_registry()

    updated_registry = []

    for doc in registry:

        if doc["document_name"] != filename:
            updated_registry.append(doc)

    save_registry(updated_registry)

    # Delete metadata chunks
    metadata = load_metadata()

    updated_metadata = []

    for chunk in metadata:

        if chunk["document_name"] != filename:
            updated_metadata.append(chunk)

    save_metadata(updated_metadata)



    rebuild_index()
    return {
        "message": "Document deleted successfully",
        "filename": filename
    }