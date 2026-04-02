import re


CLAUSE_QUERY_PATTERNS = {
    "governing_law": [r"governing law", r"which law", r"laws? of", r"jurisdiction", r"venue", r"arbitration", r"dispute"],
    "termination": [r"termination", r"terminate", r"notice period", r"for convenience", r"for cause", r"exit"],
    "payment": [r"payment", r"fees?", r"pricing", r"invoic", r"amount due"],
    "liability_cap": [r"liability", r"liability cap", r"limitation of liability", r"uncapped"],
    "indemnity": [r"indemn", r"third[- ]party claims?"],
    "confidentiality_definition": [r"confidential", r"confidential information", r"non-disclosure"],
    "permitted_use_and_non_disclosure": [r"use of information", r"disclose", r"non-disclosure", r"permitted use"],
    "return_or_destruction": [r"return", r"destroy", r"destruction"],
    "term_and_survival": [r"term", r"survival", r"remain in effect", r"duration"],
    "entire_agreement": [r"entire agreement", r"amendment", r"assignment"],
}


def detect_clause_types(query: str) -> list[str]:
    query_lower = query.lower()
    matched = []
    for clause_type, patterns in CLAUSE_QUERY_PATTERNS.items():
        if any(re.search(pattern, query_lower) for pattern in patterns):
            matched.append(clause_type)
    return matched


def select_contract_query_docs(query: str, contract_data: dict, max_clauses: int = 4) -> list[dict]:
    clauses = contract_data.get("clauses", []) or []
    if not clauses:
        return []

    clause_types = detect_clause_types(query)
    selected = []

    if clause_types:
        for clause_type in clause_types:
            for clause in clauses:
                if clause.get("type") == clause_type:
                    selected.append(clause)
        # Keep order stable while deduplicating by heading
        deduped = []
        seen_titles = set()
        for clause in selected:
            title = clause.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                deduped.append(clause)
        return deduped[:max_clauses]

    query_terms = {term for term in re.findall(r"[a-zA-Z]{4,}", query.lower())}
    scored = []
    for clause in clauses:
        haystack = f"{clause.get('title', '')} {clause.get('type', '')} {clause.get('clause_text', '')}".lower()
        overlap = sum(1 for term in query_terms if term in haystack)
        if overlap > 0:
            scored.append((overlap, clause))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [clause for _, clause in scored[:max_clauses]]
