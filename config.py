import json, os

CONFIG_FILE = "config.json"

class Config:
    @staticmethod
    def load() -> dict:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}

    @staticmethod
    def save(data: dict):
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
