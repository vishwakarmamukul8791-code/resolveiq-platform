from backend.services.json_storage import load_json_list, save_json
from backend.services.storage_paths import data_path


REGISTRY_PATH = data_path("document_registry.json")




def load_registry():
    return load_json_list(REGISTRY_PATH)

def save_registry(data):
    save_json(REGISTRY_PATH, data)
