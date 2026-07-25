from fastapi import APIRouter, UploadFile, File, HTTPException
import os

from backend.services.logging_service import (
    log_info,
    log_error
)

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    allowed_extensions = [".pdf", ".csv", ".txt"]

    if not file.filename.lower().endswith(tuple(allowed_extensions)):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    try:

        name, extension = os.path.splitext(file.filename)

        os.makedirs("data/raw", exist_ok=True)
        file_path = f"data/raw/{file.filename}"

        counter = 1

        while os.path.exists(file_path):

            file_path = f"data/raw/{name}({counter}){extension}"

            counter += 1

        with open(file_path, "wb") as buffer:

            content = await file.read()

            buffer.write(content)

        log_info(f"File uploaded successfully: {file.filename}")

        return {
            "message": "File uploaded successfully",
            "filename": os.path.basename(file_path)
        }

    except Exception as e:

        log_error(str(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to upload file."
        )