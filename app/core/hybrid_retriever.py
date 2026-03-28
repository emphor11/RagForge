class HybridRetriever:
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector = vector_retriever
        self.bm25 = bm25_retriever

    def retrieve(self, query: str, k=5):
        vector_results = self.vector.retrieve(query, k)
        bm25_results = self.bm25.retrieve(query, k)

        combined = {}

        # Merge vector results
        for doc in vector_results:
            key = doc["content"]
            combined[key] = doc

        # Merge BM25 results (boost score)
        for doc in bm25_results:
            key = doc["content"]
            if key in combined:
                combined[key]["score"] += doc["score"]
            else:
                combined[key] = doc

        # Sort by score
        sorted_docs = sorted(
            combined.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        return sorted_docs[:k]