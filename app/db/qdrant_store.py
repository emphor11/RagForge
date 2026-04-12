import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
from dotenv import load_dotenv

class QdrantStore:
    def __init__(self, collection_name="ragforge"):
        load_dotenv()
        # Support both the legacy names in the repo and standard Qdrant env names.
        url = os.getenv("QDRANT_URL") or os.getenv("Quadrant_Endpoint")
        api_key = os.getenv("QDRANT_API_KEY") or os.getenv("Quadrant_API_KEY")
        self.collection_name = collection_name

        if not url:
            print("⚠️ WARNING: Qdrant URL missing. Vector search features will be limited.")
            self.client = None
        else:
            try:
                self.client = QdrantClient(url=url, api_key=api_key)
            except Exception as e:
                print(f"❌ Failed to initialize Qdrant client: {e}")
                self.client = None

    def is_configured(self):
        return self.client is not None

    def _ensure_collection(self):
        if not self.is_configured(): return
        
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384, # Size for all-MiniLM-L6-v2
                        distance=models.Distance.COSINE
                    ),
                )
        except Exception as e:
            print(f"❌ Failed to ensure Qdrant collection: {e}")
            self.client = None

    def add_documents(self, chunks, embeddings):
        if not self.is_configured():
            return

        self._ensure_collection()
        if not self.is_configured():
            return

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            payload = self._sanitize_metadata(chunk["metadata"])
            payload["content"] = chunk["content"]
            
            points.append(models.PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload=payload
            ))
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def _sanitize_metadata(self, metadata):
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, list):
                sanitized[key] = " | ".join(str(item) for item in value) if value else ""
            else:
                sanitized[key] = value
        return sanitized

    def query(self, query_embedding, n_results=5, where=None):
        if not self.is_configured():
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        self._ensure_collection()
        if not self.is_configured():
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=n_results
        )

        if where:
            search_result = [
                result for result in search_result
                if all(result.payload.get(key) == value for key, value in where.items())
            ]

        return {
            "documents": [[res.payload["content"] for res in search_result]],
            "metadatas": [[res.payload for res in search_result]],
            "distances": [[max(0.0, 1.0 - float(res.score)) for res in search_result]],
        }

    def get_all_documents(self, source=None):
        if not self.is_configured():
            return []

        self._ensure_collection()
        if not self.is_configured():
            return []

        scroll_result = self.client.scroll(
            collection_name=self.collection_name,
            limit=100,
            with_payload=True,
            with_vectors=False
        )[0]
        
        if source:
            return [
                {"content": p.payload["content"], "metadata": p.payload} 
                for p in scroll_result if p.payload.get("source") == source
            ]
        
        return [{"content": p.payload["content"], "metadata": p.payload} for p in scroll_result]

    def delete_documents(self, source=None):
        if not self.is_configured() or not source:
            return

        self._ensure_collection()
        if not self.is_configured():
            return

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source",
                            match=models.MatchValue(value=source),
                        )
                    ]
                )
            ),
        )
