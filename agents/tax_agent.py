"""
Agent 4: Tax Agent
Narrates deterministic tax calculation results in simple Hinglish.
NEVER recalculates — only explains pre-computed results.
Uses llama-3.3-70b-versatile.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_quality
from prompts.narration_prompts import TAX_NARRATION_PROMPT

logger = logging.getLogger("astraguard.agents.tax")


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
    """Fallback template when LLM is unavailable."""
    comparison = calc_result.get("comparison", {})
    optimal = comparison.get("optimal_regime", "N/A")
    savings = comparison.get("savings_with_optimal", 0)
    old_tax = calc_result.get("old_regime", {}).get("total_tax", 0)
    new_tax = calc_result.get("new_regime", {}).get("total_tax", 0)

    missed = calc_result.get("missed_deductions", [])
    missed_text = []
    for d in missed[:3]:
        missed_text.append(
            f"{d.get('section', 'N/A')}: ₹{d.get('potential_tax_saving', 0):,.0f} bachega — {d.get('action', 'Check details')}"
        )

    return {
        "key_insight": (
            f"Tere case mein {optimal} regime better hai. "
            f"Old: ₹{old_tax:,.0f}, New: ₹{new_tax:,.0f} — ₹{savings:,.0f} bachta hai. "
            + (f"Lekin {len(missed)} deductions miss ho rahe hain!" if missed else "")
        ),
        "missed_deduction_actions": missed_text,
        "regime_helper": f"{'New' if optimal == 'OLD' else 'Old'} regime tab better hota jab deductions kam hoti hain.",
        "one_line_summary": f"{optimal} regime se ₹{savings:,.0f} bachega.",
    }


async def run_tax_agent(
    calculation_result: dict,
    financial_dna: dict | None = None,
) -> dict:
    """
    Generate narration for a tax calculation result.

    Args:
        calculation_result: Raw output from tax_engine.py
        financial_dna: Optional user profile for context

    Returns:
        {
            "narration": dict,
            "compliance_flags": list[str],
        }
    """
    old_regime = calculation_result.get("old_regime", {})
    new_regime = calculation_result.get("new_regime", {})
    comparison = calculation_result.get("comparison", {})
    missed = calculation_result.get("missed_deductions", [])

    prompt = TAX_NARRATION_PROMPT.format(
        calculation_result=json.dumps(calculation_result, indent=2, default=str),
        old_tax=old_regime.get("total_tax", 0),
        new_tax=new_regime.get("total_tax", 0),
        optimal_regime=comparison.get("optimal_regime", "N/A"),
        savings=comparison.get("savings_with_optimal", 0),
        missed_deductions=json.dumps(missed, indent=2, default=str),
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    narration = _parse_json_response(raw_response)

    if not narration:
        logger.warning("Tax narration LLM failed — using template")
        narration = _build_template_narration(calculation_result)

    return {
        "narration": narration,
        "compliance_flags": [],
    }
