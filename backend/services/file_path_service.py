from pathlib import Path

from backend.services.storage_paths import data_path


RAW_DOCUMENT_DIR = data_path("raw")

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".csv", ".txt"}


def resolve_raw_document_path(filename: str) -> Path:
    if not filename:
        raise ValueError("Filename is required")

    if (
        "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or filename in {".", ".."}
        or len(filename) > 255
    ):
        raise ValueError("Invalid filename")

    candidate = (RAW_DOCUMENT_DIR / filename).resolve()

    if candidate.parent != RAW_DOCUMENT_DIR:
        raise ValueError("Invalid filename")

    if candidate.suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError("Unsupported file type")

    return candidate
