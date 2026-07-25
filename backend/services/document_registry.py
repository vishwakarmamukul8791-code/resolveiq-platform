import json
import os


REGISTRY_PATH = (
    "data/document_registry.json"
)




def load_registry():

    path = "data/document_registry.json"

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as file:

        content = file.read().strip()

        if not content:
            return []

        return json.loads(content)

def save_registry(data):
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)

    with open(
        REGISTRY_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )