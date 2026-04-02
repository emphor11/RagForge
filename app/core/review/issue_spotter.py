import re


HIGH_VALUE_CLAUSE_TYPES = {
    "termination",
    "liability_cap",
    "indemnity",
    "payment",
    "governing_law",
}


def build_clause_lookup(clauses: list[dict]) -> dict[str, dict]:
    lookup = {}
    for clause in clauses:
        clause_type = clause.get("type", "")
        if clause_type and clause_type not in lookup:
            lookup[clause_type] = clause
    return lookup


def quote_preview(text: str, limit: int = 180) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    return clean[:limit]


def spot_clause_issues(contract_profile: dict, clauses: list[dict]) -> list[dict]:
    document_type = contract_profile.get("document_type", "")
    clause_lookup = build_clause_lookup(clauses)
    findings = []

    def add_finding(
        finding_type: str,
        clause_type: str,
        severity: str,
        title: str,
        explanation: str,
        source_clause: dict | None = None,
        confidence: float = 0.8,
    ):
        source_quotes = []
        clause_refs = []
        if source_clause:
            source_quotes.append(quote_preview(source_clause.get("clause_text", "")))
            clause_refs.append(source_clause.get("title", clause_type))

        findings.append({
            "finding_type": finding_type,
            "clause_type": clause_type,
            "severity": severity,
            "title": title,
            "explanation": explanation,
            "clause_refs": clause_refs,
            "source_quotes": source_quotes,
            "confidence": confidence,
            "status": "open",
        })

    if document_type != "nda" and "payment" not in clause_lookup:
        add_finding(
            "missing_protection",
            "payment",
            "high",
            "Payment terms are not clearly identified",
            "The contract profile did not detect a payment clause. Commercial agreements should define fees, timing, and payment mechanics.",
            confidence=0.78,
        )

    if "termination" not in clause_lookup and document_type in {"msa", "sow", "vendor_agreement", "employment_agreement", "lease"}:
        add_finding(
            "missing_protection",
            "termination",
            "high",
            "Termination rights are not clearly identified",
            "The clause inventory did not detect a termination clause. This can leave exit mechanics and notice requirements undefined.",
            confidence=0.84,
        )

    if "liability_cap" not in clause_lookup and document_type in {"msa", "sow", "vendor_agreement"}:
        add_finding(
            "missing_protection",
            "liability_cap",
            "high",
            "No limitation of liability clause detected",
            "The agreement does not appear to include a liability cap. That can leave exposure uncapped for commercial claims.",
            confidence=0.9,
        )

    if "indemnity" not in clause_lookup and document_type in {"msa", "sow", "vendor_agreement"}:
        add_finding(
            "missing_protection",
            "indemnity",
            "medium",
            "No indemnity clause detected",
            "The clause inventory did not detect an indemnity provision. Review whether third-party risk allocation is intentionally omitted.",
            confidence=0.82,
        )

    termination_clause = clause_lookup.get("termination")
    if termination_clause:
        text = termination_clause.get("clause_text", "").lower()
        if "for convenience" not in text:
            add_finding(
                "risk",
                "termination",
                "medium",
                "No express termination-for-convenience language detected",
                "The termination clause does not appear to provide an explicit termination-for-convenience right. Review whether the parties intended a discretionary exit right.",
                source_clause=termination_clause,
                confidence=0.76,
            )
        if "notice" not in text:
            add_finding(
                "negotiation_point",
                "termination",
                "medium",
                "Termination notice mechanics should be reviewed",
                "The termination clause does not clearly reference notice timing. Add notice periods if the contract should support orderly exit.",
                source_clause=termination_clause,
                confidence=0.74,
            )

    liability_clause = clause_lookup.get("liability_cap")
    if liability_clause:
        text = liability_clause.get("clause_text", "").lower()
        if "unlimited" in text or "no limit" in text:
            add_finding(
                "risk",
                "liability_cap",
                "high",
                "Liability appears uncapped",
                "The liability clause uses language suggesting uncapped exposure. Confirm whether this was intentional and commercially acceptable.",
                source_clause=liability_clause,
                confidence=0.91,
            )

    indemnity_clause = clause_lookup.get("indemnity")
    if indemnity_clause:
        text = indemnity_clause.get("clause_text", "").lower()
        if "all claims" in text and "limit" not in text and "cap" not in text:
            add_finding(
                "risk",
                "indemnity",
                "high",
                "Indemnity appears broad without an express limit",
                "The indemnity clause appears broad and does not obviously include a cap or narrowing qualifier. Review the risk allocation carefully.",
                source_clause=indemnity_clause,
                confidence=0.88,
            )

    payment_clause = clause_lookup.get("payment")
    if payment_clause:
        text = payment_clause.get("clause_text", "").lower()
        if "upon receipt" in text:
            add_finding(
                "negotiation_point",
                "payment",
                "medium",
                "Payment timing may be aggressive",
                "The payment clause appears to require payment upon receipt. Consider whether the review standard expects a longer payment window.",
                source_clause=payment_clause,
                confidence=0.77,
            )

    governing_law_clause = clause_lookup.get("governing_law")
    if governing_law_clause:
        text = governing_law_clause.get("clause_text", "").lower()
        if "arbitration" in text and "seat" not in text and "venue" not in text:
            add_finding(
                "negotiation_point",
                "governing_law",
                "low",
                "Dispute resolution mechanics could be more specific",
                "The clause references arbitration but does not clearly identify seat or venue language. Confirm whether dispute mechanics are sufficiently defined.",
                source_clause=governing_law_clause,
                confidence=0.7,
            )

    return findings
