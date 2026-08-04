import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.services.auth_service import require_admin
from backend.services.file_path_service import resolve_raw_document_path
from backend.services.logging_service import log_error, log_info


router = APIRouter()

DEFAULT_MAX_UPLOAD_SIZE_MB = 10
READ_CHUNK_SIZE = 1024 * 1024


def _get_max_upload_bytes():
    raw_value = os.getenv(
        "MAX_UPLOAD_SIZE_MB",
        str(DEFAULT_MAX_UPLOAD_SIZE_MB),
    )

    try:
        size_mb = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            "MAX_UPLOAD_SIZE_MB must be a positive integer."
        ) from exc

    if size_mb <= 0:
        raise RuntimeError(
            "MAX_UPLOAD_SIZE_MB must be a positive integer."
        )

    return size_mb * 1024 * 1024


def _reserve_upload_path(original_path):
    """
    Atomically claims a filename using O_CREAT|O_EXCL, which fails
    outright if the path already exists instead of silently overwriting
    it. The previous approach (`while path.exists(): try_next_name()`)
    checked existence and created the file as two separate steps — two
    uploads of the same original filename arriving at nearly the same
    moment could both pass the `.exists()` check for the same candidate
    name before either had created it, and one would silently clobber
    the other. O_CREAT|O_EXCL makes "does this name exist" and "claim
    it" one atomic OS-level operation, so only one of the two racing
    requests can ever win a given filename.
    """

    candidate = original_path
    counter = 1

    while True:
        try:
            fd = os.open(
                str(candidate),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.close(fd)
            return candidate
        except FileExistsError:
            candidate = original_path.with_name(
                f"{original_path.stem}({counter}){original_path.suffix}"
            )
            counter += 1


def _validate_file_content(file_path):
    with file_path.open("rb") as uploaded_file:
        header = uploaded_file.read(4096)

    if not header:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if file_path.suffix.lower() == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="File content is not a valid PDF.",
            )
        return

    try:
        with file_path.open(
            "r",
            encoding="utf-8-sig",
        ) as uploaded_text:
            while text_chunk := uploaded_text.read(64 * 1024):
                if "\x00" in text_chunk:
                    raise UnicodeDecodeError(
                        "utf-8",
                        b"\x00",
                        0,
                        1,
                        "NUL byte",
                    )
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Text and CSV uploads must contain UTF-8 text.",
        ) from exc


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin)
):
    try:
        file_path = resolve_raw_document_path(file.filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path = _reserve_upload_path(file_path)

    try:
        total_bytes = 0
        max_bytes = _get_max_upload_bytes()

        with file_path.open("wb") as buffer:
            while chunk := await file.read(READ_CHUNK_SIZE):
                total_bytes += len(chunk)

                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File is too large. Maximum upload size is "
                            f"{max_bytes // (1024 * 1024)} MB."
                        ),
                    )

                buffer.write(chunk)

        _validate_file_content(file_path)

        safe_filename = file_path.name

        log_info(
            f"File uploaded successfully: {safe_filename} "
            f"by admin={current_user['username']}"
        )

        return {
            "message": "File uploaded successfully",
            "filename": safe_filename
        }

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise

    except Exception as exc:
        file_path.unlink(missing_ok=True)
        log_error(str(exc))

        raise HTTPException(
            status_code=500,
            detail="Unable to upload file."
        ) from exc
