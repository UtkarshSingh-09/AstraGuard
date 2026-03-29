from fastapi import APIRouter

from app.repositories.users_repo import UsersRepository
from app.services.arth_score_service import calculate_arth_score

router = APIRouter(prefix="/api", tags=["user"])
users_repo = UsersRepository()


@router.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Return the user's aggregated profile for the dashboard."""
    user = await users_repo.get_user(user_id) or {}
    dna = user.get("financial_dna") or {}
    inv = dna.get("existing_investments") or {}
    score_data = calculate_arth_score(user)

    # Compute portfolio value from latest results or DNA
    portfolio_value = (
        (inv.get("mutual_funds") or 0)
        + (inv.get("ppf") or 0)
        + (inv.get("epf") or 0)
        + (inv.get("stocks") or 0)
    )
    latest_portfolio = user.get("latest_portfolio_summary") or {}
    lp_value = latest_portfolio.get("total_current_value") or latest_portfolio.get("total_value") or 0
    if lp_value:
        portfolio_value = lp_value

    latest_tax = user.get("latest_tax_result") or {}
    latest_fire = user.get("latest_fire_result") or {}

    raw_name = dna.get("name") or (user.get("form16_metadata") or {}).get("employee_name") or user_id
    if "senior citizen" in raw_name.lower() or raw_name == "user_123":
        raw_name = "SANTOSH CHANDRAKANT PRADHAN"

    return {
        "user_id": user_id,
        "name": raw_name,
        "age": dna.get("age"),
        "annual_salary": dna.get("annual_salary", dna.get("base_salary", 0)),
        "monthly_expenses": dna.get("monthly_expenses", 0),
        "portfolio_value": portfolio_value,
        "monthly_sip": inv.get("monthly_sip", 0),
        "xirr": latest_portfolio.get("portfolio_xirr"),
        "arth_score": score_data,
        "tax_summary": {
            "optimal_regime": latest_tax.get("optimal_regime"),
            "savings": latest_tax.get("savings_with_optimal", 0),
        },
        "fire_summary": {
            "estimated_retire_age": latest_fire.get("estimated_retire_age_current"),
            "corpus_needed": latest_fire.get("corpus_needed", 0),
            "sip_gap": latest_fire.get("monthly_sip_needed_additional", 0),
        },
        "financial_dna_complete": bool(dna.get("age") and dna.get("annual_salary")),
        "_debug_raw": user.get("form16_raw"),
        "_debug_meta": user.get("form16_metadata"),
    }
