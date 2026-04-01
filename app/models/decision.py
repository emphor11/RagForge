from pydantic import BaseModel
from typing import List, Literal, Optional


class Insight(BaseModel):
    insight: str
    source: str
    confidence: float


class Risk(BaseModel):
    finding: str
    severity: Literal["high", "medium", "low"]
    reason: str
    source: str
    confidence: float


class Opportunity(BaseModel):
    finding: str
    source: str
    confidence: float


class Action(BaseModel):
    action: str
    rationale: str
    source: str
    confidence: float


class DecisionOutput(BaseModel):
    reasoning: str
    summary: str
    key_insights: List[Insight]
    risks: List[Risk]
    opportunities: List[Opportunity]
    recommended_actions: List[Action]
    overall_confidence: float
    context_quality: Literal["full", "partial", "insufficient"]
    context_gap: Optional[str] = None