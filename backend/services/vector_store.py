import json
import os


def save_metadata(metadata):

    with open(
        "data/vector_store/metadata.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4
        )


def load_metadata():

    path = "data/vector_store/metadata.json"

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError:
        return []