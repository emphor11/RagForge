from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None

    def _get_model(self):
        if self.model is None:
            self.model = SentenceTransformer(self.model_name, local_files_only=True)
        return self.model

    def embed(self, texts):
        return self._get_model().encode(texts)
