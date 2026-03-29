"""
Pydantic models for Financial DNA, Behavioral DNA, and Goals.
These are the core data contracts shared between agents and the backend.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class CityType(str, Enum):
    METRO = "metro"
    NON_METRO = "non-metro"


class BehaviorType(str, Enum):
    PANIC_PRONE = "panic_prone"
    DISCIPLINED = "disciplined"
    IMPULSIVE = "impulsive"
    PASSIVE = "passive"
    MODERATE = "moderate"


class RecoveryAwareness(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ─── Sub-models ───────────────────────────────────────────────────────────────

class ExistingInvestments(BaseModel):
    mutual_funds: float = 0.0
    ppf: float = 0.0
    fd: float = 0.0
    stocks: float = 0.0
    epf: float = 0.0
    nps: float = 0.0
    gold: float = 0.0
    real_estate: float = 0.0


class Goal(BaseModel):
    id: str | None = None
    name: str
    target_amount: float | None = None
    target_year: int | None = None
    monthly_draw_today_value: float | None = None  # for retirement-type goals
    target_age: int | None = None  # for retirement-type goals
    emotional_label: str | None = None  # e.g., "Priya's IIT Fund", "Freedom"
    priority: int = 1  # 1 = highest


# ─── Core DNA Models ─────────────────────────────────────────────────────────

class FinancialDNA(BaseModel):
    """User's complete financial profile extracted from conversation."""

    age: int | None = None
    annual_salary: float | None = None
    monthly_expenses: float | None = None
    existing_investments: ExistingInvestments = Field(
        default_factory=ExistingInvestments
    )
    goals: list[Goal] = Field(default_factory=list)
    insurance_cover: float | None = None
    risk_profile: RiskProfile | None = None
    city_type: CityType | None = None
    dependents: int | None = None
    spouse_income: float | None = None
    has_home_loan: bool = False
    home_loan_interest_annual: float | None = None
    rent_paid_monthly: float | None = None
    hra_received: float | None = None

    def total_existing_corpus(self) -> float:
        """Sum of all existing investments."""
        inv = self.existing_investments
        return (
            inv.mutual_funds + inv.ppf + inv.fd + inv.stocks
            + inv.epf + inv.nps + inv.gold + inv.real_estate
        )


class BehavioralDNA(BaseModel):
    """User's behavioral profile for panic detection and intervention."""

    panic_threshold: float = -15.0  # market drop % that triggers panic
    behavior_type: BehaviorType = BehaviorType.MODERATE  # mapped later
    last_panic_event: str | None = None  # e.g., "COVID March 2020"
    action_rate: float = 0.5  # 0.0 (never acts) to 1.0 (always acts on impulse)
    recovery_awareness: RecoveryAwareness = RecoveryAwareness.MEDIUM
    behavioral_discipline_score: int = 50  # 0–100
    self_reported: bool = True
    sip_pauses_last_12m: int = 0
    panic_portfolio_checks: int = 0

    # Workaround: use_enum_values for string serialization
    model_config = {"use_enum_values": True}


class LiteracyScores(BaseModel):
    """Tracks user financial literacy per dimension."""

    tax: int = 0       # 0–100
    mutual_funds: int = 0
    fire: int = 0
    insurance: int = 0
    overall: int = 0

    def compute_overall(self) -> int:
        scores = [self.tax, self.mutual_funds, self.fire, self.insurance]
        self.overall = sum(scores) // len(scores) if scores else 0
        return self.overall


class UserProfile(BaseModel):
    """Complete user profile combining all DNA components."""

    user_id: str
    financial_dna: FinancialDNA = Field(default_factory=FinancialDNA)
    behavioral_dna: BehavioralDNA = Field(default_factory=BehavioralDNA)
    literacy_scores: LiteracyScores = Field(default_factory=LiteracyScores)
    phone_number: str | None = None  # for WhatsApp
    preferred_language: str = "hinglish"  # hinglish, english, hindi
