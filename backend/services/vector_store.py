from backend.services.json_storage import load_json_list, save_json
from backend.services.storage_paths import data_path


METADATA_PATH = data_path("vector_store", "metadata.json")


def save_metadata(metadata):
    save_json(METADATA_PATH, metadata)


def load_metadata():
    return load_json_list(METADATA_PATH)
