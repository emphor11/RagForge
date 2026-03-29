import json
import os


class InsightStore:
    def __init__(self, base_path="insights"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, document_id: str, data: dict):
        path = os.path.join(self.base_path, f"{document_id}.json")

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, document_id: str):
        path = os.path.join(self.base_path, f"{document_id}.json")

        if not os.path.exists(path):
            return None

        with open(path, "r") as f:
            json_data = json.load(f)

        return json_data