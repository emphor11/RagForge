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

    def update_review_finding_status(self, document_id: str, finding_index: int, status: str):
        data = self.load(document_id)
        if not data:
            return None

        findings = data.get("review_findings", [])
        if finding_index < 0 or finding_index >= len(findings):
            return None

        findings[finding_index]["status"] = status
        self.save(document_id, data)
        return findings[finding_index]

    def list_all(self):
        docs = []

        if not os.path.exists(self.base_path):
            return []

        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                path = os.path.join(self.base_path, filename)
                mtime = os.path.getmtime(path)
                doc_id = filename.replace(".json", "")

                docs.append({
                    "id": doc_id,
                    "filename": doc_id,
                    "upload_date": mtime
                })

        # Sort by mtime (newest first)
        docs.sort(key=lambda x: x["upload_date"], reverse=True)

        return docs
