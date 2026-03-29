"""
Agent 10: Audit Narrator Agent 🔥
Converts raw JSON audit trails into human-readable educational walkthroughs.
Satisfies the "traceable logic" requirement.
Uses llama-3.3-70b-versatile.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_quality
from prompts.audit_prompts import AUDIT_NARRATION_PROMPT, AUDIT_CONTEXT

logger = logging.getLogger("astraguard.agents.audit_narrator")


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


def _format_indian_number(num: float | int) -> str:
    """Format number in Indian style (₹1,23,45,678)."""
    if num < 0:
        return "-₹" + _format_indian_number(abs(num))[1:]

    num = int(num)
    s = str(num)
    if len(s) <= 3:
        return f"₹{s}"

    # Last 3 digits
    result = s[-3:]
    s = s[:-3]

    # Groups of 2
    while s:
        result = s[-2:] + "," + result
        s = s[:-2]

    return f"₹{result}"


def _build_template_narration(audit_trail: list[dict], calc_type: str) -> dict:
    """Fallback template when LLM is unavailable."""
    narrated_steps = []
    for i, step in enumerate(audit_trail, 1):
        formula = step.get("formula", "N/A")
        result = step.get("result", "N/A")
        step_name = step.get("step", "Calculation Step")

        # Format result as Indian number if it's numeric
        if isinstance(result, (int, float)):
            result_formatted = _format_indian_number(result)
        else:
            result_formatted = str(result)

        narrated_steps.append({
            "step_number": i,
            "title": step_name.replace("_", " ").title(),
            "explanation": f"Formula: {formula} = {result_formatted}",
            "formula_visual": f"{formula} = {result_formatted}",
            "why_it_matters": "Yeh step overall calculation ke liye zaroori hai.",
        })

    return {
        "calculation_type": calc_type,
        "total_steps": len(narrated_steps),
        "narrated_steps": narrated_steps,
        "summary": f"Total {len(narrated_steps)} steps mein calculation complete hua.",
    }


async def run_audit_narrator(
    audit_trail: list[dict],
    calculation_type: str = "fire",
) -> dict:
    """
    Convert raw audit trail into human-readable educational walkthrough.

    Args:
        audit_trail: List of {step, formula, inputs, output/result, timestamp}
        calculation_type: "fire", "tax", or "portfolio"

    Returns:
        {
            "calculation_type": str,
            "total_steps": int,
            "narrated_steps": [
                {
                    "step_number": int,
                    "title": str,
                    "explanation": str,  # Hinglish
                    "formula_visual": str,  # formatted math
                    "why_it_matters": str,
                }
            ],
            "summary": str,
        }
    """
    if not audit_trail:
        return {
            "calculation_type": calculation_type,
            "total_steps": 0,
            "narrated_steps": [],
            "summary": "No audit trail available.",
        }

    context = AUDIT_CONTEXT.get(calculation_type, "")

    prompt = AUDIT_NARRATION_PROMPT.format(
        calculation_type=calculation_type,
        audit_trail=json.dumps(audit_trail, indent=2, default=str),
    )
    if context:
        prompt = f"CONTEXT: {context}\n\n{prompt}"

    raw_response = await safe_invoke_quality(prompt, fallback="")
    result = _parse_json_response(raw_response)

    if not result or "narrated_steps" not in result:
        logger.warning("Audit narration LLM failed — using template")
        result = _build_template_narration(audit_trail, calculation_type)

    return result
