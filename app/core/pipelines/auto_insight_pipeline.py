from app.core.pipelines.embedding_pipeline import store_chunks
from app.core.generation.contract_analyzer import LLMContractAnalyzer

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

        # Step 3: Extract text only
        docs = [chunk["content"] for chunk in chunks]

        # Step 4: Take strategic chunks (Intro/Summary priority)
        # Instead of just longest, take first 15 chunks to preserve logical flow
        selected_docs = docs[:15]
        
        print(f"\n--- RETRIEVED CHUNKS FOR UPLOAD ANALYSIS ---")
        for i, chunk_text in enumerate(selected_docs):
            print(f"Chunk {i+1}: {chunk_text[:200]}...\n")
        print(f"--- END CHUNKS ---\n")
        
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
        }

        # Step 9: Save result to persistent store
        self.insight_store.save(document_id, combined_result)

        return combined_result

