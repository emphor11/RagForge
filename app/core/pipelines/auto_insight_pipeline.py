class AutoInsightPipeline:
    def __init__(self, ingestion_pipeline, generator, insight_store):
        self.ingestion_pipeline = ingestion_pipeline
        self.generator = generator
        self.insight_store = insight_store

    def run(self, file_path: str, document_id: str):
        # Step 1: Ingest document → chunks
        chunks = self.ingestion_pipeline(file_path)

        # Step 2: Extract text only
        docs = [chunk["content"] for chunk in chunks]

        # Step 3: Take top chunks (simple version)
        # select longer, richer chunks
        selected_docs = sorted(docs, key=lambda x: len(x), reverse=True)[:10]

        # Step 4: Generate intelligence (NO QUERY)
        result = self.generator.generate(
            docs=selected_docs,
            mode="document"
        )

        # Step 5: Save result
        self.insight_store.save(document_id, result)

        return result