import mimetypes
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

import httpx

from backend.services.file_path_service import resolve_raw_document_path
from backend.services.persistence_config import is_supabase_backend


class ObjectStorageError(RuntimeError):
    """Raised when a private Supabase Storage operation fails."""


class ObjectAlreadyExistsError(ObjectStorageError):
    pass


def _storage_settings():
    project_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    bucket = os.getenv(
        "SUPABASE_STORAGE_BUCKET",
        "resolveiq-documents",
    ).strip()

    if not project_url or not service_key or not bucket:
        raise RuntimeError(
            "Supabase Storage configuration is incomplete."
        )

    return project_url, service_key, bucket


def _headers(content_type: str | None = None) -> dict:
    _, service_key, _ = _storage_settings()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    if content_type:
        headers["Content-Type"] = content_type

    return headers


def _object_path(filename: str) -> str:
    safe_filename = resolve_raw_document_path(filename).name
    return f"raw/{safe_filename}"


def _encoded_object_path(filename: str) -> str:
    return "/".join(
        quote(part, safe="")
        for part in _object_path(filename).split("/")
    )


def _upload_once(local_path: Path, filename: str) -> None:
    project_url, _, bucket = _storage_settings()
    content_type = (
        mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )
    url = (
        f"{project_url}/storage/v1/object/"
        f"{quote(bucket, safe='')}/{_encoded_object_path(filename)}"
    )

    with local_path.open("rb") as source:
        payload = source.read()

    response = httpx.post(
        url,
        content=payload,
        headers={
            **_headers(content_type),
            "x-upsert": "false",
        },
        timeout=30,
    )

    if response.status_code in {200, 201}:
        return

    body = response.text.lower()

    if (
        response.status_code == 409
        or "already exists" in body
        or "duplicate" in body
    ):
        raise ObjectAlreadyExistsError(filename)

    raise ObjectStorageError(
        "Supabase Storage upload failed "
        f"(status={response.status_code})."
    )


def upload_unique_document(local_path: Path, requested_filename: str) -> str:
    original = resolve_raw_document_path(requested_filename).name
    original_path = Path(original)
    candidate = original
    counter = 1

    while True:
        try:
            _upload_once(local_path, candidate)
            return candidate
        except ObjectAlreadyExistsError:
            candidate = (
                f"{original_path.stem}({counter}){original_path.suffix}"
            )
            counter += 1


def download_document(filename: str, destination: Path) -> None:
    project_url, _, bucket = _storage_settings()
    url = (
        f"{project_url}/storage/v1/object/authenticated/"
        f"{quote(bucket, safe='')}/{_encoded_object_path(filename)}"
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream(
        "GET",
        url,
        headers=_headers(),
        timeout=30,
    ) as response:
        if response.status_code == 404:
            raise FileNotFoundError(filename)

        if response.status_code != 200:
            raise ObjectStorageError(
                "Supabase Storage download failed "
                f"(status={response.status_code})."
            )

        with destination.open("wb") as target:
            for chunk in response.iter_bytes():
                target.write(chunk)


def document_exists(filename: str) -> bool:
    project_url, _, bucket = _storage_settings()
    url = (
        f"{project_url}/storage/v1/object/authenticated/"
        f"{quote(bucket, safe='')}/{_encoded_object_path(filename)}"
    )

    with httpx.stream(
        "GET",
        url,
        headers={**_headers(), "Range": "bytes=0-0"},
        timeout=15,
    ) as response:
        if response.status_code == 404:
            return False

        if response.status_code in {200, 206}:
            return True

        raise ObjectStorageError(
            "Supabase Storage lookup failed "
            f"(status={response.status_code})."
        )


def delete_document_object(filename: str) -> bool:
    project_url, _, bucket = _storage_settings()
    url = (
        f"{project_url}/storage/v1/object/{quote(bucket, safe='')}"
    )
    response = httpx.request(
        "DELETE",
        url,
        headers={
            **_headers("application/json"),
        },
        json={"prefixes": [_object_path(filename)]},
        timeout=20,
    )

    if response.status_code in {200, 404}:
        return response.status_code == 200

    raise ObjectStorageError(
        "Supabase Storage deletion failed "
        f"(status={response.status_code})."
    )


@contextmanager
def materialize_document(filename: str):
    """Yield a local path regardless of the configured storage backend."""

    local_path = resolve_raw_document_path(filename)

    if not is_supabase_backend():
        yield local_path
        return

    with TemporaryDirectory(prefix="resolveiq-document-") as temp_dir:
        temp_path = Path(temp_dir) / local_path.name
        download_document(local_path.name, temp_path)
        yield temp_path
