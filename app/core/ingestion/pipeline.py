from .loader import load_document
from .chunker import chunk_text


def ingest_document(file_path: str):
    text = load_document(file_path)
    chunks = chunk_text(text, source=file_path)
    return chunks