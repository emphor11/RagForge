from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self, documents):
        self.texts = [doc["content"] for doc in documents]
        tokenized = [text.split() for text in self.texts]

        self.bm25 = BM25Okapi(tokenized)
        self.documents = documents

    def retrieve(self, query: str, k=5):
        tokenized_query = query.split()

        scores = self.bm25.get_scores(tokenized_query)

        ranked = sorted(
            zip(self.documents, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {**doc, "score": score}
            for doc, score in ranked[:k]
        ]