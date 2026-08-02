import os

import numpy as np
from google import genai
from google.genai import types


EMBEDDING_PROVIDER = os.getenv(
    "EMBEDDING_PROVIDER",
    "local"
).strip().lower()

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "gemini-embedding-001"
).strip()

EMBEDDING_DIMENSION = int(
    os.getenv("EMBEDDING_DIMENSION", "384")
)
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_local_model = None
_gemini_client = None


def _get_local_model():
    global _local_model

    if _local_model is None:
        from sentence_transformers import SentenceTransformer

        _local_model = SentenceTransformer(
            LOCAL_EMBEDDING_MODEL
        )

    return _local_model


def _get_gemini_client():
    global _gemini_client

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is required for Gemini embeddings."
        )

    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=api_key)

    return _gemini_client


def _generate_gemini_embeddings(texts):
    response = _get_gemini_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        ),
    )

    vectors = np.asarray(
        [
            embedding.values
            for embedding in response.embeddings
        ],
        dtype="float32",
    )

    expected_shape = (
        len(texts),
        EMBEDDING_DIMENSION,
    )

    if vectors.shape != expected_shape:
        raise RuntimeError(
            "Unexpected Gemini embedding shape: "
            f"expected={expected_shape}, actual={vectors.shape}"
        )

    norms = np.linalg.norm(
        vectors,
        axis=1,
        keepdims=True,
    )

    if np.any(norms == 0):
        raise RuntimeError(
            "Gemini returned a zero-length embedding."
        )

    return np.ascontiguousarray(
        vectors / norms,
        dtype="float32",
    )


def generate_embeddings(chunks):
    if not chunks:
        return np.empty(
            (0, EMBEDDING_DIMENSION),
            dtype="float32",
        )

    if EMBEDDING_PROVIDER == "gemini":
        return _generate_gemini_embeddings(chunks)

    if EMBEDDING_PROVIDER != "local":
        raise RuntimeError(
            "EMBEDDING_PROVIDER must be 'local' or 'gemini'."
        )

    model = _get_local_model()

    return np.ascontiguousarray(
        model.encode(chunks),
        dtype="float32",
    )


def get_embedding_model_name():
    if EMBEDDING_PROVIDER == "local":
        return LOCAL_EMBEDDING_MODEL

    return EMBEDDING_MODEL
