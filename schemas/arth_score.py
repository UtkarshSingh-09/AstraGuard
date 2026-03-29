"""
Pydantic models for Arth Score — the 6-dimension financial wellness metric.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArthScoreDimension(BaseModel):
    """Single dimension of the Arth Score."""

    score: int = 0          # 0–100
    max_score: int = 100
    status: str = "unknown"  # excellent, good, warning, needs_work, critical
    detail: str = ""          # human-readable detail

    def compute_status(self) -> str:
        if self.score >= 85:
            self.status = "excellent"
        elif self.score >= 70:
            self.status = "good"
        elif self.score >= 50:
            self.status = "warning"
        elif self.score >= 30:
            self.status = "needs_work"
        else:
            self.status = "critical"
        return self.status


class EmergencyFundDimension(ArthScoreDimension):
    months_covered: float = 0.0
    target_months: int = 6


class InsuranceDimension(ArthScoreDimension):
    cover_existing: float = 0.0
    cover_needed: float = 0.0
    gap_cr: float = 0.0


class TaxEfficiencyDimension(ArthScoreDimension):
    saved_this_fy: float = 0.0
    potential_saving: float = 0.0


class InvestmentHealthDimension(ArthScoreDimension):
    portfolio_xirr: float | None = None
    overlap_severity: str = "UNKNOWN"  # LOW, MEDIUM, HIGH
    expense_drag_annual: float = 0.0


class GoalProgressDimension(ArthScoreDimension):
    goals_on_track: int = 0
    total_goals: int = 0


class BehavioralDisciplineDimension(ArthScoreDimension):
    sip_pauses_12m: int = 0
    panic_checks: int = 0
    streak_days: int = 0


class ArthScore(BaseModel):
    """
    AstraGuard's proprietary financial wellness score.
    Total: 0–1000 (weighted sum of 6 dimensions × 100 each,
    scaled with different weights).
    """

    total: int = 0
    max_score: int = 1000
    percentile: int | None = None  # among all AstraGuard users

    emergency_fund: EmergencyFundDimension = Field(
        default_factory=EmergencyFundDimension
    )
    insurance: InsuranceDimension = Field(
        default_factory=InsuranceDimension
    )
    tax_efficiency: TaxEfficiencyDimension = Field(
        default_factory=TaxEfficiencyDimension
    )
    investment_health: InvestmentHealthDimension = Field(
        default_factory=InvestmentHealthDimension
    )
    goal_progress: GoalProgressDimension = Field(
        default_factory=GoalProgressDimension
    )
    behavioral_discipline: BehavioralDisciplineDimension = Field(
        default_factory=BehavioralDisciplineDimension
    )

    improvement_suggestion: str = ""
    next_milestone: dict = Field(default_factory=dict)

    # Weights for final score calculation (sum = 10)
    WEIGHTS: dict = Field(
        default={
            "emergency_fund": 1.5,
            "insurance": 1.5,
            "tax_efficiency": 1.5,
            "investment_health": 2.0,
            "goal_progress": 2.0,
            "behavioral_discipline": 1.5,
        },
        exclude=True,
    )

    def compute_total(self) -> int:
        """Compute weighted total score out of 1000."""
        dimensions = {
            "emergency_fund": self.emergency_fund.score,
            "insurance": self.insurance.score,
            "tax_efficiency": self.tax_efficiency.score,
            "investment_health": self.investment_health.score,
            "goal_progress": self.goal_progress.score,
            "behavioral_discipline": self.behavioral_discipline.score,
        }
        weighted_sum = sum(
            dimensions[dim] * self.WEIGHTS[dim]
            for dim in dimensions
        )
        self.total = int(weighted_sum)
        return self.total

    def to_breakdown_dict(self) -> dict:
        """Return breakdown suitable for API response."""
        return {
            "emergency_fund": self.emergency_fund.model_dump(),
            "insurance": self.insurance.model_dump(),
            "tax_efficiency": self.tax_efficiency.model_dump(),
            "investment_health": self.investment_health.model_dump(),
            "goal_progress": self.goal_progress.model_dump(),
            "behavioral_discipline": self.behavioral_discipline.model_dump(),
        }
