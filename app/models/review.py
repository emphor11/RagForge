from pydantic import BaseModel
from typing import List, Literal


class ReviewFinding(BaseModel):
    finding_type: Literal["risk", "missing_protection", "negotiation_point"]
    clause_type: str
    severity: Literal["high", "medium", "low"]
    title: str
    explanation: str
    clause_refs: List[str]
    source_quotes: List[str]
    confidence: float
    status: Literal["open", "reviewed", "accepted", "dismissed", "escalated"] = "open"
    reviewer_note: str = ""
