from app.core.contracts.clause_tagger import infer_clause_type, normalize_heading
from app.core.contracts.contract_classifier import classify_contract
from app.core.contracts.term_extractor import (
    extract_effective_date,
    extract_governing_law,
    extract_parties,
    extract_payment_structure,
    extract_renewal_mechanics,
    extract_term_length,
)


def build_clause_records(chunks: list[dict]) -> list[dict]:
    clause_records = []
    clause_lookup = {}

    for chunk in chunks:
        metadata = chunk["metadata"]
        normalized_heading = normalize_heading(metadata.get("section_heading", ""))
        clause_type = infer_clause_type(normalized_heading, chunk["content"])

        metadata["section_heading"] = normalized_heading
        metadata["clause_title"] = normalized_heading
        metadata["clause_type"] = clause_type

        if not normalized_heading:
            continue

        existing_clause = clause_lookup.get(normalized_heading)
        if existing_clause:
            existing_clause["chunk_ids"].append(metadata["chunk_id"])
            existing_clause["clause_text"] = (
                f"{existing_clause['clause_text']}\n\n{chunk['content']}".strip()
            )
            existing_clause["text_preview"] = existing_clause["clause_text"][:240].strip()
            continue

        clause_record = {
            "title": normalized_heading,
            "type": clause_type,
            "chunk_id": metadata["chunk_id"],
            "page_number": metadata.get("page_number", 1),
            "chunk_ids": [metadata["chunk_id"]],
            "clause_text": chunk["content"],
            "text_preview": chunk["content"][:240].strip(),
        }
        clause_lookup[normalized_heading] = clause_record
        clause_records.append(clause_record)

    return clause_records


def build_contract_profile(document_id: str, chunks: list[dict]) -> dict:
    full_text = "\n\n".join(chunk["content"] for chunk in chunks)
    contract_type = classify_contract(full_text)

    clause_records = build_clause_records(chunks)
    clause_index = [
        {
            "title": clause["title"],
            "type": clause["type"],
            "chunk_id": clause["chunk_id"],
            "page_number": clause["page_number"],
        }
        for clause in clause_records
    ]

    return {
        "document_id": document_id,
        "document_type": contract_type["document_type"],
        "classification_confidence": contract_type["confidence"],
        "parties": extract_parties(chunks),
        "effective_date": extract_effective_date(full_text),
        "governing_law": extract_governing_law(full_text),
        "term_length": extract_term_length(full_text),
        "renewal_mechanics": extract_renewal_mechanics(full_text),
        "payment_structure": extract_payment_structure(full_text, contract_type["document_type"]),
        "clause_index": clause_index,
    }
