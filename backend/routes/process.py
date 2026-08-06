import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE
from backend.services.auth_service import require_admin
from backend.services.cleaning_service import clean_text
from backend.services.document_registry import load_registry, save_registry
from backend.services.embedding_service import generate_embeddings
from backend.services.extraction_service import extract_text
from backend.services.faiss_service import (
    create_staged_index,
    delete_faiss_index,
    load_faiss_index,
    save_faiss_index
)
from backend.services.file_path_service import resolve_raw_document_path
from backend.services.hash_service import generate_file_hash
from backend.services.logging_service import log_error, log_info
from backend.services.object_storage_service import (
    delete_document_object,
    materialize_document,
)
from backend.services.persistence_config import is_supabase_backend
from backend.services.pgvector_service import commit_processed_document
from backend.services.reindex_service import rebuild_index
from backend.services.storage_locks import synchronized_document_storage
from backend.services.vector_store import load_metadata, save_metadata


router = APIRouter()


def _chunk_single_text(text):
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def create_chunks_from_segments(segments):
    """
    Chunk every page, CSV row, or text segment separately so each
    chunk retains its original page number and source location.
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


def _load_consistent_existing_index(existing_metadata):
    """
    Load the existing index and repair it before appending when its
    vector count does not match the existing metadata count.
    """
    index = load_faiss_index()
    expected_count = len(existing_metadata)

    if expected_count == 0:
        if index is not None and index.ntotal != 0:
            index = rebuild_index()

        return index

    if index is None or index.ntotal != expected_count:
        index = rebuild_index()

    if index is None or index.ntotal != expected_count:
        actual_count = 0 if index is None else index.ntotal

        raise RuntimeError(
            "Existing FAISS/metadata consistency could not be restored: "
            f"vectors={actual_count}, metadata={expected_count}"
        )

    return index


def _restore_processing_state(
    original_metadata,
    original_registry,
    original_index
):
    """
    Best-effort rollback for failures during persistence.
    Every recovery operation is attempted even if another one fails.
    """
    rollback_errors = []

    operations = [
        (
            "metadata",
            lambda: save_metadata(original_metadata)
        ),
        (
            "registry",
            lambda: save_registry(original_registry)
        ),
        (
            "FAISS index",
            lambda: (
                delete_faiss_index()
                if original_index is None
                else save_faiss_index(original_index)
            )
        )
    ]

    for name, operation in operations:
        try:
            operation()
        except Exception as exc:
            rollback_errors.append(f"{name}: {exc}")

    if rollback_errors:
        raise RuntimeError(
            "Processing rollback failed: "
            + "; ".join(rollback_errors)
        )


def _remove_duplicate_upload(filename, materialized_path):
    if is_supabase_backend():
        delete_document_object(filename)
    else:
        materialized_path.unlink(missing_ok=True)


def _process_materialized_document(file_path, safe_filename, current_user):
    file_hash = generate_file_hash(str(file_path))
    original_registry = load_registry()

    for document in original_registry:
        if document["hash"] == file_hash:
            if document["document_name"] != safe_filename:
                _remove_duplicate_upload(safe_filename, file_path)

            return {
                "message": "Document already exists",
                "filename": document["document_name"],
            }

    raw_segments = extract_text(str(file_path))

    segments = [
        {
            "text": clean_text(segment["text"]),
            "page_number": segment["page_number"],
            "source_location": segment["source_location"]
        }
        for segment in raw_segments
    ]

    chunks = create_chunks_from_segments(segments)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No content found in file"
        )

    new_records = [
        {
            "chunk_id": str(uuid.uuid4()),
            "document_name": safe_filename,
            "chunk": chunk["chunk"],
            "page_number": chunk["page_number"],
            "source_location": chunk["source_location"]
        }
        for chunk in chunks
    ]

    proposed_registry = [
        *original_registry,
        {
            "document_name": safe_filename,
            "hash": file_hash
        }
    ]

    chunk_texts = [chunk["chunk"] for chunk in chunks]
    embeddings = generate_embeddings(chunk_texts)

    if is_supabase_backend():
        total_vectors = commit_processed_document(
            safe_filename,
            new_records,
            embeddings,
            proposed_registry,
        )

        log_info(
            f"Document processed successfully: {safe_filename} "
            f"by admin={current_user['username']}"
        )

        return {
            "filename": safe_filename,
            "total_chunks": len(chunks),
            "embedding_dimension": int(embeddings.shape[1]),
            "metadata_records": total_vectors,
            "total_vectors": total_vectors,
        }

    original_metadata = load_metadata()
    original_index = _load_consistent_existing_index(original_metadata)
    proposed_metadata = [*original_metadata, *new_records]

    staged_index = create_staged_index(embeddings, original_index)

    if staged_index.ntotal != len(proposed_metadata):
        raise RuntimeError(
            "Staged FAISS/metadata count mismatch: "
            f"vectors={staged_index.ntotal}, "
            f"metadata={len(proposed_metadata)}"
        )

    try:
        save_faiss_index(staged_index)
        save_metadata(proposed_metadata)
        save_registry(proposed_registry)

    except Exception as commit_exc:
        try:
            _restore_processing_state(
                original_metadata,
                original_registry,
                original_index
            )

        except Exception as rollback_exc:
            log_error(
                f"Document processing commit failed: {commit_exc}; "
                f"rollback also failed: {rollback_exc}"
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Document processing failed and storage "
                    "recovery was incomplete."
                )
            ) from commit_exc

        log_error(
            f"Document processing commit failed and was rolled back: "
            f"{commit_exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to save processed document."
        ) from commit_exc

    log_info(
        f"Document processed successfully: {safe_filename} "
        f"by admin={current_user['username']}"
    )

    return {
        "filename": safe_filename,
        "total_chunks": len(chunks),
        "embedding_dimension": staged_index.d,
        "metadata_records": len(proposed_metadata),
        "total_vectors": staged_index.ntotal
    }


@router.post("/process-document")
@synchronized_document_storage
def process_document(
    filename: str,
    current_user: dict = Depends(require_admin)
):
    try:
        file_path = resolve_raw_document_path(filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    if not is_supabase_backend() and not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    safe_filename = file_path.name

    try:
        with materialize_document(safe_filename) as materialized_path:
            return _process_materialized_document(
                materialized_path,
                safe_filename,
                current_user,
            )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        log_error(str(exc))

        raise HTTPException(
            status_code=500,
            detail="Unable to process document."
        ) from exc
