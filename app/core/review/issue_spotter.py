import re


HIGH_VALUE_CLAUSE_TYPES = {
    "termination",
    "liability_cap",
    "indemnity",
    "payment",
    "governing_law",
}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
COMMERCIAL_DOC_TYPES = {"msa", "sow", "vendor_agreement", "employment_agreement", "lease"}


def build_clause_lookup(clauses: list[dict]) -> dict[str, dict]:
    lookup = {}
    for clause in clauses:
        clause_type = clause.get("type", "")
        if clause_type and clause_type not in lookup:
            lookup[clause_type] = clause
    return lookup


def find_clause_by_heading(clauses: list[dict], pattern: str) -> dict | None:
    for clause in clauses:
        title = clause.get("title", "")
        if title and re.search(pattern, title, re.IGNORECASE):
            return clause
    return None


def quote_preview(text: str, limit: int = 180) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    return clean[:limit]


def has_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def extract_notice_days(text: str) -> int | None:
    match = re.search(r"(\d{1,3})\s*(calendar\s+)?days?", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def deduplicate_findings(findings: list[dict]) -> list[dict]:
    deduped = []
    seen_exact = set()

    for finding in findings:
        key = (
            finding.get("finding_type"),
            finding.get("clause_type"),
            finding.get("title"),
        )
        if key in seen_exact:
            continue
        seen_exact.add(key)
        deduped.append(finding)

    grouped = {}
    for finding in deduped:
        clause_type = finding.get("clause_type", "")
        grouped.setdefault(clause_type, []).append(finding)

    result = []
    for clause_type, clause_findings in grouped.items():
        hard_findings = [
            finding for finding in clause_findings
            if finding.get("finding_type") in {"risk", "missing_protection"}
        ]
        negotiation_points = [
            finding for finding in clause_findings
            if finding.get("finding_type") == "negotiation_point"
        ]

        result.extend(hard_findings)

        if negotiation_points:
            negotiation_points.sort(
                key=lambda finding: (
                    SEVERITY_RANK.get(finding.get("severity", "low"), 0),
                    finding.get("confidence", 0),
                ),
                reverse=True,
            )
            result.extend(negotiation_points[:2])

    return sorted(
        result,
        key=lambda finding: (
            SEVERITY_RANK.get(finding.get("severity", "low"), 0),
            finding.get("confidence", 0),
        ),
        reverse=True,
    )


def compute_confidence(
    contract_profile: dict,
    finding_type: str,
    severity: str,
    source_clause: dict | None = None,
) -> float:
    doc_conf = float(contract_profile.get("classification_confidence") or 0.75)
    severity_bonus = {"high": 0.08, "medium": 0.05, "low": 0.02}.get(severity, 0.0)
    source_bonus = 0.0

    if source_clause:
        clause_text = source_clause.get("clause_text", "")
        title = (source_clause.get("title") or "").strip()
        source_bonus += 0.12
        if len(clause_text.split()) >= 12:
            source_bonus += 0.05
        if title:
            source_bonus += 0.03
    elif finding_type == "missing_protection":
        source_bonus -= 0.03

    type_base = {
        "missing_protection": 0.56,
        "risk": 0.6,
        "negotiation_point": 0.58,
    }.get(finding_type, 0.55)

    confidence = type_base + (doc_conf * 0.18) + severity_bonus + source_bonus
    return round(max(0.55, min(confidence, 0.93)), 2)


def spot_clause_issues(contract_profile: dict, clauses: list[dict]) -> list[dict]:
    document_type = contract_profile.get("document_type", "")
    clause_lookup = build_clause_lookup(clauses)
    termination_candidate = clause_lookup.get("termination") or find_clause_by_heading(clauses, r"\btermination\b")
    findings = []

    def add_finding(
        finding_type: str,
        clause_type: str,
        severity: str,
        title: str,
        explanation: str,
        source_clause: dict | None = None,
        confidence: float | None = None,
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
            "confidence": confidence if confidence is not None else compute_confidence(
                contract_profile=contract_profile,
                finding_type=finding_type,
                severity=severity,
                source_clause=source_clause,
            ),
            "status": "open",
            "reviewer_note": "",
        })

    if document_type != "nda" and "payment" not in clause_lookup:
        add_finding(
            "missing_protection",
            "payment",
            "high",
            "Payment terms are not clearly identified",
            "The contract profile did not detect a payment clause. Commercial agreements should define fees, timing, and payment mechanics.",
        )

    if not termination_candidate and document_type in COMMERCIAL_DOC_TYPES:
        add_finding(
            "missing_protection",
            "termination",
            "high",
            "Termination rights are not clearly identified",
            "The clause inventory did not detect a termination clause. This can leave exit mechanics and notice requirements undefined.",
        )

    if "liability_cap" not in clause_lookup and document_type in {"msa", "sow", "vendor_agreement"}:
        add_finding(
            "missing_protection",
            "liability_cap",
            "high",
            "No limitation of liability clause detected",
            "The agreement does not appear to include a liability cap. That can leave exposure uncapped for commercial claims.",
        )

    if "indemnity" not in clause_lookup and document_type in {"msa", "sow", "vendor_agreement"}:
        add_finding(
            "missing_protection",
            "indemnity",
            "medium",
            "No indemnity clause detected",
            "The clause inventory did not detect an indemnity provision. Review whether third-party risk allocation is intentionally omitted.",
        )

    termination_clause = termination_candidate
    if termination_clause:
        text = termination_clause.get("clause_text", "").lower()
        notice_days = extract_notice_days(text)
        has_convenience_style_exit = (
            "for convenience" in text
            or "either party may terminate" in text
            or "may terminate this agreement" in text
        )
        if not has_convenience_style_exit:
            add_finding(
                "risk",
                "termination",
                "medium",
                "No express termination-for-convenience language detected",
                "The termination clause does not appear to provide an explicit termination-for-convenience right. Review whether the parties intended a discretionary exit right.",
                source_clause=termination_clause,
            )
        if "notice" not in text:
            add_finding(
                "negotiation_point",
                "termination",
                "medium",
                "Termination notice mechanics should be reviewed",
                "The termination clause does not clearly reference notice timing. Add notice periods if the contract should support orderly exit.",
                source_clause=termination_clause,
            )
        elif notice_days is not None and notice_days < 30:
            add_finding(
                "negotiation_point",
                "termination",
                "medium",
                "Termination notice period may be short",
                f"The termination clause appears to use a {notice_days}-day notice period. Confirm whether that is long enough for transition and wind-down obligations.",
                source_clause=termination_clause,
            )
        if "cause" not in text and "breach" not in text:
            add_finding(
                "risk",
                "termination",
                "medium",
                "Termination-for-cause trigger is not obvious",
                "The termination clause does not clearly mention breach or cause-based exit language. Review whether default scenarios are adequately addressed.",
                source_clause=termination_clause,
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
            )
        elif "fees paid" not in text and "amounts paid" not in text and "twelve months" not in text:
            add_finding(
                "negotiation_point",
                "liability_cap",
                "medium",
                "Liability cap formula is not obvious",
                "The liability clause does not clearly tie the cap to fees paid, contract value, or a stated monetary ceiling. Review whether the cap formula is sufficiently explicit.",
                source_clause=liability_clause,
            )
        if "consequential" not in text and "indirect" not in text:
            add_finding(
                "negotiation_point",
                "liability_cap",
                "low",
                "Excluded damages language may be missing",
                "The liability clause does not clearly reference consequential or indirect damages. Confirm whether damages exclusions should be stated separately.",
                source_clause=liability_clause,
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
            )
        if "third party" not in text:
            add_finding(
                "negotiation_point",
                "indemnity",
                "medium",
                "Indemnity trigger scope is not clearly limited to third-party claims",
                "The indemnity clause does not clearly refer to third-party claims. Review whether the indemnity could be read more broadly than intended.",
                source_clause=indemnity_clause,
            )
        if "defend" not in text and "control of defense" not in text:
            add_finding(
                "negotiation_point",
                "indemnity",
                "low",
                "Defense control mechanics are not obvious",
                "The indemnity clause does not clearly address who controls the defense of claims. Consider whether defense mechanics should be spelled out.",
                source_clause=indemnity_clause,
            )

    payment_clause = clause_lookup.get("payment")
    if payment_clause:
        text = payment_clause.get("clause_text", "").lower()
        has_payment_window = has_any_pattern(
            text,
            [r"upon receipt", r"net\s*\d+", r"\d{1,3}\s*days?", r"within\s+\d{1,3}\s*days?"],
        )
        if "upon receipt" in text:
            add_finding(
                "negotiation_point",
                "payment",
                "medium",
                "Payment timing may be aggressive",
                "The payment clause appears to require payment upon receipt. Consider whether the review standard expects a longer payment window.",
                source_clause=payment_clause,
            )
        if not has_payment_window:
            add_finding(
                "risk",
                "payment",
                "medium",
                "Payment timing is not clearly defined",
                "The payment clause does not clearly state a due date or payment window. Review whether invoice timing and payment deadlines are explicit enough.",
                source_clause=payment_clause,
            )
        if "late fee" not in text and "interest" not in text:
            add_finding(
                "negotiation_point",
                "payment",
                "low",
                "Late payment remedy is not obvious",
                "The payment clause does not clearly reference late-payment interest or similar remedies. Consider whether overdue payment protection is needed.",
                source_clause=payment_clause,
            )

    governing_law_clause = clause_lookup.get("governing_law")
    if governing_law_clause:
        text = governing_law_clause.get("clause_text", "").lower()
        needs_forum_specificity = (
            "exclusive jurisdiction" not in text
            and "courts of" not in text
            and "courts in" not in text
            and "jurisdiction in" not in text
            and "jurisdiction of courts in" not in text
            and "seat" not in text
            and "venue" not in text
        )
        if "arbitration" in text and needs_forum_specificity:
            add_finding(
                "negotiation_point",
                "governing_law",
                "low",
                "Dispute resolution forum mechanics could be more specific",
                "The clause references arbitration but does not clearly identify seat, venue, or other forum-selection language. Confirm whether dispute mechanics are sufficiently defined.",
                source_clause=governing_law_clause,
            )
        elif needs_forum_specificity:
            add_finding(
                "negotiation_point",
                "governing_law",
                "low",
                "Forum selection language is not obvious",
                "The dispute clause does not clearly specify exclusive jurisdiction, court forum, or arbitral seat language. Review whether forum selection should be clearer.",
                source_clause=governing_law_clause,
            )

    if document_type == "nda":
        remedies_clause = clause_lookup.get("remedies")
        if not remedies_clause:
            add_finding(
                "missing_protection",
                "remedies",
                "low",
                "No express injunctive-relief or remedies clause detected",
                "The NDA does not appear to include a dedicated remedies clause. Review whether the disclosing party reserves injunctive relief or other express remedies for unauthorized disclosure.",
            )

        obligations_clause = clause_lookup.get("permitted_use_and_non_disclosure")
        return_clause = clause_lookup.get("return_or_destruction")
        if obligations_clause and not return_clause:
            text = obligations_clause.get("clause_text", "").lower()
            if "return or destroy" not in text and "return" not in text and "destroy" not in text:
                add_finding(
                    "negotiation_point",
                    "return_or_destruction",
                    "low",
                    "Return or destruction mechanics are not obvious",
                    "The NDA does not clearly state whether confidential materials must be returned or destroyed on request or at the end of the relationship. Consider whether explicit disposition mechanics are needed.",
                    source_clause=obligations_clause,
                )

    return deduplicate_findings(findings)
