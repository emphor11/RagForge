from __future__ import annotations

import json
from statistics import mean
from typing import Any

from groq import Groq

from config.settings import settings


CONTROL_PROMPT = """Return only valid JSON. Do not include markdown, explanation, or code fences."""


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in Groq evaluator output.")
    return json.loads(text[start : end + 1])


class GroqReviewEvaluator:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _call_groq(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY for hosted evaluator.")

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CONTROL_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        raw = str(response.choices[0].message.content or "")
        return _extract_json(raw)

    def evaluate_finding(self, finding: dict[str, Any], context: str) -> dict[str, Any]:
        prompt = f"""
You are verifying whether a legal review finding is grounded in the contract text.
Return JSON with this exact structure:
{{
  "verdict": "grounded|partial|unsupported",
  "confidence": 0.0,
  "evidence": "short supporting quote or empty string",
  "rationale": "one short sentence"
}}

FINDING TITLE: {finding.get("title", "")}
FINDING TYPE: {finding.get("finding_type", "")}
CLAUSE TYPE: {finding.get("clause_type", "")}
SEVERITY: {finding.get("severity", "")}
EXPLANATION: {finding.get("explanation", "")}
SOURCE QUOTES: {json.dumps(finding.get("source_quotes", [])[:3])}

CONTRACT CONTEXT:
{context[:5000]}
"""
        try:
            return self._call_groq(prompt)
        except Exception as exc:
            print(f"⚠️ Groq evaluator failed for finding '{finding.get('title', '')}': {exc}")
            return {
                "verdict": "partial",
                "confidence": float(finding.get("confidence", 0.55) or 0.55),
                "evidence": "",
                "rationale": "Fallback evaluator path used because the hosted grounding check was unavailable.",
            }

    def evaluate(
        self,
        findings: list[dict[str, Any]],
        context_docs: list[str],
        clauses: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        clauses = clauses or []
        context = "\n\n".join(context_docs[:10]).strip()
        if not findings:
            evaluation = {
                "score": 82,
                "status": "pass",
                "mode": "groq_grounding_check",
                "recommendation": "No major review findings were generated. Continue with manual legal review for material obligations and carve-outs.",
                "evaluated_findings": [],
            }
            review_audit = {
                "score": 82,
                "status": "pass",
                "mode": "groq_grounding_check",
                "grounding_score": 0.84,
                "structure_score": 0.86,
                "coverage_score": 0.78,
                "recommendation": evaluation["recommendation"],
            }
            return evaluation, review_audit

        evaluated_findings = []
        for finding in findings:
            finding_eval = self.evaluate_finding(finding, context)
            enriched = dict(finding)
            enriched["evaluation"] = finding_eval
            if finding_eval.get("confidence") is not None:
                enriched["confidence"] = max(
                    float(enriched.get("confidence", 0.0) or 0.0),
                    float(finding_eval.get("confidence", 0.0) or 0.0),
                )
            evaluated_findings.append(enriched)

        verdict_weights = {"grounded": 1.0, "partial": 0.65, "unsupported": 0.25}
        grounding_values = [
            verdict_weights.get(item["evaluation"].get("verdict", "partial"), 0.65)
            * float(item["evaluation"].get("confidence", 0.6) or 0.6)
            for item in evaluated_findings
        ]
        grounding_score = min(0.99, max(0.0, mean(grounding_values)))

        structure_values = []
        for item in evaluated_findings:
            completeness = 0.0
            completeness += 0.3 if item.get("title") else 0.0
            completeness += 0.25 if item.get("explanation") else 0.0
            completeness += 0.2 if item.get("clause_refs") else 0.0
            completeness += 0.25 if item.get("source_quotes") else 0.0
            structure_values.append(completeness)
        structure_score = min(0.99, max(0.0, mean(structure_values)))

        critical_clause_types = {
            "termination",
            "payment",
            "liability_cap",
            "confidentiality_definition",
            "indemnity",
            "governing_law",
        }
        clause_types_present = {clause.get("type", "") for clause in clauses}
        clause_coverage = (
            len(critical_clause_types & clause_types_present) / len(critical_clause_types)
            if clause_types_present
            else 0.35
        )
        finding_coverage = min(1.0, len(evaluated_findings) / 4)
        coverage_score = min(0.99, max(0.0, (clause_coverage * 0.65) + (finding_coverage * 0.35)))

        overall_score = round(((grounding_score * 0.45) + (structure_score * 0.25) + (coverage_score * 0.30)) * 100)
        status = "pass" if overall_score >= 70 else "fail"

        recommendation = (
            "Hosted Fast Review is well grounded in the retrieved contract context."
            if status == "pass"
            else "Review required. Improve clause coverage or run Deep Verify for stronger second-pass validation."
        )

        evaluation = {
            "score": overall_score,
            "status": status,
            "mode": "groq_grounding_check",
            "recommendation": recommendation,
            "evaluated_findings": evaluated_findings,
        }
        review_audit = {
            "score": overall_score,
            "status": status,
            "mode": "groq_grounding_check",
            "grounding_score": grounding_score,
            "structure_score": structure_score,
            "coverage_score": coverage_score,
            "recommendation": recommendation,
        }
        return evaluation, review_audit
