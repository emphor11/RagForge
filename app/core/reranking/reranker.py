import os


class Reranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None

    def _get_model(self):
        if self.model is None:
            from sentence_transformers import CrossEncoder

            local_files_only = os.getenv("LOCAL_MODEL_FILES_ONLY", "true").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            self.model = CrossEncoder(
                self.model_name,
                local_files_only=local_files_only,
            )
        return self.model

    def rerank(self, query, documents, top_k=5):
        if not documents:
            return []

        pairs = [(query, doc["content"]) for doc in documents]

        try:
            scores = self._get_model().predict(pairs)
        except Exception as exc:
            print(f"⚠️ Reranker unavailable, using retrieval order: {exc}")
            return documents[:top_k]

        reranked = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {**doc, "rerank_score": score}
            for doc, score in reranked[:top_k]
        ]
