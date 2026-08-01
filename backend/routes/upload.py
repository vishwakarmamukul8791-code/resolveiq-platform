from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.services.auth_service import require_admin
from backend.services.file_path_service import resolve_raw_document_path
from backend.services.logging_service import log_error, log_info


router = APIRouter()


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

    original_path = file_path
    counter = 1

    while file_path.exists():
        file_path = original_path.with_name(
            f"{original_path.stem}({counter}){original_path.suffix}"
        )
        counter += 1

    try:
        content = await file.read()

        with file_path.open("wb") as buffer:
            buffer.write(content)

        safe_filename = file_path.name

        log_info(
            f"File uploaded successfully: {safe_filename} "
            f"by admin={current_user['username']}"
        )

        return {
            "message": "File uploaded successfully",
            "filename": safe_filename
        }

    except Exception as exc:
        log_error(str(exc))

        raise HTTPException(
            status_code=500,
            detail="Unable to upload file."
        ) from exc
