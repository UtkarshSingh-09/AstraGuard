from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any


def _future_value_lumpsum(amount: float, annual_rate: float, years: float) -> float:
    return amount * ((1 + annual_rate) ** years)


def _future_value_sip(monthly_sip: float, annual_rate: float, months: int) -> float:
    if monthly_sip <= 0 or months <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return monthly_sip * months
    return monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate)


def _required_monthly_sip_for_fv(target_fv: float, annual_rate: float, months: int) -> float:
    if target_fv <= 0:
        return 0.0
    if months <= 0:
        return target_fv
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return target_fv / months
    denom = ((1 + monthly_rate) ** months - 1) / monthly_rate
    if denom <= 0:
        return target_fv
    return target_fv / denom


def _inflation_adjusted_monthly_need(target_monthly_draw_today_value: float, inflation_rate: float, years: float) -> float:
    return target_monthly_draw_today_value * ((1 + inflation_rate) ** years)


def _corpus_needed(monthly_need_at_retire: float, safe_withdrawal_rate: float = 0.04) -> float:
    return (monthly_need_at_retire * 12) / safe_withdrawal_rate


def _estimate_retire_age_with_sip(
    *,
    age: int,
    target_monthly_draw_today_value: float,
    inflation_rate: float,
    equity_return: float,
    debt_return: float,
    existing_mf: float,
    existing_ppf: float,
    existing_epf: float,
    monthly_sip: float,
    max_years: int = 40,
) -> float:
    # Scan in 0.1-year steps for practical precision without heavy compute.
    step = 0.1
    points = int(max_years / step)
    for i in range(1, points + 1):
        years = i * step
        months = max(1, int(round(years * 12)))
        monthly_need = _inflation_adjusted_monthly_need(
            target_monthly_draw_today_value=target_monthly_draw_today_value,
            inflation_rate=inflation_rate,
            years=years,
        )
        needed = _corpus_needed(monthly_need)
        projected = (
            _future_value_lumpsum(existing_mf, equity_return, years)
            + _future_value_lumpsum(existing_ppf + existing_epf, debt_return, years)
            + _future_value_sip(monthly_sip, equity_return, months)
        )
        if projected >= needed:
            return round(age + years, 1)
    return round(age + max_years, 1)


def calculate_fire_plan(inputs: dict[str, Any]) -> dict[str, Any]:
    age = int(inputs["age"])
    target_retire_age = int(inputs["target_retire_age"])
    if target_retire_age <= age:
        raise ValueError("Retirement age must be greater than current age")

    annual_salary = float(inputs["annual_salary"])
    monthly_expenses = float(inputs["monthly_expenses"])
    existing_mf = float(inputs.get("existing_mf", 0))
    existing_ppf = float(inputs.get("existing_ppf", 0))
    existing_epf = float(inputs.get("existing_epf", 0))
    monthly_sip_current = float(inputs.get("monthly_sip_current", 0))
    target_monthly_draw = float(inputs["target_monthly_draw"])

    inflation_rate = float(inputs.get("inflation_rate", 0.06))
    equity_return = float(inputs.get("equity_return", 0.12))
    debt_return = float(inputs.get("debt_return", 0.07))
    safe_withdrawal_rate = float(inputs.get("safe_withdrawal_rate", 0.04))
    insurance_cover_existing = float(inputs.get("insurance_cover_existing", 0))
    emergency_fund_current = float(inputs.get("emergency_fund_current", 0))

    years_to_retire = target_retire_age - age
    months_to_retire = years_to_retire * 12

    monthly_need_at_retire = _inflation_adjusted_monthly_need(
        target_monthly_draw_today_value=target_monthly_draw,
        inflation_rate=inflation_rate,
        years=years_to_retire,
    )
    if safe_withdrawal_rate <= 0:
        raise ValueError("safe_withdrawal_rate must be greater than 0")
    corpus_needed = _corpus_needed(monthly_need_at_retire, safe_withdrawal_rate=safe_withdrawal_rate)

    projected_existing = (
        _future_value_lumpsum(existing_mf, equity_return, years_to_retire)
        + _future_value_lumpsum(existing_ppf + existing_epf, debt_return, years_to_retire)
    )
    projected_with_current_sip = projected_existing + _future_value_sip(
        monthly_sip_current,
        equity_return,
        months_to_retire,
    )
    corpus_gap = corpus_needed - projected_with_current_sip

    monthly_sip_total_needed = _required_monthly_sip_for_fv(
        target_fv=max(corpus_needed - projected_existing, 0),
        annual_rate=equity_return,
        months=months_to_retire,
    )
    monthly_sip_needed_additional = max(monthly_sip_total_needed - monthly_sip_current, 0)

    estimated_retire_age_current = _estimate_retire_age_with_sip(
        age=age,
        target_monthly_draw_today_value=target_monthly_draw,
        inflation_rate=inflation_rate,
        equity_return=equity_return,
        debt_return=debt_return,
        existing_mf=existing_mf,
        existing_ppf=existing_ppf,
        existing_epf=existing_epf,
        monthly_sip=monthly_sip_current,
    )
    estimated_retire_age_with_plan = _estimate_retire_age_with_sip(
        age=age,
        target_monthly_draw_today_value=target_monthly_draw,
        inflation_rate=inflation_rate,
        equity_return=equity_return,
        debt_return=debt_return,
        existing_mf=existing_mf,
        existing_ppf=existing_ppf,
        existing_epf=existing_epf,
        monthly_sip=monthly_sip_current + monthly_sip_needed_additional,
    )

    income_years_remaining = max(0, 60 - age)
    cover_needed = annual_salary * income_years_remaining * 0.5
    insurance_gap = max(0.0, cover_needed - insurance_cover_existing)

    emergency_target = monthly_expenses * 6
    emergency_gap = max(0.0, emergency_target - emergency_fund_current)
    emergency_months_covered = (emergency_fund_current / monthly_expenses) if monthly_expenses > 0 else 0

    glidepath = [
        {"age_range": f"{age}-{max(age, target_retire_age - 6)}", "equity_pct": 80, "debt_pct": 20, "note": "Aggressive growth phase"},
        {"age_range": f"{max(age, target_retire_age - 6)}-{max(age, target_retire_age - 2)}", "equity_pct": 60, "debt_pct": 40, "note": "Transition phase"},
        {"age_range": f"{max(age, target_retire_age - 2)}-{target_retire_age}", "equity_pct": 40, "debt_pct": 60, "note": "Capital preservation"},
        {"age_range": f"{target_retire_age}+", "equity_pct": 30, "debt_pct": 70, "note": "Income generation"},
    ]

    year_now = datetime.now().year
    month_by_month_plan = []
    running_corpus = existing_mf + existing_ppf + existing_epf
    sip_total = monthly_sip_current + monthly_sip_needed_additional
    for m in range(1, min(months_to_retire, 12) + 1):
        running_corpus = (running_corpus * (1 + (equity_return / 12))) + sip_total
        year = year_now + ((m - 1) // 12)
        month_by_month_plan.append(
            {
                "month": ((m - 1) % 12) + 1,
                "year": year,
                "age": round(age + (m / 12), 1),
                "corpus_value": round(running_corpus),
                "equity_allocation": round(running_corpus * 0.8),
                "debt_allocation": round(running_corpus * 0.2),
                "sip_this_month": round(sip_total),
                "goal_progress": {
                    "retirement": round(min((running_corpus / corpus_needed) * 100, 100), 1),
                    "emergency_fund": round(min((emergency_fund_current / max(emergency_target, 1)) * 100, 100), 1),
                },
            }
        )

    consequence_timeline = [
        {"age": age + 2, "event": f"₹{ceil(max(monthly_sip_needed_additional, 1) * 24):,} compounding advantage locked in"},
        {"age": age + 8, "event": "Primary mid-term goal funding milestone"},
        {"age": max(target_retire_age - 2, age + 1), "event": "Portfolio shifts to capital preservation"},
        {"age": target_retire_age, "event": f"Retirement target check - corpus goal ₹{round(corpus_needed):,}"},
        {"age": target_retire_age + 15, "event": "Legacy potential improves with disciplined SIP continuity"},
    ]

    audit_trail = [
        {
            "step": "inflation_adjusted_monthly_need",
            "formula": "target_monthly_draw * (1 + inflation_rate) ^ years_to_retire",
            "inputs": {
                "target_monthly_draw": target_monthly_draw,
                "inflation_rate": inflation_rate,
                "years_to_retire": years_to_retire,
            },
            "result": round(monthly_need_at_retire, 2),
        },
        {
            "step": "corpus_needed",
            "formula": "monthly_need_at_retire * 12 / safe_withdrawal_rate",
            "inputs": {
                "monthly_need_at_retire": round(monthly_need_at_retire, 2),
                "safe_withdrawal_rate": safe_withdrawal_rate,
            },
            "result": round(corpus_needed, 2),
        },
        {
            "step": "projected_existing_corpus",
            "formula": "FV(existing_mf, equity_return) + FV(existing_ppf + existing_epf, debt_return)",
            "inputs": {
                "existing_mf": existing_mf,
                "existing_ppf": existing_ppf,
                "existing_epf": existing_epf,
                "equity_return": equity_return,
                "debt_return": debt_return,
                "years_to_retire": years_to_retire,
            },
            "result": round(projected_existing, 2),
        },
        {
            "step": "required_total_sip",
            "formula": "PMT(target=corpus_needed - projected_existing)",
            "inputs": {"months_to_retire": months_to_retire, "equity_return": equity_return},
            "result": round(monthly_sip_total_needed, 2),
        },
    ]

    return {
        "status": "success",
        "summary": {
            "corpus_needed": round(corpus_needed),
            "corpus_at_retire_current_trajectory": round(projected_with_current_sip),
            "corpus_gap": round(corpus_gap),
            "monthly_sip_needed_additional": round(monthly_sip_needed_additional),
            "monthly_sip_total_needed": round(monthly_sip_total_needed),
            "estimated_retire_age_current": estimated_retire_age_current,
            "estimated_retire_age_with_plan": estimated_retire_age_with_plan,
            "retire_age_delta_years": round(max(estimated_retire_age_current - target_retire_age, 0), 1),
        },
        "glidepath": glidepath,
        "insurance_gap": {
            "cover_needed": round(cover_needed),
            "cover_existing": round(insurance_cover_existing),
            "gap": round(insurance_gap),
            "recommendation": "Close gap with term plan after underwriting comparison.",
        },
        "emergency_fund": {
            "target": round(emergency_target),
            "current": round(emergency_fund_current),
            "gap": round(emergency_gap),
            "months_covered": round(emergency_months_covered, 1),
            "target_months": 6,
        },
        "month_by_month_plan": month_by_month_plan,
        "consequence_timeline": consequence_timeline,
        "audit_trail": audit_trail,
    }
