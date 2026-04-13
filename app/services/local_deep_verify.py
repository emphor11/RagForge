from __future__ import annotations

import json
import os
import re
from hashlib import sha1
from typing import Any

from app.core.embeddings.embedder import Embedder
from app.core.ingestion.chunker import chunk_text
from app.core.retrieval.bm25_retriever import BM25Retriever
from app.core.reranking.reranker import Reranker
from app.db.chroma_store import ChromaStore
from app.evaluation.evaluator import InsightEvaluator


LOCAL_VERIFY_QUERY = (
    "parties effective date governing law payment obligations term termination "
    "liability indemnity confidentiality intellectual property dispute resolution "
    "missing protections negotiation points"
)
LOCAL_TOP_K = 12
FINDING_TOP_K = 4


def _slug_collection_name(document_id: str) -> str:
    digest = sha1(document_id.encode("utf-8")).hexdigest()[:20]
    return f"verify_{digest}"


def _sanitize_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"pass", "verified", "ok"}:
        return "pass"
    if normalized in {"needs_review", "review_required"}:
        return "needs_review"
    if normalized in {"fail", "failed"}:
        return "fail"
    return "needs_review"


def _finding_query(finding: dict[str, Any]) -> str:
    parts = [
        finding.get("title", ""),
        finding.get("finding_type", ""),
        finding.get("clause_type", ""),
        finding.get("explanation", ""),
        " ".join(finding.get("clause_refs", [])[:3]),
    ]
    return " ".join(part for part in parts if part).strip()


def _merge_docs(vector_docs: list[dict[str, Any]], bm25_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined: dict[tuple[Any, ...], dict[str, Any]] = {}
    for doc in vector_docs:
        metadata = doc.get("metadata") or {}
        key = (
            metadata.get("chunk_id"),
            metadata.get("page_number"),
            doc.get("content", "")[:80],
        )
        combined[key] = doc
    for doc in bm25_docs:
        metadata = doc.get("metadata") or {}
        key = (
            metadata.get("chunk_id"),
            metadata.get("page_number"),
            doc.get("content", "")[:80],
        )
        if key in combined:
            combined[key]["score"] = float(combined[key].get("score", 0.0)) + float(doc.get("score", 0.0))
        else:
            combined[key] = doc
    return list(combined.values())


class LocalHybridVerifier:
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.collection_name = _slug_collection_name(document_id)
        self.embedder = Embedder()
        self.reranker = Reranker()
        self.vector_store = ChromaStore(collection_name=self.collection_name)
        self.evaluator = InsightEvaluator()

    def _vector_retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        query_embedding = self.embedder.embed([query])[0]
        results = self.vector_store.query(
            query_embedding,
            n_results=top_k,
            where={"source": self.document_id},
        )
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        return [
            {
                "content": doc,
                "metadata": meta,
                "score": 1 / (1 + float(dist)),
                "retrieval_source": "vector",
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

    def build_index(self, chunks: list[dict[str, Any]]):
        self.vector_store.delete_documents(source=self.document_id)
        texts = [chunk["content"] for chunk in chunks if chunk.get("content")]
        if not texts:
            return
        embeddings = self.embedder.embed(texts)
        self.vector_store.add_documents(chunks, embeddings)

    def hybrid_retrieve(self, query: str, chunks: list[dict[str, Any]], top_k: int = LOCAL_TOP_K) -> list[dict[str, Any]]:
        bm25 = BM25Retriever(chunks)
        bm25_docs = bm25.retrieve(query, k=max(top_k, LOCAL_TOP_K))
        vector_docs = self._vector_retrieve(query, top_k=max(top_k, LOCAL_TOP_K))
        merged = _merge_docs(vector_docs, bm25_docs)
        return self.reranker.rerank(query, merged, top_k=top_k)

    def build_verification_result(self, source_document: dict[str, Any]) -> dict[str, Any]:
        raw_text = source_document.get("raw_text", "") or ""
        if not raw_text.strip():
            raise ValueError("Deep Verify requires raw_text in the hosted document payload.")

        os.environ.setdefault("LOCAL_MODEL_FILES_ONLY", "false")

        document_id = (
            source_document.get("contract_profile", {}).get("document_id")
            or source_document.get("document_id")
            or self.document_id
        )
        chunks = chunk_text(raw_text, document_id=document_id)
        self.build_index(chunks)

        base_context_docs = self.hybrid_retrieve(LOCAL_VERIFY_QUERY, chunks, top_k=LOCAL_TOP_K)
        base_context_texts = [doc.get("content", "") for doc in base_context_docs if doc.get("content")]

        evidence_by_finding = []
        enhanced_findings = []
        for finding in source_document.get("review_findings", [])[:12]:
            query = _finding_query(finding)
            supporting_docs = self.hybrid_retrieve(query or LOCAL_VERIFY_QUERY, chunks, top_k=FINDING_TOP_K)
            evidence = [doc.get("content", "") for doc in supporting_docs if doc.get("content")]
            evidence_by_finding.append(
                {
                    "title": finding.get("title", ""),
                    "query": query,
                    "evidence": evidence,
                }
            )
            updated_finding = dict(finding)
            if evidence:
                updated_finding["verification_context"] = evidence[:2]
                if not updated_finding.get("source_quotes"):
                    updated_finding["source_quotes"] = evidence[:1]
            enhanced_findings.append(updated_finding)

        insights = dict(source_document.get("insights") or {})
        insights["deep_verify_context"] = base_context_texts[:6]

        evaluation = self.evaluator.run(insights, raw_text)
        review_audit = self.evaluator.evaluate_legal_review(
            enhanced_findings,
            source_document.get("clauses", []) or [],
            source_document.get("contract_profile", {}) or {},
        )

        return {
            "chunks": chunks,
            "base_context_docs": base_context_docs,
            "base_context_texts": base_context_texts,
            "enhanced_findings": enhanced_findings,
            "evaluation": evaluation,
            "review_audit": review_audit,
            "evidence_by_finding": evidence_by_finding,
            "retrieval_debug": {
                "mode": "local_hybrid_reranked",
                "chunk_count": len(chunks),
                "selected_chunk_ids": [
                    doc.get("metadata", {}).get("chunk_id")
                    for doc in base_context_docs
                    if doc.get("metadata", {}).get("chunk_id") is not None
                ],
                "selected_count": len(base_context_docs),
            },
        }


def build_ollama_prompt(source_document: dict[str, Any], parity_result: dict[str, Any], max_context_chars: int) -> str:
    contract_profile = source_document.get("contract_profile", {})
    findings = parity_result.get("enhanced_findings", [])
    evidence_by_finding = parity_result.get("evidence_by_finding", [])
    retrieved_context = "\n\n".join(parity_result.get("base_context_texts", [])[:8])[:max_context_chars]

    compact_findings = [
        {
            "title": finding.get("title"),
            "finding_type": finding.get("finding_type"),
            "clause_type": finding.get("clause_type"),
            "severity": finding.get("severity"),
            "explanation": finding.get("explanation"),
            "source_quotes": finding.get("source_quotes", [])[:2],
            "verification_context": finding.get("verification_context", [])[:2],
        }
        for finding in findings[:12]
    ]

    prompt = f"""
You are performing a deep legal verification pass using retrieval-backed evidence.
Return ONLY valid JSON with this exact shape:
{{
  "verification_summary": "short summary",
  "evaluation": {{
    "score": 0,
    "status": "pass or needs_review or fail",
    "recommendation": "short recommendation",
    "issues": ["..."]
  }},
  "review_audit": {{
    "score": 0,
    "status": "pass or needs_review or fail",
    "recommendation": "short recommendation",
    "grounding_score": 0.0,
    "structure_score": 0.0,
    "coverage_score": 0.0,
    "issues": ["..."]
  }},
  "review_findings": [
    {{
      "title": "same title",
      "confidence": 0.0,
      "verification_note": "short note"
    }}
  ]
}}

Rules:
- Scores must stay between 0 and 100.
- grounding_score, structure_score, coverage_score must stay between 0.0 and 1.0.
- review_findings must return one item for each input finding, matched by title.
- Use the retrieved evidence below to verify or weaken findings.
- If evidence is weak or contradictory, lower confidence.
- Do not return markdown.

Contract profile:
{json.dumps(contract_profile, ensure_ascii=True)}

Retrieval-backed findings:
{json.dumps(compact_findings, ensure_ascii=True)}

Evidence by finding:
{json.dumps(evidence_by_finding[:12], ensure_ascii=True)}

Retrieved contract context:
{retrieved_context}
"""
    return prompt


def merge_verified_findings(
    original_findings: list[dict[str, Any]],
    verified_findings: list[dict[str, Any]],
    parity_result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    parity_result = parity_result or {}
    indexed = {
        item.get("title", "").strip(): item
        for item in verified_findings
        if item.get("title")
    }
    evidence_map = {
        item.get("title", "").strip(): item
        for item in parity_result.get("evidence_by_finding", [])
        if item.get("title")
    }

    merged = []
    for finding in original_findings:
        key = finding.get("title", "").strip()
        patch = indexed.get(key, {})
        evidence = evidence_map.get(key, {})
        updated = dict(finding)
        if "confidence" in patch:
            updated["confidence"] = patch["confidence"]
        if patch.get("verification_note"):
            updated["verification_note"] = patch["verification_note"]
        if evidence.get("evidence"):
            updated["verification_context"] = evidence["evidence"][:2]
        merged.append(updated)
    return merged


def build_final_verification_payload(
    source_document: dict[str, Any],
    parity_result: dict[str, Any],
    ollama_result: dict[str, Any] | None,
    provider: str,
) -> dict[str, Any]:
    ollama_result = ollama_result or {}
    verified_findings = ollama_result.get("review_findings", [])
    merged_findings = merge_verified_findings(
        source_document.get("review_findings", []),
        verified_findings,
        parity_result=parity_result,
    )

    evaluation = dict(parity_result.get("evaluation", {}))
    review_audit = dict(parity_result.get("review_audit", {}))

    llm_evaluation = ollama_result.get("evaluation") or {}
    llm_audit = ollama_result.get("review_audit") or {}

    if llm_evaluation.get("recommendation"):
        evaluation["recommendation"] = llm_evaluation["recommendation"]
    if llm_evaluation.get("issues"):
        evaluation["issues"] = sorted(
            set((evaluation.get("issues") or []) + llm_evaluation.get("issues", []))
        )

    if llm_audit.get("recommendation"):
        review_audit["recommendation"] = llm_audit["recommendation"]
    if llm_audit.get("issues"):
        review_audit["issues"] = sorted(
            set((review_audit.get("issues") or []) + llm_audit.get("issues", []))
        )

    metrics = review_audit.get("metrics", {}) if isinstance(review_audit.get("metrics"), dict) else {}
    if "grounding_score" not in review_audit:
        review_audit["grounding_score"] = round(float(metrics.get("grounding", 0)) / 100.0, 4)
    if "structure_score" not in review_audit:
        review_audit["structure_score"] = round(float(metrics.get("structure", 0)) / 100.0, 4)
    if "coverage_score" not in review_audit:
        review_audit["coverage_score"] = round(float(metrics.get("completeness", 0)) / 100.0, 4)

    review_audit["status"] = _sanitize_status(str(review_audit.get("status", "needs_review")))
    evaluation["status"] = _sanitize_status(str(evaluation.get("status", "needs_review")))

    verification_summary = ollama_result.get(
        "verification_summary",
        "Deep verification completed with local hybrid retrieval, reranking, evaluator checks, and Ollama review.",
    )

    return {
        "verification_mode": "local_ollama_parity",
        "verification_provider": provider,
        "verification_summary": verification_summary,
        "evaluation": evaluation,
        "review_audit": review_audit,
        "review_findings": merged_findings,
        "verification_debug": {
            "local_retrieval": parity_result.get("retrieval_debug", {}),
            "evidence_by_finding": parity_result.get("evidence_by_finding", []),
        },
    }
