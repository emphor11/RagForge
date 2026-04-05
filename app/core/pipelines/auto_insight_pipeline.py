from app.core.pipelines.embedding_pipeline import store_chunks
from app.core.generation.contract_analyzer import LLMContractAnalyzer
from app.core.retrieval.vector_retriever import VectorRetriever
from app.core.retrieval.bm25_retriever import BM25Retriever
from app.core.retrieval.hybrid_retriever import HybridRetriever
from app.core.reranking.reranker import Reranker

class AutoInsightPipeline:
    def __init__(self, ingestion_pipeline, generator, insight_store, evaluator=None):
        self.ingestion_pipeline = ingestion_pipeline
        self.generator = generator
        self.insight_store = insight_store
        self.evaluator = evaluator
        self.contract_analyzer = LLMContractAnalyzer()

    def run(self, file_path: str, document_id: str):
        # Step 1: Ingest document → chunks
        chunks = self.ingestion_pipeline(file_path, document_id)

        # Step 2: Store chunks in vector DB (added for RAG)
        store_chunks(chunks)

        # Step 3: Select strategic chunks using retrieval (real RAG-style selection)
        # Previously this was `docs[:15]`, which is not relevance-based.
        retrieval_query = (
            "Extract key contract context: parties, effective date, governing law, "
            "term and termination rights, payment terms, confidentiality obligations, "
            "liability and indemnity protections."
        )

        vector = VectorRetriever()
        bm25 = BM25Retriever(chunks)
        hybrid = HybridRetriever(vector, bm25)

        # Retrieve a larger candidate set, then rerank down to the context budget.
        candidate_docs = hybrid.retrieve(retrieval_query, k=30, document_id=document_id)
        reranker = Reranker()
        top_docs = reranker.rerank(retrieval_query, candidate_docs, top_k=15)

        selected_docs = [doc["content"] for doc in top_docs if doc.get("content")]
        selected_chunk_ids = [
            doc.get("metadata", {}).get("chunk_id")
            for doc in top_docs
            if doc.get("metadata", {}).get("chunk_id") is not None
        ]

        retrieval_debug = {
            "retrieval_query": retrieval_query,
            "candidate_count": len(candidate_docs),
            "selected_count": len(selected_docs),
            "selected_chunk_ids": selected_chunk_ids,
        }

        print(f"\n--- RETRIEVAL DEBUG (UPLOAD) ---")
        print(f"Candidate docs: {retrieval_debug['candidate_count']}")
        print(f"Selected docs: {retrieval_debug['selected_count']}")
        print(f"Selected chunk ids: {retrieval_debug['selected_chunk_ids']}")
        print(f"--- END RETRIEVAL DEBUG ---\n")

        context = "\n\n".join(selected_docs)

        # Step 5: Advanced LLM Contract Metadata Extraction
        # Extract profile from preamble/intro context
        contract_profile = self.contract_analyzer.extract_profile(document_id, context)
        
        # Extract specific clauses from chunks
        clause_records = self.contract_analyzer.extract_clauses(chunks)
        contract_profile["clause_index"] = [
            {"title": c["title"], "type": c["type"], "chunk_id": c["chunk_id"], "page_number": c["page_number"]}
            for c in clause_records
        ]
        
        # Issue spotting acting as legal reviewer
        review_findings = self.contract_analyzer.spot_issues(contract_profile, clause_records)

        # Step 6: Generate general structure/opportunities intelligence
        insights = self.generator.generate(
            docs=selected_docs,
            mode="document"
        )

        # Step 7: Evaluate Insights
        evaluation = {}
        review_audit = {}
        if self.evaluator:
            evaluation = self.evaluator.run(insights, context)
            review_audit = self.evaluator.evaluate_legal_review(
                review_findings=review_findings,
                clauses=clause_records,
                contract_profile=contract_profile,
            )

        # Step 8: Combined Data Object (Safe Storage)
        combined_result = {
            "contract_profile": contract_profile,
            "clauses": clause_records,
            "review_findings": review_findings,
            "insights": insights,
            "evaluation": evaluation,
            "review_audit": review_audit,
            "retrieval_debug": retrieval_debug,
        }

        # Step 9: Save result to persistent store
        self.insight_store.save(document_id, combined_result)

        return combined_result

