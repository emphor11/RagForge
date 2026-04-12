import chromadb
from chromadb.config import Settings


class ChromaStore:
    def __init__(self, collection_name="ragforge"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, chunks, embeddings):
        import uuid
        ids = [str(uuid.uuid4()) for _ in range(len(chunks))]

        documents = [c["content"] for c in chunks]
        metadatas = [self._sanitize_metadata(c["metadata"]) for c in chunks]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def _sanitize_metadata(self, metadata):
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, list):
                if not value:
                    sanitized[key] = ""
                else:
                    sanitized[key] = " | ".join(str(item) for item in value)
            else:
                sanitized[key] = value
        return sanitized

    def query(self, query_embedding, n_results=5, where=None):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

    def get_all_documents(self, source=None):
        if source:
            results = self.collection.get(where={"source": source})
        else:
            results = self.collection.get()

        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []

        return [
            {"content": doc, "metadata": meta}
            for doc, meta in zip(documents, metadatas)
        ]

    def delete_documents(self, source=None):
        if source:
            self.collection.delete(where={"source": source})
