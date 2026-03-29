"""
Pydantic models for API request/response contracts.
Ankit's FastAPI routes use these to validate incoming requests
and structure outgoing responses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


# ═══════════════════════════════════════════════════════════════════════
# ONBOARDING
# ═══════════════════════════════════════════════════════════════════════

class OnboardRequest(BaseModel):
    session_id: str
    conversation_history: list[dict]  # [{role, content}]
    extraction_complete: bool = False


class OnboardResponse(BaseModel):
    status: Literal["gathering", "complete"]
    next_question: str | None = None
    extracted_so_far: dict = Field(default_factory=dict)
    behavioral_dna: dict | None = None
    completion_percentage: int = 0
    user_id: str | None = None
    financial_dna: dict | None = None
    arth_score: dict | None = None
    literacy_quiz: dict | None = None  # initial literacy assessment
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════
# FIRE PLAN
# ═══════════════════════════════════════════════════════════════════════

class FireRequest(BaseModel):
    user_id: str
    inputs: dict  # age, salary, expenses, mf, ppf, target_draw, retire_age, etc.


class FireResponse(BaseModel):
    status: str = "success"
    calculation_id: str | None = None
    summary: dict = Field(default_factory=dict)
    glidepath: list[dict] = Field(default_factory=list)
    insurance_gap: dict = Field(default_factory=dict)
    emergency_fund: dict = Field(default_factory=dict)
    consequence_timeline: list[dict] = Field(default_factory=list)
    llm_narration: str | None = None
    audit_trail: list[dict] = Field(default_factory=list)
    audit_narration: list[dict] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    literacy_insight: dict | None = None
    sebi_disclaimer: str = ""
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════
# TAX
# ═══════════════════════════════════════════════════════════════════════

class TaxRequest(BaseModel):
    user_id: str
    inputs: dict  # salary, hra, rent, 80c, nps, home_loan, 80d, etc.


class TaxResponse(BaseModel):
    status: str = "success"
    calculation_id: str | None = None
    old_regime: dict = Field(default_factory=dict)
    new_regime: dict = Field(default_factory=dict)
    comparison: dict = Field(default_factory=dict)
    missed_deductions: list[dict] = Field(default_factory=list)
    instrument_recommendations: list[dict] = Field(default_factory=list)
    llm_explanation: str | None = None
    audit_trail: list[dict] = Field(default_factory=list)
    audit_narration: list[dict] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    literacy_insight: dict | None = None
    sebi_disclaimer: str = ""
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════
# PORTFOLIO X-RAY
# ═══════════════════════════════════════════════════════════════════════

class PortfolioXrayRequest(BaseModel):
    user_id: str
    mode: Literal["cams_auto", "mock"] = "mock"
    mock_scenario: str | None = "overlap_heavy"
    pan: str | None = None
    email: str | None = None


class PortfolioXrayResponse(BaseModel):
    status: str = "processing"
    job_id: str | None = None
    estimated_seconds: int = 45
    portfolio_summary: dict | None = None
    funds: list[dict] = Field(default_factory=list)
    overlap_analysis: dict | None = None
    expense_analysis: dict | None = None
    rebalancing_plan: list[dict] = Field(default_factory=list)
    llm_narration: str | None = None
    audit_trail: list[dict] = Field(default_factory=list)
    audit_narration: list[dict] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    literacy_insight: dict | None = None
    sebi_disclaimer: str = ""
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════
# BEHAVIORAL / INTERVENTION
# ═══════════════════════════════════════════════════════════════════════

class InterventionSimulateRequest(BaseModel):
    user_id: str
    market_drop_pct: float
    send_whatsapp: bool = True
    send_push: bool = True


class InterventionResponse(BaseModel):
    risk_state: dict = Field(default_factory=dict)
    consequence_simulation: dict = Field(default_factory=dict)
    intervention_message: dict = Field(default_factory=dict)
    whatsapp_sent: bool = False
    whatsapp_sid: str | None = None
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════
# LIFE SIMULATOR
# ═══════════════════════════════════════════════════════════════════════

class LifeSimulatorRequest(BaseModel):
    user_id: str
    event_description: str
    financial_dna: dict | None = None
    behavioral_dna: dict | None = None


class LifeSimulatorResponse(BaseModel):
    event_type: str = ""
    impacts: dict = Field(default_factory=dict)
    narration: str | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    urgency: str = "MEDIUM"
    error: str | None = None
