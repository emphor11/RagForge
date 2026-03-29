import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.pipelines.auto_insight_pipeline import AutoInsightPipeline
from app.db.insight_store import InsightStore
from app.core.generation.structured_generator import StructuredGenerator
from app.core.ingestion.pipeline import ingest_document


pipeline = AutoInsightPipeline(
    ingestion_pipeline=ingest_document,
    generator=StructuredGenerator(),
    insight_store=InsightStore()
)

result = pipeline.run(
    file_path="test.txt",
    document_id="doc1"
)

print(result)