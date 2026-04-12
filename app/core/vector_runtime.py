from functools import lru_cache

from app.core.embeddings.embedder import Embedder
from app.db.chroma_store import ChromaStore
from app.db.qdrant_store import QdrantStore


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()


@lru_cache(maxsize=1)
def get_vector_store():
    qdrant_store = QdrantStore()
    if qdrant_store.is_configured():
        return qdrant_store
    return ChromaStore()
