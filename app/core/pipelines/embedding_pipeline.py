from app.core.embeddings.embedder import Embedder
from app.db.qdrant_store import QdrantStore  # Import Qdrant instead of Chroma

embedder = Embedder()
vector_db = QdrantStore()  # Initialize QdrantStore


def store_chunks(chunks):
    texts = [c["content"] for c in chunks]
    embeddings = embedder.embed(texts)
    vector_db.add_documents(chunks, embeddings)
