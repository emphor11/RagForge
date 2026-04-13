from typing import Callable, Optional

from app.core.generation.contract_analyzer import LLMContractAnalyzer
from app.core.generation.structured_generator import StructuredGenerator
from app.core.ingestion.pipeline import ingest_document
from app.core.retrieval.bm25_retriever import BM25Retriever
from app.db.insight_store import InsightStore
from app.services.groq_evaluator import GroqReviewEvaluator
from app.services.retrieval import get_hosted_retrieval_service


LIVE_MAX_CHUNKS = 40
LIVE_CONTEXT_DOCS = 15
LIVE_QUERY = (
    "Extract the most important contract context covering parties, effective date, "
    "governing law, term, termination rights, payment terms, confidentiality, "
    "liability, indemnity, data use, and dispute handling."
)


def _emit(progress_callback: Optional[Callable[[str, int, Optional[str]], None]], stage: str, progress: int, detail: Optional[str] = None):
    if progress_callback:
        progress_callback(stage, progress, detail)


def _select_live_chunks(chunks: list[dict], max_chunks: int = LIVE_MAX_CHUNKS):
    if not chunks:
        return []

    leading = chunks[: min(5, len(chunks))]
    bm25 = BM25Retriever(chunks)
    ranked = bm25.retrieve(LIVE_QUERY, k=min(max_chunks, len(chunks)))

    ordered = []
    seen = set()
    for chunk in leading + ranked:
        chunk_id = chunk.get("metadata", {}).get("chunk_id")
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        ordered.append(chunk)
        if len(ordered) >= max_chunks:
            break

    return ordered


def _select_context_docs(retrieved_docs: list[dict], fallback_chunks: list[dict]) -> tuple[list[str], list[int], str]:
    if retrieved_docs:
        docs = [doc.get("content", "") for doc in retrieved_docs if doc.get("content")]
        chunk_ids = [
            doc.get("metadata", {}).get("chunk_id")
            for doc in retrieved_docs
            if doc.get("metadata", {}).get("chunk_id") is not None
        ]
        return docs[:LIVE_CONTEXT_DOCS], chunk_ids, "hybrid_reranked"

    selected_chunks = _select_live_chunks(fallback_chunks, max_chunks=LIVE_MAX_CHUNKS)
    docs = [
        chunk.get("content", "")
        for chunk in selected_chunks[:LIVE_CONTEXT_DOCS]
        if chunk.get("content")
    ]
    chunk_ids = [
        chunk.get("metadata", {}).get("chunk_id")
        for chunk in selected_chunks
        if chunk.get("metadata", {}).get("chunk_id") is not None
    ]
    return docs, chunk_ids, "bm25_fallback"


def run_live_analysis(document_id: str, file_path: str, progress_callback: Optional[Callable[[str, int, Optional[str]], None]] = None):
    analyzer = LLMContractAnalyzer()
    generator = StructuredGenerator()
    evaluator = GroqReviewEvaluator()
    retrieval = get_hosted_retrieval_service()
    store = InsightStore()

    _emit(progress_callback, "parsing_document", 15, "Reading and chunking the contract")
    chunks, raw_text = ingest_document(file_path, document_id)

    _emit(progress_callback, "building_context", 35, "Selecting the most relevant clauses")
    vector_store_stats = retrieval.store_document_chunks(document_id, chunks[:LIVE_MAX_CHUNKS])
    retrieved_docs = retrieval.hybrid_retrieve(
        document_id=document_id,
        query=LIVE_QUERY,
        chunks=chunks[:LIVE_MAX_CHUNKS],
        top_k=LIVE_CONTEXT_DOCS,
    )
    selected_docs, selected_chunk_ids, retrieval_mode = _select_context_docs(retrieved_docs, chunks)

    if not selected_docs and raw_text:
        selected_docs = [raw_text[:15000]]

    _emit(progress_callback, "analysing_contract", 60, "Extracting profile, clauses, and risks")
    contract_profile = analyzer.extract_profile(document_id, "\n\n".join(selected_docs))
    if not contract_profile:
        raise ValueError("Failed to classify and extract the contract profile.")

    if not contract_profile.get("is_legal_document", True):
        result = {
            "contract_profile": contract_profile,
            "clauses": [],
            "review_findings": [],
            "insights": {
                "summary": "Analysis skipped because the uploaded file does not appear to be a formal legal agreement.",
                "key_insights": [],
                "risks": [],
                "recommended_actions": [],
                "reasoning": "The live Groq analysis path identified this file as non-legal content.",
                "overall_confidence": 0.0,
                "context_quality": "insufficient",
                "context_gap": "Document is not a legal agreement.",
            },
            "evaluation": {
                "score": 0,
                "status": "deferred",
                "mode": "non_legal_document",
                "recommendation": "Analysis stopped because the uploaded file does not appear to be a legal agreement.",
            },
            "review_audit": {
                "score": 0,
                "status": "deferred",
                "mode": "non_legal_document",
            },
            "analysis_chunks": chunks[:LIVE_MAX_CHUNKS],
            "raw_text": raw_text,
            "analysis_mode": "groq_live",
        }
        _emit(progress_callback, "saving_results", 90, "Saving analysis results")
        store.save(document_id, result)
        return result

    clause_input_chunks = retrieved_docs if retrieved_docs else _select_live_chunks(chunks, max_chunks=LIVE_MAX_CHUNKS)
    clause_records = analyzer.extract_clauses(clause_input_chunks)
    contract_profile["clause_index"] = [
        {
            "title": clause["title"],
            "type": clause["type"],
            "chunk_id": clause["chunk_id"],
            "page_number": clause["page_number"],
        }
        for clause in clause_records
    ]
    review_findings = analyzer.spot_issues(contract_profile, clause_records)

    insights = generator.generate(
        docs=selected_docs,
        mode="document",
        document_type=contract_profile.get("document_type"),
    )
    evaluation, review_audit = evaluator.evaluate(
        findings=review_findings,
        context_docs=selected_docs,
        clauses=clause_records,
    )

    result = {
        "contract_profile": contract_profile,
        "clauses": clause_records,
        "review_findings": review_findings,
        "insights": insights,
        "evaluation": evaluation,
        "review_audit": review_audit,
        "analysis_chunks": chunks[:LIVE_MAX_CHUNKS],
        "raw_text": raw_text,
        "analysis_mode": "groq_live",
        "verification_summary": "Hosted Fast Review completed with hybrid retrieval, reranked context, and Groq grounding checks.",
        "retrieval_debug": {
            "mode": retrieval_mode,
            "selected_chunk_ids": selected_chunk_ids,
            "selected_count": len(selected_docs),
            "stored_vectors": vector_store_stats.get("stored_vectors", 0),
            "vector_mode": vector_store_stats.get("mode", "bm25_only"),
            "rerank_enabled": retrieval.has_reranker(),
        },
    }

    _emit(progress_callback, "saving_results", 90, "Saving analysis results")
    store.save(document_id, result)
    return result
