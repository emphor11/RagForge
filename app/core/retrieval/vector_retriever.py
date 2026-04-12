from typing import List, Optional
from app.core.vector_runtime import get_embedder, get_vector_store


class VectorRetriever:
    def __init__(self):
        self.embedder = get_embedder()
        self.db = get_vector_store()

    def retrieve(self, query: str, k=5, document_id: Optional[str] = None):
        query_embedding = self.embedder.embed([query])[0]

        where = {"source": document_id} if document_id else None
        results = self.db.query(query_embedding, n_results=k, where=where)

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        # Convert distance → similarity score
        return [
            {
                "content": doc,
                "metadata": meta,
                "score": 1 / (1 + dist)   # normalize
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]
