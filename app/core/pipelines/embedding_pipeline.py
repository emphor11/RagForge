from app.core.vector_runtime import get_embedder, get_vector_store


def store_chunks(chunks):
    texts = [c["content"] for c in chunks]
    if not texts:
        return

    embeddings = get_embedder().embed(texts)
    get_vector_store().add_documents(chunks, embeddings)
