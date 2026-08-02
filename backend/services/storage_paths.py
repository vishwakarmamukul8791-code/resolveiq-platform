import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_data_dir() -> Path:
    configured = os.getenv("DATA_DIR", "").strip()

    if not configured:
        return (PROJECT_ROOT / "data").resolve()

    path = Path(configured).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


DATA_DIR = _resolve_data_dir()


def data_path(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)
