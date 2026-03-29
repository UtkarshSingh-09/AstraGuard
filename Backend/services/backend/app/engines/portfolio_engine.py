from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from math import isfinite
from typing import Any


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _xirr(cashflows: list[tuple[date, float]]) -> float:
    if not cashflows:
        return 0.0
    cashflows = sorted(cashflows, key=lambda x: x[0])
    if not any(v < 0 for _, v in cashflows) or not any(v > 0 for _, v in cashflows):
        return 0.0
    t0 = cashflows[0][0]

    def f(rate: float) -> float:
        total = 0.0
        for d, amt in cashflows:
            tau = (d - t0).days / 365.0
            total += amt / ((1 + rate) ** tau)
        return total

    def df(rate: float) -> float:
        total = 0.0
        for d, amt in cashflows:
            tau = (d - t0).days / 365.0
            total += (-tau * amt) / ((1 + rate) ** (tau + 1))
        return total

    rate = 0.12
    for _ in range(100):
        fv = f(rate)
        derv = df(rate)
        if abs(fv) < 1e-8:
            break
        if derv == 0:
            break
        next_rate = rate - (fv / derv)
        if not isfinite(next_rate) or next_rate <= -0.99:
            break
        if abs(next_rate - rate) < 1e-10:
            rate = next_rate
            break
        rate = next_rate
    return round(rate * 100, 2)


def _infer_cashflows(fund: dict[str, Any], valuation_date: date) -> list[tuple[date, float]]:
    flows: list[tuple[date, float]] = []
    for txn in fund.get("transactions", []):
        d = _parse_date(txn["date"])
        amt = float(txn["amount"])
        # Convention: investment outflow must be negative for XIRR equation.
        if txn.get("type", "BUY").upper() in {"BUY", "SIP", "STP_IN"} and amt > 0:
            amt = -amt
        flows.append((d, amt))
    flows.append((valuation_date, float(fund.get("current_value", 0))))
    return flows


def _overlap_analysis(funds: list[dict[str, Any]]) -> dict[str, Any]:
    significant = []
    fund_holdings = []
    for f in funds:
        weight_map = {}
        for h in f.get("holdings", []):
            stock = str(h.get("stock", "")).strip()
            if stock:
                weight_map[stock] = float(h.get("weight", 0))
        fund_holdings.append(weight_map)
    
    n = len(funds)
    max_overlap = 0.0
    
    for i in range(n):
        for j in range(i + 1, n):
            h1 = fund_holdings[i]
            h2 = fund_holdings[j]
            common_stocks = set(h1.keys()).intersection(set(h2.keys()))
            overlap_val = sum(min(h1[s], h2[s]) for s in common_stocks)
            
            if overlap_val > 0:
                if overlap_val > max_overlap:
                    max_overlap = overlap_val
                
                significant.append({
                    "funds": [str(funds[i].get("name", f"Fund {i}")), str(funds[j].get("name", f"Fund {j}"))],
                    "overlap_pct": round(overlap_val, 2),
                    "common_stocks_count": len(common_stocks)
                })
    
    significant = sorted(significant, key=lambda x: x["overlap_pct"], reverse=True)
    overlap_score = round(max_overlap)
    
    if overlap_score >= 60:
        severity = "HIGH"
    elif overlap_score >= 30:
        severity = "MEDIUM"
    else:
        severity = "LOW"
        
    return {
        "significant_overlaps": significant,
        "overlap_severity": severity,
        "overlap_score": overlap_score,
    }


def _rebalancing_plan(funds: list[dict[str, Any]], overlap: dict[str, Any], as_of: date) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    high_overlap = overlap.get("overlap_severity") == "HIGH"
    for fund in funds:
        fund_name = str(fund.get("name", "Unknown Fund"))
        invested = float(fund.get("invested", 0))
        current_value = float(fund.get("current_value", 0))
        gain = current_value - invested
        first_txn = None
        txns = fund.get("transactions", [])
        if txns:
            first_txn = min(_parse_date(t["date"]) for t in txns)
        days_held = (as_of - first_txn).days if first_txn else 0

        if high_overlap and gain > 0 and days_held < 365:
            stcg = round(gain * 0.20)
            wait_days = 365 - days_held
            plan.append(
                {
                    "action": "WAIT_AND_REDIRECT",
                    "fund_name": fund_name,
                    "reason": f"{wait_days} days to LTCG eligibility",
                    "days_to_ltcg": wait_days,
                    "stcg_if_exit_now": stcg,
                    "stcg_avoided_by_waiting": stcg,
                    "immediate_action": "Redirect new SIP to lower-overlap alternate fund",
                    "after_ltcg_action": "Trim exposure after LTCG eligibility window",
                }
            )

        plan_type = str(fund.get("plan_type", "")).upper()
        expense_ratio = float(fund.get("expense_ratio", 0))
        direct_ratio = float(fund.get("direct_plan_expense_ratio", expense_ratio))
        if plan_type == "REGULAR" and expense_ratio > direct_ratio:
            annual_saving = round((expense_ratio - direct_ratio) * current_value / 100)
            plan.append(
                {
                    "action": "SWITCH_TO_DIRECT",
                    "fund_name": fund_name,
                    "reason": f"Regular plan expense drag of approximately ₹{annual_saving:,}/year",
                    "annual_saving": annual_saving,
                    "how_to": "Switch to direct plan via AMC portal after tax/load check",
                }
            )
    return plan


def analyze_portfolio(inputs: dict[str, Any]) -> dict[str, Any]:
    funds = inputs.get("funds", [])
    if not funds:
        raise ValueError("At least one fund is required")

    as_of = _parse_date(inputs.get("as_of_date", date.today().isoformat()))
    benchmark_xirr = float(inputs.get("benchmark_xirr_nifty50", 12.8))

    portfolio_cashflows: list[tuple[date, float]] = []
    funds_out: list[dict[str, Any]] = []

    total_invested = 0.0
    total_current_value = 0.0
    for fund in funds:
        invested = float(fund.get("invested", 0))
        current_value = float(fund.get("current_value", 0))
        total_invested += invested
        total_current_value += current_value

        cfs = _infer_cashflows(fund, as_of)
        fxirr = _xirr(cfs)
        portfolio_cashflows.extend(cfs[:-1])  # keep one portfolio terminal later

        funds_out.append(
            {
                "name": fund.get("name"),
                "isin": fund.get("isin"),
                "invested": round(invested),
                "current_value": round(current_value),
                "xirr": fxirr,
                "expense_ratio": float(fund.get("expense_ratio", 0)),
                "plan_type": fund.get("plan_type", "UNKNOWN"),
                "direct_plan_expense_ratio": float(fund.get("direct_plan_expense_ratio", 0)),
                "top_holdings": fund.get("top_holdings", []),
            }
        )

    portfolio_cashflows.append((as_of, total_current_value))
    portfolio_xirr = _xirr(portfolio_cashflows)
    overlap = _overlap_analysis(funds)

    total_expense_drag = 0.0
    regular_to_direct_saving = 0.0
    for idx, fund in enumerate(funds):
        invested = float(fund.get("invested", 0))
        current = float(fund.get("current_value", 0))
        exp = float(fund.get("expense_ratio", 0))
        direct = float(fund.get("direct_plan_expense_ratio", exp))
        
        txns = fund.get("transactions", [])
        if txns:
            first_txn = min(_parse_date(t["date"]) for t in txns)
            days_held = (as_of - first_txn).days
        else:
            days_held = 0
        H = days_held / 365.0
        
        g = funds_out[idx]["xirr"] / 100.0
        e = exp / 100.0
        
        if H > 0 and invested > 0:
            drag = (invested * ((1 + g) ** H)) - (invested * ((1 + g - e) ** H))
            total_expense_drag += max(0.0, drag)
        else:
            total_expense_drag += e * current

        if str(fund.get("plan_type", "")).upper() == "REGULAR" and exp > direct:
            direct_e = direct / 100.0
            if H > 0 and invested > 0:
                saving = (invested * ((1 + g - direct_e) ** H)) - (invested * ((1 + g - e) ** H))
            else:
                saving = ((exp - direct) / 100) * current
            regular_to_direct_saving += max(0.0, saving)

    rebalance = _rebalancing_plan(funds, overlap, as_of)

    audit_trail = [
        {
            "step": "portfolio_xirr",
            "formula": "sum(CF_i / (1+r)^tau_i)=0 solved for r",
            "result": portfolio_xirr,
        },
        {
            "step": "overlap_score",
            "formula": "sum(min(weight_A_i, weight_B_i))",
            "result": overlap["overlap_score"],
        },
        {
            "step": "expense_drag",
            "formula": "V0*(1+g)^H - V0*(1+g-e)^H",
            "result": round(total_expense_drag),
        },
    ]

    return {
        "status": "complete",
        "portfolio_summary": {
            "total_invested": round(total_invested),
            "current_value": round(total_current_value),
            "absolute_return": round(total_current_value - total_invested),
            "absolute_return_pct": round(((total_current_value - total_invested) / total_invested) * 100, 2)
            if total_invested > 0
            else 0.0,
            "portfolio_xirr": portfolio_xirr,
            "benchmark_xirr_nifty50": benchmark_xirr,
            "outperformance": round(portfolio_xirr - benchmark_xirr, 2),
        },
        "funds": funds_out,
        "overlap_analysis": overlap,
        "expense_analysis": {
            "total_annual_expense_drag": round(total_expense_drag),
            "regular_to_direct_saving": round(regular_to_direct_saving),
            "years_to_switch_benefit_visible": 2,
        },
        "rebalancing_plan": rebalance,
        "audit_trail": audit_trail,
    }
