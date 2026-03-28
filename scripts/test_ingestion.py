import sys
import os

# Add the project root to sys.path so 'app' can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.ingestion.pipeline import ingest_document

chunks = ingest_document("test.txt")

print(f"Total chunks: {len(chunks)}")
print(chunks[0])