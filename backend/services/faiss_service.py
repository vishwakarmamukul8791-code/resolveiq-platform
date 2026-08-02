import os
import tempfile
from pathlib import Path

import faiss
import numpy as np

from backend.services.storage_paths import data_path


INDEX_PATH = data_path("vector_store", "index.faiss")


def _prepare_embeddings(embeddings):
    prepared = np.asarray(embeddings, dtype="float32")

    if prepared.ndim != 2 or prepared.shape[0] == 0:
        raise ValueError(
            "Embeddings must be a non-empty two-dimensional array."
        )

    return prepared


def create_faiss_index(embeddings):
    prepared = _prepare_embeddings(embeddings)

    dimension = prepared.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(prepared)

    return index


def create_staged_index(embeddings, existing_index=None):
    """
    Creates an updated FAISS index without modifying the existing index.

    The caller can persist the staged index only after all processing
    steps have completed successfully.
    """
    prepared = _prepare_embeddings(embeddings)
    dimension = prepared.shape[1]

    if existing_index is None:
        staged_index = faiss.IndexFlatL2(dimension)
    else:
        if existing_index.d != dimension:
            raise RuntimeError(
                "Embedding dimension does not match existing FAISS index: "
                f"index={existing_index.d}, embeddings={dimension}"
            )

        staged_index = faiss.clone_index(existing_index)

    staged_index.add(prepared)

    return staged_index


def save_faiss_index(index):
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=INDEX_PATH.parent,
            prefix=f".{INDEX_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        faiss.write_index(index, str(temp_path))
        os.replace(temp_path, INDEX_PATH)

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def load_faiss_index():
    if not INDEX_PATH.is_file():
        return None

    return faiss.read_index(str(INDEX_PATH))


def delete_faiss_index():
    INDEX_PATH.unlink(missing_ok=True)


def add_embeddings_to_index(embeddings):
    """
    Backward-compatible helper for callers that require immediate saving.
    Transactional processing should use create_staged_index() directly.
    """
    existing_index = load_faiss_index()
    staged_index = create_staged_index(embeddings, existing_index)

    save_faiss_index(staged_index)

    return staged_index
