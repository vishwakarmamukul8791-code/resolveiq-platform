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
from backend.services.extraction_service import extract_text
from backend.services.cleaning_service import clean_text
from backend.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP
)
from backend.services.logging_service import (
    log_info,
    log_error
)

import os
import uuid

router = APIRouter()


def _chunk_single_text(text):

    chunks = []

    start = 0

    while start < len(text):

        end = start + CHUNK_SIZE

        chunks.append(text[start:end])

        start += (CHUNK_SIZE - CHUNK_OVERLAP)

    return chunks


def create_chunks_from_segments(segments):
    """
    Chunks each segment (page / row / full document) separately,
    so every resulting chunk keeps exactly one page_number and
    source_location. A chunk never spans two PDF pages.
    """

    all_chunks = []

    for segment in segments:

        pieces = _chunk_single_text(segment["text"])

        for piece in pieces:

            all_chunks.append({
                "chunk": piece,
                "page_number": segment["page_number"],
                "source_location": segment["source_location"]
            })

    return all_chunks


@router.post("/process-document")
def process_document(filename: str):

    file_path = f"data/raw/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    try:

        # Duplicate check using hash
        file_hash = generate_file_hash(file_path)

        registry = load_registry()

        for document in registry:

            if document["hash"] == file_hash:

                return {
                    "message": "Document already exists",
                    "filename": filename
                }

        # Extract text, page-by-page / row-by-row
        raw_segments = extract_text(file_path)

        # Clean each segment independently
        segments = []

        for segment in raw_segments:

            segments.append({
                "text": clean_text(segment["text"]),
                "page_number": segment["page_number"],
                "source_location": segment["source_location"]
            })

        # Chunking (page/location-aware)
        chunks = create_chunks_from_segments(segments)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No content found in file"
            )

        # Load existing metadata
        existing_metadata = load_metadata()

        # Save chunk metadata, including where each chunk came from
        for chunk in chunks:

            existing_metadata.append({
                "chunk_id": str(uuid.uuid4()),
                "document_name": filename,
                "chunk": chunk["chunk"],
                "page_number": chunk["page_number"],
                "source_location": chunk["source_location"]
            })

        save_metadata(existing_metadata)

        # Generate embeddings (text only)
        chunk_texts = [chunk["chunk"] for chunk in chunks]

        embeddings = generate_embeddings(chunk_texts)

        # Save vectors to FAISS
        index = add_embeddings_to_index(embeddings)

        # Save hash to registry
        registry.append({
            "document_name": filename,
            "hash": file_hash
        })

        save_registry(registry)

        log_info(f"Document processed successfully: {filename}")

        return {
            "filename": filename,
            "total_chunks": len(chunks),
            "embedding_dimension": len(embeddings[0]),
            "metadata_records": len(existing_metadata),
            "total_vectors": index.ntotal
        }

    except HTTPException:

        raise

    except Exception as e:

        log_error(str(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to process document."
        )