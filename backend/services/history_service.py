import json
import os

HISTORY_PATH = "data/history/chat_history.json"


def load_history():

    if not os.path.exists(HISTORY_PATH):
        return []

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError:
        return []


def save_history(history):

    with open(HISTORY_PATH, "w", encoding="utf-8") as file:

        json.dump(
            history,
            file,
            indent=4
        )