import os


class Embedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None

    def _get_model(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            local_files_only = os.getenv("LOCAL_MODEL_FILES_ONLY", "true").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            self.model = SentenceTransformer(
                self.model_name,
                local_files_only=local_files_only,
            )
        return self.model

    def embed(self, texts):
        return self._get_model().encode(texts)
