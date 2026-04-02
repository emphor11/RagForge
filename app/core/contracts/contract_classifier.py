import re


CONTRACT_TYPES = {
    "msa": {
        "strong": [r"master services agreement", r"\bmsa\b"],
        "weak": [r"statement of work", r"services"],
    },
    "sow": {
        "strong": [r"statement of work", r"\bsow\b"],
        "weak": [r"services described in", r"deliverables"],
    },
    "nda": {
        "strong": [r"non-disclosure agreement", r"\bnda\b", r"confidentiality agreement"],
        "weak": [r"confidential information", r"non-disclosure", r"receiving party", r"disclosing party"],
    },
    "vendor_agreement": {
        "strong": [r"vendor agreement", r"supply agreement", r"procurement agreement"],
        "weak": [r"supplier", r"purchase order", r"goods"],
    },
    "employment_agreement": {
        "strong": [r"employment agreement"],
        "weak": [r"employee", r"employer", r"salary", r"termination of employment"],
    },
    "lease": {
        "strong": [r"\blease agreement\b", r"\blease\b"],
        "weak": [r"lessor", r"lessee", r"rent", r"premises"],
    },
}


def classify_contract(text: str) -> dict:
    haystack = text.lower()
    title_region = haystack[:1200]
    first_lines = "\n".join(line.strip() for line in text.splitlines()[:5] if line.strip()).lower()

    title_overrides = [
        ("master services agreement", "msa"),
        ("statement of work", "sow"),
        ("non-disclosure agreement", "nda"),
        ("confidentiality agreement", "nda"),
        ("vendor agreement", "vendor_agreement"),
        ("employment agreement", "employment_agreement"),
        ("lease agreement", "lease"),
    ]
    for phrase, contract_type in title_overrides:
        if phrase in first_lines:
            return {"document_type": contract_type, "confidence": 0.97}

    scores = {}

    for contract_type, rules in CONTRACT_TYPES.items():
        score = 0

        for pattern in rules["strong"]:
            if re.search(pattern, first_lines):
                score += 8
                continue
            if re.search(pattern, title_region):
                score += 5
            elif re.search(pattern, haystack):
                score += 3

        for pattern in rules["weak"]:
            if re.search(pattern, haystack):
                score += 1

        scores[contract_type] = score

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score <= 0:
        return {"document_type": "unknown", "confidence": 0.3}

    confidence = 0.95 if best_score >= 5 else 0.8 if best_score >= 3 else 0.6
    return {"document_type": best_type, "confidence": confidence}
