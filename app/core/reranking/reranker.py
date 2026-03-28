from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query, documents, top_k=5):
        pairs = [(query, doc["content"]) for doc in documents]

        scores = self.model.predict(pairs)

        reranked = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {**doc, "rerank_score": score}
            for doc, score in reranked[:top_k]
        ]
