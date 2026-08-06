from backend.services.json_storage import load_json_list, save_json
from backend.services.persistence_config import is_supabase_backend
from backend.services.storage_paths import data_path


METADATA_PATH = data_path("vector_store", "metadata.json")


def save_metadata(metadata):
    if is_supabase_backend():
        raise RuntimeError(
            "Supabase chunk metadata must be saved together with embeddings."
        )

    save_json(METADATA_PATH, metadata)


def load_metadata():
    if is_supabase_backend():
        from backend.services.pgvector_service import load_chunk_metadata

        return load_chunk_metadata()

    return load_json_list(METADATA_PATH)
