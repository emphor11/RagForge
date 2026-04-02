from app.core.pipelines.embedding_pipeline import store_chunks
from app.core.contracts.profile_builder import build_clause_records, build_contract_profile

class AutoInsightPipeline:
    def __init__(self, ingestion_pipeline, generator, insight_store, evaluator=None):
        self.ingestion_pipeline = ingestion_pipeline
        self.generator = generator
        self.insight_store = insight_store
        self.evaluator = evaluator

    def run(self, file_path: str, document_id: str):
        # Step 1: Ingest document → chunks
        chunks = self.ingestion_pipeline(file_path, document_id)

        # Step 1.5: Build contract profile + normalize clause metadata
        contract_profile = build_contract_profile(document_id, chunks)
        clause_records = build_clause_records(chunks)

        # Step 2: Store chunks in vector DB (added for RAG)
        store_chunks(chunks)

        # Step 3: Extract text only
        docs = [chunk["content"] for chunk in chunks]

        # Step 4: Take strategic chunks (Intro/Summary priority)
        # Instead of just longest, take first 15 chunks to preserve logical flow
        selected_docs = docs[:15]
        context = "\n\n".join(selected_docs)

        # Step 5: Generate intelligence
        insights = self.generator.generate(
            docs=selected_docs,
            mode="document"
        )

        # Step 6: Evaluate Insights (New Evaluation Layer)
        evaluation = {}
        if self.evaluator:
            evaluation = self.evaluator.run(insights, context)

        # Step 7: Combined Data Object (Safe Storage)
        combined_result = {
            "contract_profile": contract_profile,
            "clauses": clause_records,
            "insights": insights,
            "evaluation": evaluation
        }

        # Step 8: Save result to persistent store
        self.insight_store.save(document_id, combined_result)

        return combined_result
