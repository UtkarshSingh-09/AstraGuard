from __future__ import annotations

from typing import Any


def _clamp(value: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(value))))


def calculate_arth_score(user: dict[str, Any] | None) -> dict[str, Any]:
    if not user:
        total = 500
        return {
            "total": total,
            "max": 1000,
            "percentile": 50,
            "breakdown": {
                "emergency_fund": {"score": 50, "max": 100, "status": "warning"},
                "insurance": {"score": 50, "max": 100, "status": "warning"},
                "tax_efficiency": {"score": 50, "max": 100, "status": "warning"},
                "investment_health": {"score": 50, "max": 100, "status": "warning"},
                "goal_progress": {"score": 50, "max": 100, "status": "warning"},
                "behavioral_discipline": {"score": 50, "max": 100, "status": "warning"},
            },
            "improvement_suggestion": "Complete onboarding and connect portfolio for a more accurate score",
            "next_milestone": {"score": 700, "actions_needed": ["Finish onboarding", "Add investment details"]},
        }

    fdna = user.get("financial_dna", {})
    bdna = user.get("behavioral_dna", {})
    fire = user.get("latest_fire_result", {})
    tax = user.get("latest_tax_result", {})
    portfolio = user.get("latest_portfolio_summary", {})

    monthly_expenses = float(fdna.get("monthly_expenses", 0) or 0)
    emergency_fund = float(fdna.get("emergency_fund", 0) or 0)
    ef_months = (emergency_fund / monthly_expenses) if monthly_expenses > 0 else 0
    emergency_score = _clamp((ef_months / 6) * 100)

    insurance_gap = float(fire.get("insurance_gap", 0) or fire.get("gap", 0) or 0)
    insurance_score = _clamp(100 - min((insurance_gap / 100000.0), 100))

    savings = float(tax.get("savings_with_optimal", 0) or 0)
    tax_score = _clamp(min(100, 50 + (savings / 1000)))

    outperformance = float(portfolio.get("outperformance", 0) or 0)
    investment_score = _clamp(60 + (outperformance * 5))

    goals = fdna.get("goals", [])
    goal_progress = 70 if goals else 50
    goal_score = _clamp(goal_progress)

    behavioral_score = _clamp(float(bdna.get("behavioral_discipline_score", 50) or 50))

    total = emergency_score + insurance_score + tax_score + investment_score + goal_score + behavioral_score
    percentile = _clamp((total / 1000) * 100, 1, 99)

    return {
        "total": total,
        "max": 1000,
        "percentile": percentile,
        "breakdown": {
            "emergency_fund": {"score": emergency_score, "max": 100, "status": "good" if emergency_score >= 70 else "warning", "months_covered": round(ef_months, 1), "target": 6},
            "insurance": {"score": insurance_score, "max": 100, "status": "good" if insurance_score >= 70 else "warning", "gap_cr": round(insurance_gap / 10000000, 2)},
            "tax_efficiency": {"score": tax_score, "max": 100, "status": "excellent" if tax_score >= 80 else "warning", "saved_this_fy": round(savings)},
            "investment_health": {"score": investment_score, "max": 100, "status": "good" if investment_score >= 70 else "warning", "xirr": portfolio.get("portfolio_xirr"), "overlap": portfolio.get("overlap_severity")},
            "goal_progress": {"score": goal_score, "max": 100, "status": "good" if goal_score >= 70 else "warning", "goals_on_track": len(goals), "total_goals": len(goals)},
            "behavioral_discipline": {"score": behavioral_score, "max": 100, "status": "needs_work" if behavioral_score < 70 else "good", "sip_pauses_12m": bdna.get("sip_pauses_last_12m", 0), "panic_checks": bdna.get("panic_portfolio_checks", 0)},
        },
        "improvement_suggestion": "Improve Behavioral Discipline to raise overall score faster",
        "next_milestone": {"score": min(total + 50, 900), "actions_needed": ["No SIP pause this month", "Avoid panic portfolio checks on red days"]},
    }
