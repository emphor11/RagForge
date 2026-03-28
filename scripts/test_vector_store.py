import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.ingestion.pipeline import ingest_document
from app.core.pipelines.embedding_pipeline import store_chunks

chunks = ingest_document("test.txt")

store_chunks(chunks)

print("Stored successfully")
