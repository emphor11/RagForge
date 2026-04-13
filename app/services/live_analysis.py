from typing import Callable, Optional

from app.core.generation.contract_analyzer import LLMContractAnalyzer
from app.core.generation.structured_generator import StructuredGenerator
from app.core.ingestion.pipeline import ingest_document
from app.core.retrieval.bm25_retriever import BM25Retriever
from app.db.insight_store import InsightStore


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


def run_live_analysis(document_id: str, file_path: str, progress_callback: Optional[Callable[[str, int, Optional[str]], None]] = None):
    analyzer = LLMContractAnalyzer()
    generator = StructuredGenerator()
    store = InsightStore()

    _emit(progress_callback, "parsing_document", 15, "Reading and chunking the contract")
    chunks, raw_text = ingest_document(file_path, document_id)

    _emit(progress_callback, "building_context", 35, "Selecting the most relevant clauses")
    selected_chunks = _select_live_chunks(chunks, max_chunks=LIVE_MAX_CHUNKS)
    selected_docs = [
        chunk["content"]
        for chunk in selected_chunks[:LIVE_CONTEXT_DOCS]
        if chunk.get("content")
    ]

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
                "mode": "manual_verify_required",
                "recommendation": "Run Verify only if this file should be treated as a contract.",
            },
            "review_audit": {
                "score": 0,
                "status": "deferred",
                "mode": "manual_verify_required",
            },
            "analysis_chunks": selected_chunks,
            "raw_text": raw_text,
            "analysis_mode": "groq_live",
        }
        _emit(progress_callback, "saving_results", 90, "Saving analysis results")
        store.save(document_id, result)
        return result

    clause_records = analyzer.extract_clauses(selected_chunks)
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

    result = {
        "contract_profile": contract_profile,
        "clauses": clause_records,
        "review_findings": review_findings,
        "insights": insights,
        "evaluation": {
            "score": 0,
            "status": "deferred",
            "mode": "manual_verify_required",
            "recommendation": "Run Verify for deep semantic evaluation and heavier reranking.",
        },
        "review_audit": {
            "score": 0,
            "status": "deferred",
            "mode": "manual_verify_required",
        },
        "analysis_chunks": selected_chunks,
        "raw_text": raw_text,
        "analysis_mode": "groq_live",
        "retrieval_debug": {
            "selected_chunk_ids": [
                chunk.get("metadata", {}).get("chunk_id")
                for chunk in selected_chunks
                if chunk.get("metadata", {}).get("chunk_id") is not None
            ],
            "selected_count": len(selected_chunks),
        },
    }

    _emit(progress_callback, "saving_results", 90, "Saving analysis results")
    store.save(document_id, result)
    return result
