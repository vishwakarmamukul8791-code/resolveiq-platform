import os

from fastapi import APIRouter, HTTPException
from backend.services.vector_store import load_metadata

router = APIRouter()


@router.get("/document/{filename}")
def get_document(filename: str):

    metadata = load_metadata()

    chunks = []

    for record in metadata:

        stored_filename = record["document_name"]

        if (
            stored_filename == filename or
            os.path.splitext(stored_filename)[0] == filename
        ):
            chunks.append(record)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return {
        "document_name": chunks[0]["document_name"],
        "total_chunks": len(chunks),
        "chunks": chunks
    }