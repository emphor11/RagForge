from app.core.embeddings.embedder import Embedder
from app.db.chroma_store import ChromaStore

embedder = Embedder()
vector_db = ChromaStore()


def store_chunks(chunks):
    texts = [c["content"] for c in chunks]

    embeddings = embedder.embed(texts)

    vector_db.add_documents(chunks, embeddings)