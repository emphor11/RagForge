import re


CONTRACT_TYPES = [
    ("nda", [r"non-disclosure agreement", r"\bnda\b", r"confidential information"]),
    ("msa", [r"master services agreement", r"\bmsa\b"]),
    ("sow", [r"statement of work", r"\bsow\b"]),
    ("vendor_agreement", [r"vendor agreement", r"supply agreement", r"procurement"]),
    ("employment_agreement", [r"employment agreement", r"employee", r"employer"]),
    ("lease", [r"\blease\b", r"lessor", r"lessee", r"rent"]),
]


def classify_contract(text: str) -> dict:
    haystack = text.lower()
    for contract_type, patterns in CONTRACT_TYPES:
        for pattern in patterns:
            if re.search(pattern, haystack):
                return {"document_type": contract_type, "confidence": 0.9}

    return {"document_type": "unknown", "confidence": 0.3}
