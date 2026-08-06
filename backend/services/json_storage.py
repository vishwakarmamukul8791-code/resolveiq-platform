import json
import os
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import RLock

from backend.services.database_service import (
    collection_transaction,
    load_collection,
    save_collection,
)
from backend.services.persistence_config import is_supabase_backend
from backend.services.storage_paths import DATA_DIR


class StorageCorruptionError(RuntimeError):
    """Raised instead of silently replacing malformed persisted state."""


_locks_guard = RLock()
_path_locks = defaultdict(RLock)


def _get_lock(path: Path) -> RLock:
    resolved = str(Path(path).resolve())

    with _locks_guard:
        return _path_locks[resolved]


@contextmanager
def storage_lock(path: Path):
    lock = _get_lock(Path(path))

    with lock:
        yield


def synchronized_storage(path: Path):
    """Keep a read-modify-write function atomic within this process."""

    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if is_supabase_backend():
                namespace = _collection_namespace(path)

                with collection_transaction(namespace):
                    return function(*args, **kwargs)

            with storage_lock(path):
                return function(*args, **kwargs)

        return wrapped

    return decorator


def _collection_namespace(path: Path) -> str:
    resolved = Path(path).resolve()

    try:
        return resolved.relative_to(DATA_DIR).as_posix()
    except ValueError:
        return resolved.name


def load_json_list(path: Path) -> list:
    path = Path(path)

    if is_supabase_backend():
        return load_collection(_collection_namespace(path))

    with storage_lock(path):
        if not path.is_file():
            return []

        try:
            with path.open("r", encoding="utf-8-sig") as file:
                data = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StorageCorruptionError(
                f"Invalid JSON storage file: {path.name}"
            ) from exc

        if not isinstance(data, list):
            raise StorageCorruptionError(
                f"JSON storage file must contain a list: {path.name}"
            )

        return data


def save_json(path: Path, data) -> None:
    path = Path(path)

    if is_supabase_backend():
        if not isinstance(data, list):
            raise TypeError("Database-backed JSON storage requires a list.")

        save_collection(_collection_namespace(path), data)
        return

    with storage_lock(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                json.dump(data, temp_file, indent=4)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)

            os.replace(temp_path, path)

        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
