from pydantic import BaseModel
from typing import List, Literal


class Risk(BaseModel):
    finding: str
    severity: Literal["high", "medium", "low"]
    reason: str


class Action(BaseModel):
    action: str
    rationale: str


class DecisionOutput(BaseModel):
    summary: str
    key_insights: List[str]
    risks: List[Risk]                     # ✅ FIXED
    opportunities: List[str]
    recommended_actions: List[Action]     # ✅ FIXED
    confidence_score: float
    context_coverage: Literal["full", "partial", "insufficient"]
    sources_used: List[str]