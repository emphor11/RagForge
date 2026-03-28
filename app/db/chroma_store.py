import chromadb
from chromadb.config import Settings


class ChromaStore:
    def __init__(self, collection_name="ragforge"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, chunks, embeddings):
        ids = [f"id_{i}" for i in range(len(chunks))]

        documents = [c["content"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query(self, query_embedding, n_results=5):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )