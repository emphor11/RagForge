import re


DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
)

GOVERNING_LAW_RE = re.compile(r"laws of ([A-Z][A-Za-z ]+)", re.IGNORECASE)
TERM_RE = re.compile(
    r"(?:remain in force|remain in effect|remain valid)\s+for\s+(?:an?\s+initial\s+term\s+of\s+|a\s+period\s+of\s+)?([^.]+?)(?:\.|,|\s+from\b)",
    re.IGNORECASE,
)
RENEWAL_RE = re.compile(r"(auto[- ]renew\w*|renew\w*[^.]{0,80})", re.IGNORECASE)
PAYMENT_RE = re.compile(r"(payment[^.]{0,120}|fees?[^.]{0,120}|pricing[^.]{0,120})", re.IGNORECASE)
AUTO_RENEW_RE = re.compile(r"(automatically renew\w*[^.]{0,120}|auto[- ]renew\w*[^.]{0,120})", re.IGNORECASE)
PARTY_SPLIT_RE = re.compile(
    r"\bbetween\s+(?P<party1>.+?)\s+and\s+(?P<party2>.+?)(?:\.|,|\n|$)",
    re.IGNORECASE | re.DOTALL,
)
LABELED_PARTY_RE = re.compile(
    r"Party\s+(?:Disclosing|Receiving)\s+Information:\s*(?P<party>.+?)(?=(?:,\s+with\b|\s*\(|\n|$))",
    re.IGNORECASE,
)
SIGNATORY_PARTY_RE = re.compile(
    r"(?:(?:Disclosing|Receiving)\s+Party):\s*(?P<party>[A-Z][A-Za-z0-9&.,'() -]{1,100}?)(?=\n|Signature:|Name:|Designation:|$)",
    re.IGNORECASE,
)
BETWEEN_BLOCK_RE = re.compile(
    r"\bbetween\b\s*(?P<party1>.+?)\b(?:and)\b\s*(?P<party2>.+?)(?=\bwhereas\b|\bnow therefore\b|definitions|general terms|$)",
    re.IGNORECASE | re.DOTALL,
)
M_S_ENTITY_RE = re.compile(
    r"(?:M/s\.\s*)?(?P<party>[A-Z][A-Za-z0-9&.,'() -]{1,100}?(?:Pvt\. Ltd\.|Private Limited|Inc\.|LLC|Ltd\.|Limited|Corporation|Corp\.|LP|LLP|PLC))",
)
LEGAL_ENTITY_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,\- ]{1,100}\s(?:Inc\.|LLC|Ltd\.|Limited|Corporation|Corp\.|LP|LLP|PLC|Pvt\. Ltd\.|Private Limited|Services LLP))\b"
)
LEGAL_SUFFIX_RE = re.compile(r"(?:Inc\.|LLC|Ltd\.|Limited|Corporation|Corp\.|LP|LLP|PLC|Pvt\. Ltd\.|Private Limited|Services LLP)$")


def _clean_party_name(name: str) -> str:
    party = re.sub(r"\s+", " ", (name or "")).strip(" ,.;:-")
    party = re.sub(r"^(?:and|between)\s+", "", party, flags=re.IGNORECASE)
    party = re.sub(
        r"^(this\s+)?(?:mutual\s+)?(?:non-disclosure|master services|services|employment|vendor)\s+agreement\s+(?:is\s+)?(?:entered into|made)\s+(?:on\s+.+?\s+)?between\s+",
        "",
        party,
        flags=re.IGNORECASE,
    )
    party = re.sub(r"^(on\s+\d{1,2}\s+[A-Z][a-z]+\s+\d{4}\s+between\s+)", "", party, flags=re.IGNORECASE)
    party = re.sub(r"^(party\s+(?:disclosing|receiving)\s+information:\s*)", "", party, flags=re.IGNORECASE)
    party = re.sub(r"^(?:disclosing|receiving)\s+party:\s*", "", party, flags=re.IGNORECASE)
    party = re.sub(
        r",\s*(?:with\s+(?:a\s+)?mailing\s+address|having\s+(?:its\s+)?registered\s+office|a\s+company\s+incorporated|an?\s+individual\s+residing)\b.*$",
        "",
        party,
        flags=re.IGNORECASE,
    )
    party = re.sub(
        r",\s*a\s+company\b.*$",
        "",
        party,
        flags=re.IGNORECASE,
    )
    party = re.sub(
        r",\s*a\s+limited\s+liability\s+partnership\b.*$",
        "",
        party,
        flags=re.IGNORECASE,
    )
    party = re.sub(r"\((?:\"|')?(?:disclosing|receiving)\s+party(?:\"|')?\)", "", party, flags=re.IGNORECASE)
    party = re.sub(r"\b(hereinafter|together with|collectively)\b.*$", "", party, flags=re.IGNORECASE).strip(" ,.;:-")
    if party.lower() in {"the company", "the consultant", "company", "consultant", "vendor", "client", "disclosing party", "receiving party"}:
        return ""
    return party


def _looks_like_legal_entity(name: str) -> bool:
    return bool(LEGAL_SUFFIX_RE.search(name))


def _looks_like_person_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3}", name))


def _extract_parties_from_text(text: str) -> list[str]:
    parties = []

    between_match = BETWEEN_BLOCK_RE.search(text[:1200])
    if between_match:
        for raw_party in (between_match.group("party1"), between_match.group("party2")):
            entity_match = M_S_ENTITY_RE.search(raw_party)
            if entity_match:
                party = _clean_party_name(entity_match.group("party"))
                if party and party not in parties:
                    parties.append(party)

    for regex in (LABELED_PARTY_RE, SIGNATORY_PARTY_RE):
        for match in regex.finditer(text):
            party = _clean_party_name(match.group("party"))
            if party and party not in parties and len(party.split()) <= 12:
                parties.append(party)

    match = PARTY_SPLIT_RE.search(text)
    if match:
        for raw_party in (match.group("party1"), match.group("party2")):
            for entity_match in LEGAL_ENTITY_RE.finditer(raw_party):
                party = _clean_party_name(entity_match.group(1))
                if party and party not in parties:
                    parties.append(party)

            cleaned = _clean_party_name(raw_party)
            if cleaned and cleaned not in parties and len(cleaned.split()) <= 12:
                if _looks_like_legal_entity(cleaned):
                    parties.append(cleaned)

    for entity_match in LEGAL_ENTITY_RE.finditer(text):
        party = _clean_party_name(entity_match.group(1))
        if party and party not in parties:
            parties.append(party)

    for line in text.splitlines():
        cleaned = _clean_party_name(line)
        if cleaned and cleaned not in parties and 1 < len(cleaned.split()) <= 4:
            if re.search(r"\b(has|agreed|shall|means|includes|subject|render|provide)\b", cleaned, re.IGNORECASE):
                continue
            if _looks_like_person_name(cleaned):
                parties.append(cleaned)

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
            if party and party not in seen:
                seen.append(party)
    return seen[:6]


def extract_effective_date(text: str) -> str:
    match = DATE_RE.search(text)
    return match.group(0) if match else ""


def extract_governing_law(text: str) -> str:
    clause_match = re.search(
        r"governed by(?: and construed in accordance with)? the laws of ([A-Z][A-Za-z ]+?)(?:,|\.|\sand\b|\swith\b)",
        text,
        re.IGNORECASE,
    )
    if clause_match:
        return clause_match.group(1).strip()

    match = GOVERNING_LAW_RE.search(text)
    if not match:
        return ""
    return re.split(r"\s+(?:and|with)\b", match.group(1).strip(), maxsplit=1)[0].strip()


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

    heading_match = re.search(
        r"(?:^|\n)\s*\d+(?:\.\d+)*[\)\.]?\s+([A-Z][^\n]{0,80}(?:payment|fees?)[^\n]*)",
        text,
        re.IGNORECASE,
    )
    if heading_match:
        return heading_match.group(1).strip()

    for sentence in re.findall(r"[^.]{0,160}(?:invoice|pay(?:ment)?|fees?|compensation)[^.]{0,160}", text, re.IGNORECASE):
        candidate = sentence.strip()
        candidate_lower = candidate.lower()
        if "statement of work" in candidate_lower or "deliverables" in candidate_lower:
            continue
        return candidate

    match = PAYMENT_RE.search(text)
    if not match:
        return ""
    candidate = match.group(1).strip()
    if candidate.lower() == "payment terms":
        return ""
    if "statement of work" in candidate.lower():
        return ""
    return candidate
