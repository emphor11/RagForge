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


def build_contract_profile(document_id: str, chunks: list[dict]) -> dict:
    full_text = "\n\n".join(chunk["content"] for chunk in chunks)
    contract_type = classify_contract(full_text)

    clause_index = []
    seen_headings = set()
    for chunk in chunks:
        metadata = chunk["metadata"]
        normalized_heading = normalize_heading(metadata.get("section_heading", ""))
        clause_type = infer_clause_type(normalized_heading, chunk["content"])
        metadata["section_heading"] = normalized_heading
        metadata["clause_title"] = normalized_heading
        metadata["clause_type"] = clause_type

        if normalized_heading and normalized_heading not in seen_headings:
            seen_headings.add(normalized_heading)
            clause_index.append({
                "title": normalized_heading,
                "type": clause_type,
                "chunk_id": metadata["chunk_id"],
                "page_number": metadata.get("page_number", 1),
            })

    return {
        "document_id": document_id,
        "document_type": contract_type["document_type"],
        "classification_confidence": contract_type["confidence"],
        "parties": extract_parties(chunks),
        "effective_date": extract_effective_date(full_text),
        "governing_law": extract_governing_law(full_text),
        "term_length": extract_term_length(full_text),
        "renewal_mechanics": extract_renewal_mechanics(full_text),
        "payment_structure": extract_payment_structure(full_text),
        "clause_index": clause_index,
    }
