from __future__ import annotations

from typing import Any


def _progressive_tax(income: float, slabs: list[tuple[float, float, float]]) -> tuple[float, list[dict[str, Any]]]:
    """
    slabs format: (lower_inclusive, upper_inclusive, rate_decimal)
    """
    if income <= 0:
        return 0.0, []

    tax = 0.0
    breakdown: list[dict[str, Any]] = []
    for lower, upper, rate in slabs:
        if income <= lower:
            continue
        taxable_part = min(income, upper) - lower
        if taxable_part <= 0:
            continue
        slab_tax = taxable_part * rate
        tax += slab_tax
        upper_label = "and above" if upper == float("inf") else f"{int(upper):,}"
        lower_label = f"{int(lower)+1:,}" if lower > 0 else "0"
        breakdown.append(
            {
                "range": f"{lower_label} - {upper_label}",
                "rate": f"{int(rate * 100)}%",
                "tax": round(slab_tax),
            }
        )
    return tax, breakdown


def _old_regime_slabs_contract_demo() -> list[tuple[float, float, float]]:
    # Contract-aligned slabs from project spec.
    return [
        (0, 300000, 0.00),
        (300000, 700000, 0.05),
        (700000, 1000000, 0.10),
        (1000000, 1200000, 0.15),
        # Using hackathon contract behavior for consistency with provided expected outputs.
        (1200000, float("inf"), 0.20),
    ]


def _new_regime_slabs_contract_demo() -> list[tuple[float, float, float]]:
    return [
        (0, 400000, 0.00),
        (400000, 800000, 0.05),
        (800000, 1200000, 0.10),
        (1200000, 1600000, 0.15),
        (1600000, 2000000, 0.20),
        (2000000, 2400000, 0.25),
        (2400000, float("inf"), 0.30),
    ]


def _old_regime_slabs_research_standard() -> list[tuple[float, float, float]]:
    return [
        (0, 250000, 0.00),
        (250000, 500000, 0.05),
        (500000, 1000000, 0.20),
        (1000000, float("inf"), 0.30),
    ]


def _new_regime_slabs_research_fy_2025_26() -> list[tuple[float, float, float]]:
    return [
        (0, 400000, 0.00),
        (400000, 800000, 0.05),
        (800000, 1200000, 0.10),
        (1200000, 1600000, 0.15),
        (1600000, 2000000, 0.20),
        (2000000, 2400000, 0.25),
        (2400000, float("inf"), 0.30),
    ]


def _resolve_rule_profile(financial_year: str, tax_profile: str) -> dict[str, Any]:
    if tax_profile == "research_standard":
        # Research-locked profile (defaulting to FY2025-26 style in current pack).
        return {
            "old_slabs": _old_regime_slabs_research_standard(),
            "new_slabs": _new_regime_slabs_research_fy_2025_26(),
            "std_old": 75000.0 if financial_year == "2025-26" else 50000.0,
            "std_new": 75000.0 if financial_year in {"2025-26", "2026-27"} else 50000.0,
            "profile_used": "research_standard",
        }
    # Backward-compatible demo contract profile.
    return {
        "old_slabs": _old_regime_slabs_contract_demo(),
        "new_slabs": _new_regime_slabs_contract_demo(),
        "std_old": 50000.0,
        "std_new": 75000.0,
        "profile_used": "contract_demo",
    }


def calculate_tax_comparison(inputs: dict[str, Any]) -> dict[str, Any]:
    base_salary = float(inputs["base_salary"])
    hra_received = float(inputs.get("hra_received", 0))
    rent_paid_monthly = float(inputs.get("rent_paid_monthly", 0))
    city_type = str(inputs.get("city_type", "metro")).lower()
    investments_80c = float(inputs.get("investments_80c", 0))
    nps_80ccd1b = float(inputs.get("nps_80ccd1b", 0))
    home_loan_interest_24b = float(inputs.get("home_loan_interest_24b", 0))
    health_insurance_80d_self = float(inputs.get("health_insurance_80d_self", 0))
    health_insurance_80d_parents = float(inputs.get("health_insurance_80d_parents", 0))
    other_income = float(inputs.get("other_income", 0))
    financial_year = str(inputs.get("financial_year", "2026-27"))
    tax_profile = str(inputs.get("tax_profile", "contract_demo"))

    if base_salary < 0:
        raise ValueError("Base salary cannot be negative")
    if rent_paid_monthly < 0:
        raise ValueError("Rent paid monthly cannot be negative")

    annual_rent = rent_paid_monthly * 12
    metro_pct = 0.50 if city_type == "metro" else 0.40
    hra_exemption = min(
        hra_received,
        metro_pct * base_salary,
        max(0.0, annual_rent - (0.10 * base_salary)),
    )

    gross_income = base_salary + other_income
    rule_profile = _resolve_rule_profile(financial_year, tax_profile)
    std_old = rule_profile["std_old"]
    std_new = rule_profile["std_new"]

    deductions_80c = min(investments_80c, 150000.0)
    deductions_80ccd1b = min(nps_80ccd1b, 50000.0)
    deductions_24b = min(home_loan_interest_24b, 200000.0)
    deductions_80d = min(health_insurance_80d_self + health_insurance_80d_parents, 75000.0)
    total_old_deductions = deductions_80c + deductions_80ccd1b + deductions_24b + deductions_80d

    old_taxable = max(0.0, gross_income - std_old - hra_exemption - total_old_deductions)
    new_taxable = max(0.0, gross_income - std_new)

    old_tax_before_cess, old_slab_breakdown = _progressive_tax(old_taxable, rule_profile["old_slabs"])
    new_tax_before_cess, new_slab_breakdown = _progressive_tax(new_taxable, rule_profile["new_slabs"])

    old_cess = old_tax_before_cess * 0.04
    new_cess = new_tax_before_cess * 0.04
    old_total = old_tax_before_cess + old_cess
    new_total = new_tax_before_cess + new_cess

    if old_total <= new_total:
        optimal_regime = "OLD"
        savings = new_total - old_total
    else:
        optimal_regime = "NEW"
        savings = old_total - new_total

    missed_deductions: list[dict[str, Any]] = []
    used_80d = deductions_80d
    if used_80d < 25000:
        missed_deductions.append(
            {
                "section": "80D",
                "description": "Health Insurance Premium",
                "max_deduction": 25000,
                "potential_tax_saving": round((25000 - used_80d) * 0.20),
                "regime_applicable": "OLD only",
                "action": "Buy family floater and claim health insurance deduction",
                "urgency": "HIGH",
            }
        )
    missed_deductions.append(
        {
            "section": "80TTA",
            "description": "Savings Account Interest",
            "max_deduction": 10000,
            "potential_tax_saving": 2000,
            "regime_applicable": "OLD only",
            "action": "Collect savings account interest certificate and claim if eligible",
        }
    )

    instrument_recommendations = [
        {
            "rank": 1,
            "name": "ELSS Mutual Fund",
            "section": "80C",
            "space_available": max(0, 150000 - deductions_80c),
            "already_maxed": deductions_80c >= 150000,
            "return_range": "12-15%",
            "lock_in": "3 years",
            "liquidity": "LOW",
            "risk": "HIGH",
        },
        {
            "rank": 2,
            "name": "NPS Tier 1 Additional",
            "section": "80CCD(1B)",
            "space_available": max(0, 50000 - deductions_80ccd1b),
            "already_maxed": deductions_80ccd1b >= 50000,
        },
        {
            "rank": 3,
            "name": "Health Insurance 80D",
            "section": "80D",
            "space_available": max(0, 25000 - used_80d),
            "already_maxed": used_80d >= 25000,
            "return_range": "Protection, not investment",
            "liquidity": "N/A",
            "risk": "NONE",
        },
    ]

    audit_trail = [
        {
            "step": "hra_exemption_old_regime",
            "formula": "min(hra_received, city_pct * base_salary, max(0, annual_rent - 10% base_salary))",
            "inputs": {
                "hra_received": hra_received,
                "city_pct": metro_pct,
                "base_salary": base_salary,
                "annual_rent": annual_rent,
            },
            "result": round(hra_exemption, 2),
        },
        {
            "step": "old_taxable_income",
            "formula": "gross_income - std_old - hra_exemption - total_old_deductions",
            "inputs": {
                "gross_income": gross_income,
                "std_old": std_old,
                "hra_exemption": round(hra_exemption, 2),
                "total_old_deductions": round(total_old_deductions, 2),
            },
            "result": round(old_taxable, 2),
        },
        {
            "step": "new_taxable_income",
            "formula": "gross_income - std_new",
            "inputs": {"gross_income": gross_income, "std_new": std_new},
            "result": round(new_taxable, 2),
        },
        {
            "step": "comparison",
            "formula": "abs(old_total_tax - new_total_tax)",
            "inputs": {"old_total_tax": round(old_total, 2), "new_total_tax": round(new_total, 2)},
            "result": round(savings, 2),
        },
    ]

    return {
        "status": "success",
        "tax_profile_used": rule_profile["profile_used"],
        "financial_year": financial_year,
        "old_regime": {
            "gross_income": round(gross_income),
            "standard_deduction": round(std_old),
            "hra_exemption": round(hra_exemption),
            "hra_exemption_note": (
                "Rent paid = ₹0 -> HRA exemption = ₹0. If paying rent, update."
                if annual_rent == 0
                else "HRA exemption computed using min-of-3 rule."
            ),
            "chapter_via_deductions": {
                "80C": round(deductions_80c),
                "80CCD_1B": round(deductions_80ccd1b),
                "24B": round(deductions_24b),
                "80D": round(deductions_80d),
                "total": round(total_old_deductions),
            },
            "net_taxable_income": round(old_taxable),
            "slab_breakdown": old_slab_breakdown,
            "tax_before_cess": round(old_tax_before_cess),
            "health_education_cess": round(old_cess),
            "total_tax": round(old_total),
        },
        "new_regime": {
            "gross_income": round(gross_income),
            "standard_deduction": round(std_new),
            "net_taxable_income": round(new_taxable),
            "slab_breakdown": new_slab_breakdown,
            "tax_before_cess": round(new_tax_before_cess),
            "health_education_cess": round(new_cess),
            "total_tax": round(new_total),
        },
        "comparison": {
            "optimal_regime": optimal_regime,
            "savings_with_optimal": round(savings),
            "old_regime_tax": round(old_total),
            "new_regime_tax": round(new_total),
        },
        "missed_deductions": missed_deductions,
        "instrument_recommendations": instrument_recommendations,
        "audit_trail": audit_trail,
    }
