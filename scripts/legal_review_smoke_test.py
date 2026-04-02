import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.ingestion.pipeline import ingest_document
from app.core.contracts.profile_builder import build_clause_records, build_contract_profile
from app.core.review.review_pipeline import build_review_findings
from app.evaluation.evaluator import InsightEvaluator


SAMPLES = {
    "nda_sample": """
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement is entered into on 15 March 2026 between Alpha Legal LLP and Beta Systems Private Limited.

1. Definition of Confidential Information.
Confidential Information means all non-public business, financial, technical, and commercial information disclosed by either party.

2. Permitted Use and Non-Disclosure.
The receiving party shall use Confidential Information solely for the Business Purpose and shall not disclose it except to personnel with a need to know.

3. Return or Destruction.
Upon written request, the receiving party shall promptly return or destroy Confidential Information.

7. Term and Survival.
This Agreement will remain in effect for three (3) years.

8. Governing Law and Dispute Resolution.
This Agreement will be governed by the laws of India. Any dispute shall be referred to arbitration in New Delhi.
""".strip(),
    "msa_sample": """
MASTER SERVICES AGREEMENT

This Master Services Agreement is entered into on 1 April 2026 between ClientCo Private Limited and VendorCo Services LLP.

2. Payment Terms.
Customer shall pay invoices upon receipt.

5. Term and Termination.
Either party may terminate this Agreement on 15 days notice.

8. Governing Law.
This Agreement is governed by the laws of India. Any dispute shall be referred to arbitration.
""".strip(),
}


def run_sample(sample_name: str, content: str):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    try:
        document_id = f"{sample_name}.txt"
        chunks = ingest_document(str(temp_path), document_id)
        clause_records = build_clause_records(chunks)
        contract_profile = build_contract_profile(document_id, chunks)
        review_findings = build_review_findings(contract_profile, clause_records)
        evaluator = InsightEvaluator()
        review_audit = evaluator.evaluate_legal_review(
            review_findings=review_findings,
            clauses=clause_records,
            contract_profile=contract_profile,
        )

        return {
            "document_id": document_id,
            "chunk_count": len(chunks),
            "document_type": contract_profile["document_type"],
            "parties": contract_profile["parties"],
            "clause_types": [clause.get("type", "") for clause in clause_records],
            "finding_count": len(review_findings),
            "finding_titles": [finding["title"] for finding in review_findings],
            "review_audit": review_audit,
        }
    finally:
        temp_path.unlink(missing_ok=True)


def main():
    results = {
        sample_name: run_sample(sample_name, content)
        for sample_name, content in SAMPLES.items()
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
