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
    mitigation_fix: Optional[str] = None


class Opportunity(BaseModel):
    finding: str
    source: str
    confidence: float


class Action(BaseModel):
    action: str
    rationale: str
    source: str
    confidence: float
    mitigation_fix: Optional[str] = None


class ChatCitation(BaseModel):
    quote: str
    relevance: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[ChatCitation]
    confidence: float
    found_in_document: bool


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