from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer, util
from thefuzz import fuzz
import re

class InsightEvaluator:
    def __init__(self):
        self.embedder = None
        self.embedder_model_name = "all-MiniLM-L6-v2"

        self.generic_phrases = [
            "the document discusses", "review the pdf", "for more information",
            "as mentioned in the text", "the document provides",
            "there is no mention of", "is discussed in the section",
            "the text explains", "according to the document"
        ]

        # Specificity signals — a good insight should contain at least one of these
        self.specificity_patterns = [
            r'\d+',                    # any number
            r'\b[A-Z][a-z]+[A-Z]\w*', # camelCase or proper technical terms
            r'section \d',             # section reference
            r'chapter \d',             # chapter reference
            r'equation|formula|theorem|lemma|proof',
            r'%|ratio|rate|score|accuracy|loss',
            r'\$|revenue|cost|margin|profit',
        ]
        self.legal_advice_patterns = [
            r"\byou should\b",
            r"\bmust\b",
            r"\bguarantees?\b",
            r"\bwill definitely\b",
        ]
        self.high_value_legal_clauses = {
            "termination",
            "liability_cap",
            "indemnity",
            "payment",
            "governing_law",
        }

    # -------------------------------------------------------------------------
    # 1. STRUCTURE CHECK — are all required fields present and well-formed?
    # -------------------------------------------------------------------------
    def evaluate_structure(self, insights: Dict[str, Any]) -> tuple:
        required_fields = ["summary", "key_insights", "risks",
                           "recommended_actions", "reasoning"]
        issues = []
        score = 100

        for field in required_fields:
            val = insights.get(field)
            if not val:
                issues.append(f"Missing or empty field: '{field}'")
                score -= 20
                continue
            if isinstance(val, list) and len(val) == 0:
                issues.append(f"Field '{field}' is an empty list")
                score -= 15
                continue

            # Validate sub-fields inside list items
            if field == "key_insights":
                for i, item in enumerate(val):
                    if not isinstance(item, dict):
                        issues.append(f"key_insights[{i}] is not a dict")
                        score -= 5
                        continue
                    for sub in ["insight", "source", "confidence"]:
                        if sub not in item:
                            issues.append(f"key_insights[{i}] missing '{sub}'")
                            score -= 5

            if field == "risks":
                for i, item in enumerate(val):
                    if not isinstance(item, dict):
                        continue
                    for sub in ["finding", "severity", "reason", "source", "confidence"]:
                        if sub not in item:
                            issues.append(f"risks[{i}] missing '{sub}'")
                            score -= 4
                    if item.get("severity") not in ("high", "medium", "low"):
                        issues.append(f"risks[{i}] has invalid severity: {item.get('severity')}")
                        score -= 3

        return max(0, score), issues

    # -------------------------------------------------------------------------
    # 2. GROUNDING CHECK — does each source quote actually support its claim?
    #    Uses normalized quote matching + local context windows + batched semantics
    # -------------------------------------------------------------------------
    def evaluate_grounding(self, insights: Dict[str, Any], context: str) -> tuple:
        issues = []
        total_weight = 0.0
        passed_weight = 0.0
        context_lower = context.lower()
        normalized_context = self._normalize_text(context)

        sections = {
            "key_insights": "insight",
            "risks": "finding",
            "recommended_actions": "action"
        }

        claims_to_check = []   # (field, claim_kind, claim_text, source_text, severity_weight)
        for field, label in sections.items():
            for item in insights.get(field, []):
                if not isinstance(item, dict):
                    continue
                source = item.get("source", "").strip()
                primary_claim = item.get(label, "").strip()

                claim_parts = [(label, primary_claim)]
                if field == "risks":
                    claim_parts.append(("reason", item.get("reason", "").strip()))
                elif field == "recommended_actions":
                    claim_parts.append(("rationale", item.get("rationale", "").strip()))

                if not source:
                    preview = primary_claim or item.get("reason", "") or item.get("rationale", "")
                    issues.append(f"No source quote for {field}: '{preview[:40]}...'")
                    total_weight += 1.0
                    continue

                for claim_kind, claim_text in claim_parts:
                    if not claim_text:
                        continue
                    weight = 1.0 if claim_kind in ("insight", "finding", "action") else 0.6
                    claims_to_check.append((field, claim_kind, claim_text, source, weight))
                    total_weight += weight

        if not claims_to_check:
            return 0, ["No grounded claims found — all sources missing"]

        semantic_pairs = []
        semantic_meta = []

        for field, claim_kind, claim, source, weight in claims_to_check:
            quote_check = self._find_source_window(source, context, context_lower, normalized_context)
            if not quote_check["found"]:
                issues.append(
                    f"Hallucination risk in {field}: source not found in context "
                    f"(fuzzy={quote_check['fuzzy']}): '{source[:60]}...'"
                )
                continue

            semantic_pairs.extend([claim, quote_check["window"]])
            semantic_meta.append((field, claim_kind, claim, weight))

        if semantic_pairs:
            embeddings = self._get_embedder().encode(semantic_pairs, convert_to_tensor=True)
            for idx, (field, claim_kind, claim, weight) in enumerate(semantic_meta):
                claim_embedding = embeddings[idx * 2]
                window_embedding = embeddings[idx * 2 + 1]
                sim = float(util.cos_sim(claim_embedding, window_embedding))

                threshold = 0.52 if claim_kind in ("insight", "finding", "action") else 0.48
                if sim < threshold:
                    issues.append(
                        f"Low semantic alignment in {field}.{claim_kind} (sim={sim:.2f}): "
                        f"source doesn't support claim — '{claim[:50]}...'"
                    )
                else:
                    passed_weight += weight

        score = (passed_weight / total_weight * 100) if total_weight > 0 else 0
        return round(score), issues

    def _get_embedder(self):
        if self.embedder is None:
            self.embedder = SentenceTransformer(self.embedder_model_name, local_files_only=True)
        return self.embedder

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    def _find_source_window(self, source: str, context: str, context_lower: str, normalized_context: str) -> Dict[str, Any]:
        source_lower = source.lower().strip()
        normalized_source = self._normalize_text(source)
        fuzzy_score = fuzz.partial_ratio(source_lower, context_lower)

        # Prefer direct substring matching first.
        direct_index = context_lower.find(source_lower)
        if direct_index != -1:
            return {
                "found": True,
                "fuzzy": 100,
                "window": self._extract_window(context, direct_index, len(source))
            }

        # Then try normalized matching to tolerate whitespace/newline differences.
        normalized_index = normalized_context.find(normalized_source)
        if normalized_index != -1:
            return {
                "found": True,
                "fuzzy": 100,
                "window": normalized_source
            }

        # Finally fall back to fuzzy matching for slightly imperfect quotes.
        min_fuzzy = 88 if len(normalized_source) < 80 else 82
        if fuzzy_score >= min_fuzzy:
            return {
                "found": True,
                "fuzzy": fuzzy_score,
                "window": source
            }

        return {
            "found": False,
            "fuzzy": fuzzy_score,
            "window": ""
        }

    def _extract_window(self, context: str, start: int, source_len: int, radius: int = 220) -> str:
        left = max(0, start - radius)
        right = min(len(context), start + source_len + radius)
        return context[left:right]

    # -------------------------------------------------------------------------
    # 3. QUALITY CHECK — are insights specific, non-obvious, and deep?
    # -------------------------------------------------------------------------
    def evaluate_quality(self, insights: Dict[str, Any]) -> tuple:
        issues = []
        score = 100

        # Check reasoning depth
        reasoning = insights.get("reasoning", "")
        reasoning_words = len(reasoning.split())
        if reasoning_words < 40:
            issues.append(f"Reasoning too shallow ({reasoning_words} words — need 40+)")
            score -= 20
        elif reasoning_words < 80:
            issues.append(f"Reasoning could be deeper ({reasoning_words} words)")
            score -= 10

        # Check summary depth
        summary = insights.get("summary", "")
        if len(summary.split()) < 25:
            issues.append(f"Summary too short ({len(summary.split())} words — need 25+)")
            score -= 15

        # Check for generic phrases in summary + reasoning
        combined = (summary + " " + reasoning).lower()
        for phrase in self.generic_phrases:
            if phrase in combined:
                issues.append(f"Generic phrasing detected: '{phrase}'")
                score -= 8

        # Check specificity of each insight
        for i, item in enumerate(insights.get("key_insights", [])):
            if not isinstance(item, dict):
                continue
            insight_text = item.get("insight", "")
            is_specific = any(
                re.search(p, insight_text, re.IGNORECASE)
                for p in self.specificity_patterns
            )
            if not is_specific:
                issues.append(
                    f"key_insights[{i}] appears generic — no numbers, "
                    f"section refs, or specific terms detected: '{insight_text[:60]}...'"
                )
                score -= 12

        # Check confidence score calibration — high confidence on weak items?
        for field in ["key_insights", "risks", "recommended_actions"]:
            for i, item in enumerate(insights.get(field, [])):
                if not isinstance(item, dict):
                    continue
                conf = item.get("confidence", None)
                if conf is None:
                    continue
                if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                    issues.append(f"{field}[{i}] has invalid confidence value: {conf}")
                    score -= 5

        return max(0, score), issues

    # -------------------------------------------------------------------------
    # 4. CONTEXT COVERAGE CHECK — does the model admit when context is thin?
    # -------------------------------------------------------------------------
    def evaluate_coverage(self, insights: Dict[str, Any]) -> tuple:
        issues = []
        score = 100

        cq = insights.get("context_quality")
        if cq not in ("full", "partial", "insufficient"):
            issues.append("Missing or invalid 'context_quality' field")
            score -= 20

        if cq in ("partial", "insufficient"):
            gap = insights.get("context_gap", "")
            if not gap or len(gap.strip()) < 10:
                issues.append(
                    "context_quality is partial/insufficient but 'context_gap' "
                    "is missing or too vague — model should explain what's missing"
                )
                score -= 15

        overall_conf = insights.get("overall_confidence")
        if overall_conf is None:
            issues.append("Missing 'overall_confidence' field")
            score -= 10
        elif not (0.0 <= float(overall_conf) <= 1.0):
            issues.append(f"Invalid overall_confidence value: {overall_conf}")
            score -= 10

        return max(0, score), issues

    # -------------------------------------------------------------------------
    # MAIN RUN — weighted composite score with full report
    # -------------------------------------------------------------------------
    def run(self, insights: Dict[str, Any], context: str) -> Dict[str, Any]:
        struct_score,   struct_issues   = self.evaluate_structure(insights)
        ground_score,   ground_issues   = self.evaluate_grounding(insights, context)
        qual_score,     qual_issues     = self.evaluate_quality(insights)
        coverage_score, coverage_issues = self.evaluate_coverage(insights)

        # Weights: Grounding=40%, Quality=25%, Structure=20%, Coverage=15%
        final_score = (
            ground_score   * 0.40 +
            qual_score     * 0.25 +
            struct_score   * 0.20 +
            coverage_score * 0.15
        )

        all_issues = struct_issues + ground_issues + qual_issues + coverage_issues

        return {
            "score":   round(final_score),
            "status":  "pass" if final_score >= 70 else "fail",
            "issues":  all_issues,
            "issue_count": len(all_issues),
            "metrics": {
                "grounding":  ground_score,
                "quality":    qual_score,
                "structure":  struct_score,
                "coverage":   coverage_score,
            },
            "recommendation": self._recommend(final_score, all_issues)
        }

    def evaluate_legal_review(
        self,
        review_findings: List[Dict[str, Any]],
        clauses: List[Dict[str, Any]],
        contract_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues = []
        clause_text = "\n\n".join(clause.get("clause_text", "") for clause in clauses)
        clause_text_lower = clause_text.lower()

        structure_score = 100
        grounding_score = 100
        severity_score = 100
        completeness_score = 100

        clause_types_present = {clause.get("type", "") for clause in clauses if clause.get("type")}
        doc_type = contract_profile.get("document_type", "")

        required_fields = {
            "finding_type", "clause_type", "severity", "title",
            "explanation", "clause_refs", "source_quotes", "confidence", "status"
        }

        for idx, finding in enumerate(review_findings):
            missing = required_fields - set(finding.keys())
            if missing:
                issues.append(f"review_findings[{idx}] missing fields: {', '.join(sorted(missing))}")
                structure_score -= 10

            explanation = str(finding.get("explanation", ""))
            severity = str(finding.get("severity", "")).lower()
            finding_type = str(finding.get("finding_type", ""))
            clause_type = str(finding.get("clause_type", ""))
            source_quotes = finding.get("source_quotes", []) or []
            clause_refs = finding.get("clause_refs", []) or []

            for pattern in self.legal_advice_patterns:
                if re.search(pattern, explanation, re.IGNORECASE):
                    issues.append(
                        f"review_findings[{idx}] uses over-assertive legal advice language: '{finding.get('title', '')[:50]}...'"
                    )
                    structure_score -= 8
                    break

            if finding_type in {"risk", "negotiation_point"}:
                if not source_quotes:
                    issues.append(
                        f"review_findings[{idx}] lacks source quote support for {finding_type}: '{finding.get('title', '')[:50]}...'"
                    )
                    grounding_score -= 12
                else:
                    for quote in source_quotes:
                        if quote and self._normalize_text(quote) not in self._normalize_text(clause_text):
                            issues.append(
                                f"review_findings[{idx}] source quote not found in contract text: '{quote[:60]}...'"
                            )
                            grounding_score -= 10

            if severity == "high":
                if finding_type == "missing_protection":
                    if clause_type not in self.high_value_legal_clauses:
                        issues.append(
                            f"review_findings[{idx}] high severity missing protection is not tied to a core clause type: '{finding.get('title', '')[:50]}...'"
                        )
                        severity_score -= 10
                elif not source_quotes or not clause_refs:
                    issues.append(
                        f"review_findings[{idx}] high severity finding needs stronger evidence linkage: '{finding.get('title', '')[:50]}...'"
                    )
                    severity_score -= 14

            confidence = finding.get("confidence")
            if confidence is None or not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                issues.append(f"review_findings[{idx}] has invalid confidence value: {confidence}")
                structure_score -= 5

        if doc_type in {"msa", "sow", "vendor_agreement"}:
            covered = len(clause_types_present.intersection(self.high_value_legal_clauses))
            if covered < 3:
                issues.append(
                    f"Legal review completeness is low: only {covered} of 5 high-value clause types detected."
                )
                completeness_score -= 40
            elif covered < 4:
                issues.append(
                    f"Legal review completeness is moderate: only {covered} of 5 high-value clause types detected."
                )
                completeness_score -= 20
            if len(review_findings) == 0:
                issues.append("No legal review findings were generated for a commercial contract.")
                completeness_score -= 25

        final_score = (
            max(0, grounding_score) * 0.30 +
            max(0, severity_score) * 0.20 +
            max(0, structure_score) * 0.15 +
            max(0, completeness_score) * 0.35
        )

        if final_score >= 88:
            status = "pass"
        elif final_score >= 72:
            status = "needs_review"
        else:
            status = "fail"

        if doc_type in {"msa", "sow", "vendor_agreement"}:
            covered = len(clause_types_present.intersection(self.high_value_legal_clauses))
            if covered < 3 and status == "pass":
                status = "needs_review"

        recommendation = "Legal review findings look well-supported."
        if status == "needs_review":
            recommendation = "Legal review findings are usable, but a reviewer should inspect flagged issues and missing coverage."
        elif status == "fail":
            recommendation = "Legal review findings are not reliable enough yet. Improve clause coverage or evidence support before delivery."

        return {
            "score": round(final_score),
            "status": status,
            "issues": issues,
            "issue_count": len(issues),
            "metrics": {
                "grounding": max(0, grounding_score),
                "severity_calibration": max(0, severity_score),
                "structure": max(0, structure_score),
                "completeness": max(0, completeness_score),
            },
            "recommendation": recommendation,
        }

    def _recommend(self, score: float, issues: List[str]) -> str:
        if score >= 85:
            return "Output quality is high — safe to show to client."
        if score >= 70:
            return "Acceptable quality — review flagged issues before client delivery."
        hallucination_flags = [i for i in issues if "Hallucination" in i or "semantic" in i.lower()]
        if hallucination_flags:
            return "BLOCK — hallucination risk detected. Do not show to client. Re-run with better context."
        generic_flags = [i for i in issues if "generic" in i.lower()]
        if generic_flags:
            return "REJECT — insights are too generic. Improve retrieval and re-generate."
        return "FAIL — multiple quality issues. Check metrics for details."
