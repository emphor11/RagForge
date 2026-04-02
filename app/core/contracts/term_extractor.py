import re


DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
)

GOVERNING_LAW_RE = re.compile(r"laws of ([A-Z][A-Za-z ]+)", re.IGNORECASE)
TERM_RE = re.compile(r"remain in force for ([^.]+)\.", re.IGNORECASE)
RENEWAL_RE = re.compile(r"(auto[- ]renew\w*|renew\w*[^.]{0,80})", re.IGNORECASE)
PAYMENT_RE = re.compile(r"(payment[^.]{0,120}|fees?[^.]{0,120}|pricing[^.]{0,120})", re.IGNORECASE)
AUTO_RENEW_RE = re.compile(r"(automatically renew\w*[^.]{0,120}|auto[- ]renew\w*[^.]{0,120})", re.IGNORECASE)
PARTY_SPLIT_RE = re.compile(
    r"\bbetween\s+(?P<party1>.+?)\s+and\s+(?P<party2>.+?)(?:\.|,|\n|$)",
    re.IGNORECASE | re.DOTALL,
)
LEGAL_ENTITY_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,\- ]{1,100}\s(?:Inc\.|LLC|Ltd\.|Limited|Corporation|Corp\.|Company|Co\.|LP|LLP|PLC|Private Limited|Services LLP))\b"
)


def _clean_party_name(name: str) -> str:
    party = re.sub(r"\s+", " ", (name or "")).strip(" ,.;:-")
    party = re.sub(
        r"^(this\s+)?(?:mutual\s+)?(?:non-disclosure|master services|services|employment|vendor)\s+agreement\s+(?:is\s+)?(?:entered into|made)\s+(?:on\s+.+?\s+)?between\s+",
        "",
        party,
        flags=re.IGNORECASE,
    )
    party = re.sub(r"^(on\s+\d{1,2}\s+[A-Z][a-z]+\s+\d{4}\s+between\s+)", "", party, flags=re.IGNORECASE)
    party = re.sub(r"\b(hereinafter|together with|collectively)\b.*$", "", party, flags=re.IGNORECASE).strip(" ,.;:-")
    return party


def _extract_parties_from_text(text: str) -> list[str]:
    parties = []

    match = PARTY_SPLIT_RE.search(text)
    if match:
        for raw_party in (match.group("party1"), match.group("party2")):
            for entity_match in LEGAL_ENTITY_RE.finditer(raw_party):
                party = _clean_party_name(entity_match.group(1))
                if party and party not in parties:
                    parties.append(party)

            cleaned = _clean_party_name(raw_party)
            if cleaned and cleaned not in parties and len(cleaned.split()) <= 12:
                if any(token in cleaned for token in ["LLP", "LLC", "Ltd", "Limited", "Corp", "Company", "PLC"]):
                    parties.append(cleaned)

    for entity_match in LEGAL_ENTITY_RE.finditer(text):
        party = _clean_party_name(entity_match.group(1))
        if party and party not in parties:
            parties.append(party)

    return parties[:6]


def extract_parties(chunks) -> list[str]:
    seen = []
    preamble_text = "\n".join(chunk["content"] for chunk in chunks[:3])

    for party in _extract_parties_from_text(preamble_text):
        if party not in seen:
            seen.append(party)

    for chunk in chunks[:3]:
        for party in chunk["metadata"].get("party_mentions", []):
            party = _clean_party_name(party)
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
    match = AUTO_RENEW_RE.search(text) or RENEWAL_RE.search(text)
    return match.group(1).strip() if match else ""


def extract_payment_structure(text: str, document_type: str = "") -> str:
    # NDAs often mention "pricing" in the definition of confidential information,
    # which should not be mistaken for a payment term.
    if document_type == "nda":
        return ""

    match = PAYMENT_RE.search(text)
    return match.group(1).strip() if match else ""
