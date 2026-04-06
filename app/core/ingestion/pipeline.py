from .document_parser import parse_document
from .chunker import chunk_text


def ingest_document(file_path: str, document_id: str):
    parsed = parse_document(file_path)
    chunks = chunk_text(
        parsed["text"],
        document_id=document_id,
        page_spans=parsed.get("pages", []),
    )
    return chunks, parsed["text"]
