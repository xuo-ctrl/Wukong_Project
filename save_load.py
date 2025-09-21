import json, os

SAVE_FILE = "save.json"

def save_game(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {}
