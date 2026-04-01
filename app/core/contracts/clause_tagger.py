import re


CLAUSE_PATTERNS = [
    ("confidentiality", [r"confidential", r"non-disclosure", r"permitted use"]),
    ("return_or_destruction", [r"return or destruction", r"return", r"destroy"]),
    ("exclusions", [r"exclusions", r"exceptions"]),
    ("term", [r"term and survival", r"\bterm\b", r"survival"]),
    ("governing_law", [r"governing law", r"laws of"]),
    ("dispute_resolution", [r"arbitration", r"dispute resolution"]),
    ("assignment", [r"assignment", r"assign"]),
    ("entire_agreement", [r"entire agreement", r"supersedes"]),
    ("payment", [r"payment", r"fees", r"invoice", r"pricing"]),
    ("termination", [r"termination", r"terminate"]),
    ("liability_cap", [r"limitation of liability", r"liability cap"]),
    ("indemnity", [r"indemn", r"indemnity"]),
    ("ip_rights", [r"intellectual property", r"license", r"rights"]),
    ("parties", [r"between", r"party", r"parties"]),
]


def normalize_heading(heading: str) -> str:
    heading = (heading or "").strip()
    if not heading:
        return ""

    # Collapse excessive whitespace and preserve the legal heading text.
    return re.sub(r"\s+", " ", heading)


def infer_clause_type(heading: str, text: str = "") -> str:
    haystack = f"{heading} {text}".lower()
    for clause_type, patterns in CLAUSE_PATTERNS:
        if any(re.search(pattern, haystack) for pattern in patterns):
            return clause_type
    return ""
