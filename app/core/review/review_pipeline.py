from app.core.review.issue_spotter import spot_clause_issues


def build_review_findings(contract_profile: dict, clauses: list[dict]) -> list[dict]:
    return spot_clause_issues(contract_profile, clauses)
