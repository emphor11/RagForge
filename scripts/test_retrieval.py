import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.ingestion.pipeline import ingest_document
from app.core.pipelines.embedding_pipeline import store_chunks
from app.core.vector_retriever import VectorRetriever
from app.core.bm25_retriever import BM25Retriever
from app.core.hybrid_retriever import HybridRetriever

# Step 1: Ingest
chunks = ingest_document("test.txt")

# Step 2: Store embeddings
store_chunks(chunks)

# Step 3: Init retrievers
vector = VectorRetriever()
bm25 = BM25Retriever(chunks)

hybrid = HybridRetriever(vector, bm25)

# Step 4: Query
results = hybrid.retrieve("your query here", k=5)

for r in results:
    print(r["content"][:200])
    print("Score:", r["score"])
    print("------")