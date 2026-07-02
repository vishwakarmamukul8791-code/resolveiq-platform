from fastapi import APIRouter, HTTPException
from backend.services.embedding_service import generate_embeddings
from backend.services.vector_store import (
    save_metadata,
    load_metadata
)
from backend.services.faiss_service import (
    add_embeddings_to_index
)
from backend.services.hash_service import (
    generate_file_hash
)
from backend.services.document_registry import (
    load_registry,
    save_registry
)
from backend.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP
)

import os
import uuid

router = APIRouter()


def create_chunks(text):

    chunks = []

    start = 0

    while start < len(text):

        end = start + CHUNK_SIZE

        chunks.append(
            text[start:end]
        )

        start += (
            CHUNK_SIZE - CHUNK_OVERLAP
        )

    return chunks


@router.post("/process-document")
def process_document(filename: str):

    file_path = f"data/raw/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # Duplicate check using hash
    file_hash = generate_file_hash(
        file_path
    )

    registry = load_registry()

    for document in registry:

        if document["hash"] == file_hash:

            return {
                "message": "Document already exists",
                "filename": filename
            }

    # Read file
    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()

    # Chunking
    chunks = create_chunks(content)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No content found in file"
        )

    # Load existing metadata
    existing_metadata = load_metadata()

    # Save chunk metadata
    for chunk in chunks:

        existing_metadata.append({
            "chunk_id": str(uuid.uuid4()),
            "document_name": filename,
            "chunk": chunk
        })

    save_metadata(
        existing_metadata
    )

    # Generate embeddings
    embeddings = generate_embeddings(
        chunks
    )

    # Save vectors to FAISS
    index = add_embeddings_to_index(
        embeddings
    )

    # Save hash to registry
    registry.append({
        "document_name": filename,
        "hash": file_hash
    })

    save_registry(
        registry
    )

    return {
        "filename": filename,
        "total_chunks": len(chunks),
        "embedding_dimension": len(embeddings[0]),
        "metadata_records": len(existing_metadata),
        "total_vectors": index.ntotal
    }