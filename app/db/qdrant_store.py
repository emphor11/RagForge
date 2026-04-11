import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
from dotenv import load_dotenv

class QdrantStore:
    def __init__(self, collection_name="ragforge"):
        load_dotenv()
        # We use the names from your .env file
        url = os.getenv("Quadrant_Endpoint")
        api_key = os.getenv("Quadrant_API_KEY")
        
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        
        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
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

    def add_documents(self, chunks, embeddings):
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
        # We'll implement a simple version of the filter if 'where' is provided later
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=n_results
        )
        
        # Format to match your previous ChromaDB output structure
        return {
            "documents": [[res.payload["content"] for res in search_result]],
            "metadatas": [[res.payload for res in search_result]]
        }

    def get_all_documents(self, source=None):
        # Simple scroll to get documents
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
