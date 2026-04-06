import json
import os
import sys

from app.core.pipelines.auto_insight_pipeline import AutoInsightPipeline
from app.core.ingestion.pipeline import build_pipeline
from app.core.generation.structured_generator import StructuredGenerator
from app.db.insight_store import InsightStore

def main():
    file_path = "insights/Untitled document (4).docx"
    
    if not os.path.exists(file_path):
        print("Test file not found")
        sys.exit(1)
        
    ingestion = build_pipeline()
    generator = StructuredGenerator()
    insight_store = InsightStore()
    pipeline = AutoInsightPipeline(ingestion, generator, insight_store)
    
    result = pipeline.run(file_path, os.path.basename(file_path))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
