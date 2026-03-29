"""
Agent 5: Portfolio Agent
Generates fund-specific, rupee-specific, STCG-aware rebalancing narration.
NEVER does math — only narrates pre-computed portfolio analysis.
Uses llama-3.3-70b-versatile.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_quality
from prompts.narration_prompts import PORTFOLIO_NARRATION_PROMPT

logger = logging.getLogger("astraguard.agents.portfolio")


def _parse_json_response(raw: str) -> dict:
    """Parse LLM response to JSON."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    return {}


def _build_template_narration(calc_result: dict) -> dict:
    """Fallback template when LLM fails."""
    summary = calc_result.get("portfolio_summary", {})
    overlap = calc_result.get("overlap_analysis", {})
    expense = calc_result.get("expense_analysis", {})
    rebalancing = calc_result.get("rebalancing_plan", [])

    xirr = summary.get("portfolio_xirr", 0)
    overlap_severity = overlap.get("overlap_severity", "UNKNOWN")
    expense_drag = expense.get("total_annual_expense_drag", 0)

    actions = []
    for rb in rebalancing[:3]:
        actions.append({
            "fund": rb.get("fund_name", "Unknown Fund"),
            "action": rb.get("action", "REVIEW"),
            "amount": "See details",
            "timeline": rb.get("after_ltcg_action", "Check rebalancing plan"),
            "reason": rb.get("reason", "Overlap or expense drag"),
            "alternative": rb.get("immediate_action", "Continue SIP as-is"),
        })

    return {
        "portfolio_health": (
            f"Portfolio XIRR {xirr}% hai. "
            f"Overlap severity {overlap_severity} hai — diversification improve karna chahiye."
        ),
        "rebalancing_actions": actions,
        "expense_impact": f"Annual expense drag ₹{expense_drag:,.0f} hai. Direct plans mein switch se bachega.",
        "one_line_summary": f"XIRR {xirr}%, overlap {overlap_severity}, ₹{expense_drag:,.0f}/year expense drag.",
    }


async def run_portfolio_agent(
    calculation_result: dict,
    financial_dna: dict | None = None,
) -> dict:
    """
    Generate narration for portfolio X-Ray result.

    Args:
        calculation_result: Raw output from portfolio_engine.py
        financial_dna: Optional user profile for context

    Returns:
        {
            "narration": dict,
            "compliance_flags": list[str],
        }
    """
    summary = calculation_result.get("portfolio_summary", {})
    overlap = calculation_result.get("overlap_analysis", {})
    expense = calculation_result.get("expense_analysis", {})
    funds = calculation_result.get("funds", [])

    regular_count = sum(1 for f in funds if f.get("plan_type") == "REGULAR")

    prompt = PORTFOLIO_NARRATION_PROMPT.format(
        calculation_result=json.dumps(calculation_result, indent=2, default=str),
        xirr=summary.get("portfolio_xirr", 0),
        overlap_severity=overlap.get("overlap_severity", "UNKNOWN"),
        expense_drag=expense.get("total_annual_expense_drag", 0),
        regular_count=regular_count,
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    narration = _parse_json_response(raw_response)

    if not narration:
        logger.warning("Portfolio narration LLM failed — using template")
        narration = _build_template_narration(calculation_result)

    return {
        "narration": narration,
        "compliance_flags": [],
    }
