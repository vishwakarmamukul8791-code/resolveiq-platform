from fastapi import APIRouter, Depends, HTTPException

from backend.services.auth_service import require_admin
from backend.services.bm25_service import invalidate_cache as invalidate_bm25_cache
from backend.services.document_registry import load_registry, save_registry
from backend.services.faiss_service import (
    delete_faiss_index,
    load_faiss_index,
    save_faiss_index
)
from backend.services.file_path_service import resolve_raw_document_path
from backend.services.logging_service import log_error, log_info
from backend.services.object_storage_service import (
    delete_document_object,
    document_exists,
)
from backend.services.persistence_config import is_supabase_backend
from backend.services.pgvector_service import delete_document_data
from backend.services.reindex_service import (
    build_index_from_metadata,
    persist_rebuilt_index,
    rebuild_index
)
from backend.services.vector_store import load_metadata, save_metadata
from backend.services.storage_locks import synchronized_document_storage


router = APIRouter()


def _load_consistent_original_index(original_metadata):
    index = load_faiss_index()
    expected_count = len(original_metadata)

    if expected_count == 0:
        if index is not None:
            index = rebuild_index()

        return index

    if index is None or index.ntotal != expected_count:
        index = rebuild_index()

    if index is None or index.ntotal != expected_count:
        actual_count = 0 if index is None else index.ntotal

        raise RuntimeError(
            "Original FAISS/metadata consistency could not be restored: "
            f"vectors={actual_count}, metadata={expected_count}"
        )

    return index


def _restore_deletion_state(
    original_metadata,
    original_registry,
    original_index
):
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
            "Deletion rollback failed: "
            + "; ".join(rollback_errors)
        )


@router.delete("/document/{filename}")
@synchronized_document_storage
def delete_document(
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

    safe_filename = file_path.name

    try:
        original_registry = load_registry()
        original_metadata = load_metadata()

        file_exists = (
            document_exists(safe_filename)
            if is_supabase_backend()
            else file_path.is_file()
        )

        registry_entry_exists = any(
            document["document_name"] == safe_filename
            for document in original_registry
        )

        metadata_exists = any(
            chunk["document_name"] == safe_filename
            for chunk in original_metadata
        )

        if not (
            file_exists
            or registry_entry_exists
            or metadata_exists
        ):
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        proposed_registry = [
            document
            for document in original_registry
            if document["document_name"] != safe_filename
        ]

        proposed_metadata = [
            chunk
            for chunk in original_metadata
            if chunk["document_name"] != safe_filename
        ]

        removed_chunks = (
            len(original_metadata) - len(proposed_metadata)
        )

        if is_supabase_backend():
            removed_chunks = delete_document_data(safe_filename)

            object_deleted = False

            if file_exists:
                try:
                    object_deleted = delete_document_object(safe_filename)
                except Exception as cleanup_exc:
                    # Database records are already removed atomically. An
                    # orphaned private object is inaccessible through the
                    # app and can be retried manually without resurrecting
                    # deleted document data.
                    log_error(
                        "Document record deleted but object cleanup failed: "
                        f"{type(cleanup_exc).__name__}"
                    )

            remaining_vectors = len(proposed_metadata)

            log_info(
                f"Document deleted: {safe_filename} "
                f"chunks_removed={removed_chunks} "
                f"by admin={current_user['username']}"
            )

            return {
                "message": "Document deleted successfully",
                "filename": safe_filename,
                "removed_chunks": removed_chunks,
                "remaining_vectors": remaining_vectors,
                "object_deleted": object_deleted,
            }

        original_index = _load_consistent_original_index(
            original_metadata
        )

        # Build replacement index before changing persisted state.
        staged_index = build_index_from_metadata(
            proposed_metadata
        )

        try:
            persist_rebuilt_index(staged_index)
            save_metadata(proposed_metadata)
            save_registry(proposed_registry)

            # Raw file is removed only after index and JSON updates succeed.
            if file_exists:
                file_path.unlink()

        except Exception as commit_exc:
            try:
                _restore_deletion_state(
                    original_metadata,
                    original_registry,
                    original_index
                )

            except Exception as rollback_exc:
                log_error(
                    f"Document deletion commit failed: {commit_exc}; "
                    f"rollback also failed: {rollback_exc}"
                )

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Document deletion failed and storage "
                        "recovery was incomplete."
                    )
                ) from commit_exc

            log_error(
                f"Document deletion failed and was rolled back: "
                f"{commit_exc}"
            )

            raise HTTPException(
                status_code=500,
                detail="Unable to delete document."
            ) from commit_exc

        invalidate_bm25_cache()

        log_info(
            f"Document deleted: {safe_filename} "
            f"chunks_removed={removed_chunks} "
            f"by admin={current_user['username']}"
        )

        return {
            "message": "Document deleted successfully",
            "filename": safe_filename,
            "removed_chunks": removed_chunks,
            "remaining_vectors": (
                0 if staged_index is None else staged_index.ntotal
            )
        }

    except HTTPException:
        raise

    except Exception as exc:
        log_error(str(exc))

        raise HTTPException(
            status_code=500,
            detail="Unable to delete document."
        ) from exc
