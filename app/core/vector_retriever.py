from app.core.embeddings.embedder import Embedder
from app.db.chroma_store import ChromaStore


class VectorRetriever:
    def __init__(self):
        self.embedder = Embedder()
        self.db = ChromaStore()

    def retrieve(self, query: str, k=5):
        query_embedding = self.embedder.embed([query])[0]

        results = self.db.query(query_embedding, n_results=k)

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        # Convert distance → similarity score
        return [
            {
                "content": doc,
                "metadata": meta,
                "score": 1 / (1 + dist)   # normalize
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]
