from __future__ import annotations

from functools import lru_cache
from typing import Any

from rank_bm25 import BM25Okapi

from config.settings import settings


EMBED_MODEL = "text-embedding-3-small"
RERANK_MODEL = "rerank-v3.5"
DEFAULT_TOP_K = 12
DEFAULT_PREFETCH_K = 18
EMBED_BATCH_SIZE = 64


def _normalize_tokens(text: str) -> list[str]:
    return [token for token in text.lower().split() if token]


def _chunk_payload(chunk: dict[str, Any], document_id: str) -> dict[str, Any]:
    metadata = dict(chunk.get("metadata") or {})
    metadata["document_id"] = document_id
    metadata["chunk_text"] = chunk.get("content", "")
    return metadata


class HostedRetrievalService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.cohere_api_key = settings.COHERE_API_KEY
        self.qdrant_url = settings.QDRANT_URL
        self.qdrant_api_key = settings.QDRANT_API_KEY
        self.collection_name = settings.QDRANT_COLLECTION
        self._openai_client = None
        self._cohere_client = None
        self._qdrant_client = None
        self._qdrant_models = None

    def has_embedding_stack(self) -> bool:
        return bool(self.openai_api_key and self.qdrant_url)

    def has_reranker(self) -> bool:
        return bool(self.cohere_api_key)

    def _get_openai_client(self):
        if self._openai_client is not None:
            return self._openai_client
        if not self.openai_api_key:
            return None
        try:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=self.openai_api_key)
        except Exception as exc:
            print(f"⚠️ OpenAI embeddings unavailable: {exc}")
            self._openai_client = None
        return self._openai_client

    def _get_cohere_client(self):
        if self._cohere_client is not None:
            return self._cohere_client
        if not self.cohere_api_key:
            return None
        try:
            import cohere

            self._cohere_client = cohere.ClientV2(api_key=self.cohere_api_key)
        except Exception as exc:
            print(f"⚠️ Cohere reranker unavailable: {exc}")
            self._cohere_client = None
        return self._cohere_client

    def _get_qdrant(self):
        if self._qdrant_client is not None:
            return self._qdrant_client
        if not self.qdrant_url:
            return None
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            self._qdrant_client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
            )
            self._qdrant_models = models
        except Exception as exc:
            print(f"⚠️ Qdrant client unavailable: {exc}")
            self._qdrant_client = None
            self._qdrant_models = None
        return self._qdrant_client

    def _ensure_collection(self):
        client = self._get_qdrant()
        if not client or not self._qdrant_models:
            return False

        try:
            collections = client.get_collections().collections
            if any(collection.name == self.collection_name for collection in collections):
                return True

            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=self._qdrant_models.VectorParams(
                    size=1536,
                    distance=self._qdrant_models.Distance.COSINE,
                ),
            )
            return True
        except Exception as exc:
            print(f"⚠️ Failed to ensure Qdrant collection: {exc}")
            return False

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        client = self._get_openai_client()
        if not client or not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            try:
                response = client.embeddings.create(model=EMBED_MODEL, input=batch)
            except Exception as exc:
                print(f"⚠️ OpenAI embeddings request failed: {exc}")
                return []
            vectors.extend(item.embedding for item in response.data)
        return vectors

    def _delete_document_points(self, document_id: str):
        client = self._get_qdrant()
        if not client or not self._qdrant_models:
            return
        try:
            client.delete(
                collection_name=self.collection_name,
                points_selector=self._qdrant_models.FilterSelector(
                    filter=self._qdrant_models.Filter(
                        must=[
                            self._qdrant_models.FieldCondition(
                                key="document_id",
                                match=self._qdrant_models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            print(f"⚠️ Failed to delete existing Qdrant points for {document_id}: {exc}")

    def store_document_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.has_embedding_stack():
            return {"mode": "bm25_only", "stored_vectors": 0}
        if not chunks:
            return {"mode": "bm25_only", "stored_vectors": 0}
        if not self._ensure_collection():
            return {"mode": "bm25_only", "stored_vectors": 0}

        texts = [chunk.get("content", "") for chunk in chunks if chunk.get("content")]
        vectors = self._embed_texts(texts)
        if len(vectors) != len(texts):
            return {"mode": "bm25_only", "stored_vectors": 0}

        client = self._get_qdrant()
        if not client or not self._qdrant_models:
            return {"mode": "bm25_only", "stored_vectors": 0}

        self._delete_document_points(document_id)

        try:
            points = []
            for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
                payload = _chunk_payload(chunk, document_id)
                points.append(
                    self._qdrant_models.PointStruct(
                        id=f"{document_id}:{payload.get('chunk_id', index)}",
                        vector=vector,
                        payload=payload,
                    )
                )
            client.upsert(collection_name=self.collection_name, points=points)
            return {"mode": "hybrid", "stored_vectors": len(points)}
        except Exception as exc:
            print(f"⚠️ Failed to store Qdrant vectors for {document_id}: {exc}")
            return {"mode": "bm25_only", "stored_vectors": 0}

    def bm25_retrieve(self, chunks: list[dict[str, Any]], query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
        documents = [chunk for chunk in chunks if chunk.get("content")]
        if not documents:
            return []

        tokenized_docs = [_normalize_tokens(chunk["content"]) for chunk in documents]
        bm25 = BM25Okapi(tokenized_docs)
        scores = bm25.get_scores(_normalize_tokens(query))
        ranked = sorted(
            zip(documents, scores),
            key=lambda item: item[1],
            reverse=True,
        )
        results = []
        for chunk, score in ranked[:top_k]:
            results.append(
                {
                    "content": chunk.get("content", ""),
                    "metadata": dict(chunk.get("metadata") or {}),
                    "score": float(score),
                    "retrieval_source": "bm25",
                }
            )
        return results

    def vector_retrieve(self, document_id: str, query: str, top_k: int = DEFAULT_PREFETCH_K) -> list[dict[str, Any]]:
        if not self.has_embedding_stack():
            return []
        if not self._ensure_collection():
            return []
        query_vectors = self._embed_texts([query])
        if not query_vectors:
            return []

        client = self._get_qdrant()
        if not client or not self._qdrant_models:
            return []

        try:
            response = client.search(
                collection_name=self.collection_name,
                query_vector=query_vectors[0],
                query_filter=self._qdrant_models.Filter(
                    must=[
                        self._qdrant_models.FieldCondition(
                            key="document_id",
                            match=self._qdrant_models.MatchValue(value=document_id),
                        )
                    ]
                ),
                limit=top_k,
            )
        except Exception as exc:
            print(f"⚠️ Qdrant vector search failed for {document_id}: {exc}")
            return []

        results = []
        for hit in response:
            payload = dict(hit.payload or {})
            results.append(
                {
                    "content": payload.get("chunk_text", ""),
                    "metadata": payload,
                    "score": float(getattr(hit, "score", 0.0) or 0.0),
                    "retrieval_source": "vector",
                }
            )
        return results

    def rerank_documents(self, query: str, docs: list[dict[str, Any]], top_n: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
        if len(docs) <= 1:
            return docs[:top_n]

        client = self._get_cohere_client()
        if not client:
            ranked = sorted(docs, key=lambda item: item.get("score", 0.0), reverse=True)
            for item in ranked:
                item["rerank_source"] = "score_fallback"
            return ranked[:top_n]

        try:
            response = client.rerank(
                model=RERANK_MODEL,
                query=query,
                documents=[doc.get("content", "") for doc in docs],
                top_n=min(top_n, len(docs)),
            )
        except Exception as exc:
            print(f"⚠️ Cohere rerank failed: {exc}")
            ranked = sorted(docs, key=lambda item: item.get("score", 0.0), reverse=True)
            for item in ranked:
                item["rerank_source"] = "score_fallback"
            return ranked[:top_n]

        ranked_docs = []
        for result in response.results:
            doc = dict(docs[result.index])
            doc["rerank_score"] = float(result.relevance_score or 0.0)
            doc["rerank_source"] = "cohere"
            ranked_docs.append(doc)
        return ranked_docs

    def hybrid_retrieve(
        self,
        document_id: str,
        query: str,
        chunks: list[dict[str, Any]] | None = None,
        top_k: int = DEFAULT_TOP_K,
        prefetch_k: int = DEFAULT_PREFETCH_K,
    ) -> list[dict[str, Any]]:
        chunks = chunks or []
        bm25_results = self.bm25_retrieve(chunks, query, top_k=prefetch_k)
        vector_results = self.vector_retrieve(document_id, query, top_k=prefetch_k)

        combined: list[dict[str, Any]] = []
        seen_keys: set[tuple[Any, ...]] = set()
        for doc in vector_results + bm25_results:
            metadata = doc.get("metadata") or {}
            key = (
                metadata.get("chunk_id"),
                metadata.get("page_number"),
                doc.get("content", "")[:120],
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            combined.append(doc)

        if not combined:
            return bm25_results[:top_k]
        return self.rerank_documents(query, combined, top_n=top_k)


@lru_cache(maxsize=1)
def get_hosted_retrieval_service() -> HostedRetrievalService:
    return HostedRetrievalService()
