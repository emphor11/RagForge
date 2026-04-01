import re


DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
)

GOVERNING_LAW_RE = re.compile(r"laws of ([A-Z][A-Za-z ]+)", re.IGNORECASE)
TERM_RE = re.compile(r"remain in force for ([^.]+)\.", re.IGNORECASE)
RENEWAL_RE = re.compile(r"(auto[- ]renew\w*|renew\w*[^.]{0,80})", re.IGNORECASE)
PAYMENT_RE = re.compile(r"(payment[^.]{0,120}|fees?[^.]{0,120}|pricing[^.]{0,120})", re.IGNORECASE)


def extract_parties(chunks) -> list[str]:
    seen = []
    for chunk in chunks[:3]:
        for party in chunk["metadata"].get("party_mentions", []):
            if party not in seen:
                seen.append(party)
    return seen[:6]


def extract_effective_date(text: str) -> str:
    match = DATE_RE.search(text)
    return match.group(0) if match else ""


def extract_governing_law(text: str) -> str:
    match = GOVERNING_LAW_RE.search(text)
    return match.group(1).strip() if match else ""


def extract_term_length(text: str) -> str:
    match = TERM_RE.search(text)
    return match.group(1).strip() if match else ""


def extract_renewal_mechanics(text: str) -> str:
    match = RENEWAL_RE.search(text)
    return match.group(1).strip() if match else ""


def extract_payment_structure(text: str) -> str:
    match = PAYMENT_RE.search(text)
    return match.group(1).strip() if match else ""
