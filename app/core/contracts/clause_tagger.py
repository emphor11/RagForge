import re


TITLE_PATTERNS = [
    r"non-disclosure agreement",
    r"mutual non-disclosure agreement",
    r"master services agreement",
    r"statement of work",
    r"vendor agreement",
    r"employment agreement",
    r"service agreement",
    r"\bnda\b",
    r"\bmsa\b",
    r"\bsow\b",
]
PARTIES_PATTERNS = [r"\bbetween\b", r"\bparty\b", r"\bparties\b"]
RECITALS_PATTERNS = [r"^whereas", r"business purpose", r"now,\s*therefore"]

HEADING_TYPE_PATTERNS = [
    ("parties", [r"^between$", r"^parties$", r"^party details?$"]),
    ("definitions", [r"^definitions?$", r"defined terms"]),
    ("services_scope", [r"^services\.?$", r"scope of services", r"scope of work", r"services and deliverables", r"statement of work"]),
    ("general_terms", [r"^general terms$", r"general conditions", r"general obligations"]),
    ("confidentiality_definition", [r"definition of confidential information"]),
    ("permitted_use_and_non_disclosure", [r"permitted use", r"non-disclosure", r"obligations of receiving party", r"obligations of recipient", r"receiving party"]),
    ("return_or_destruction", [r"return or destruction"]),
    ("exclusions", [r"\bexclusions?\b", r"\bexceptions?\b"]),
    ("confidentiality", [r"^confidentiality\.?$", r"confidential information", r"non-disclosure obligations"]),
    ("ip_rights", [r"no license", r"license or transfer of rights", r"intellectual property"]),
    ("remedies", [r"\bremedies?\b"]),
    ("term_and_survival", [r"term and survival", r"\bsurvival\b", r"time periods", r"confidentiality period", r"\bterm\b", r"\bduration\b"]),
    ("governing_law", [r"governing law", r"applicable law"]),
    ("dispute_resolution", [r"dispute resolution", r"arbitration", r"dispute[s]?"]),
    ("entire_agreement", [r"entire agreement", r"whole agreement"]),
    ("severability", [r"severability"]),
    ("subcontracting", [r"sub-?contracting", r"subcontracting"]),
    ("modifications", [r"modifications?", r"amendments?"]),
    ("assignment", [r"assignment"]),
    ("non_solicitation", [r"non-?solicitation"]),
    ("payment", [r"payment terms", r"fees", r"pricing", r"invoices?", r"compensation"]),
    ("termination", [r"termination", r"term and termination"]),
    ("liability_cap", [r"limitation of liability", r"liability cap", r"limits? of liability"]),
    ("indemnity", [r"\bindemn", r"hold harmless"]),
    ("signatures", [r"signatures?", r"in witness whereof", r"signed by"]),
]


def normalize_heading(heading: str) -> str:
    heading = (heading or "").strip()
    if not heading:
        return ""

    # Collapse excessive whitespace and preserve the legal heading text.
    return re.sub(r"\s+", " ", heading)


def infer_clause_type(heading: str, text: str = "") -> str:
    heading_lower = heading.lower().strip()
    heading_core = re.sub(r"^\d+(?:\.\d+)*[\)\.]?\s*", "", heading_lower).strip()
    text_lower = text.lower()

    if not heading_lower:
        if any(re.search(pattern, text_lower) for pattern in RECITALS_PATTERNS):
            return "recitals"
        if "this agreement is made and entered into" in text_lower or any(
            re.search(pattern, text_lower) for pattern in PARTIES_PATTERNS
        ):
            return "parties"
        return ""

    if any(re.search(pattern, heading_lower) for pattern in TITLE_PATTERNS):
        return "title"

    for clause_type, patterns in HEADING_TYPE_PATTERNS:
        if any(re.search(pattern, heading_lower) or re.search(pattern, heading_core) for pattern in patterns):
            return clause_type

    # Body fallback is intentionally narrow so headings remain the dominant signal.
    if "this agreement is made" in text_lower[:250]:
        return "title"
    if "hereinafter called" in text_lower[:250] or text_lower.startswith("m/s."):
        return "parties"
    if any(re.search(pattern, text_lower[:250]) for pattern in RECITALS_PATTERNS):
        return "recitals"

    return ""
