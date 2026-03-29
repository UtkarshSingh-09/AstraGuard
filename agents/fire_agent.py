"""
Agent 3: FIRE Agent
Adds LLM narration on top of deterministic FIRE calculations.
NEVER does math — only narrates pre-computed results.
Uses llama-3.3-70b-versatile for quality narration.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_quality
from prompts.narration_prompts import FIRE_NARRATION_PROMPT, FIRE_CONSEQUENCE_STOP_SIP_PROMPT

logger = logging.getLogger("astraguard.agents.fire")


def _validate_narration_numbers(narration: str, calc_result: dict) -> bool:
    """
    Cross-check that key numbers in the LLM narration match the calculation.
    If the LLM hallucinates different numbers, we reject the narration.
    """
    summary = calc_result.get("summary", {})
    key_numbers = [
        str(int(summary.get("corpus_needed", 0))),
        str(int(summary.get("monthly_sip_total_needed", 0))),
    ]
    # Check if at least one key number appears in narration
    for num in key_numbers:
        if num != "0" and num in narration.replace(",", "").replace("₹", ""):
            return True
    # If no key numbers found, the narration might be hallucinating
    return False


def _build_template_narration(calc_result: dict, financial_dna: dict) -> dict:
    """Fallback template narration when LLM is unavailable or hallucinates."""
    summary = calc_result.get("summary", {})
    age = financial_dna.get("age", "N/A")
    retire_age = summary.get("estimated_retire_age_with_plan", "N/A")
    corpus = summary.get("corpus_needed", 0)
    sip = summary.get("monthly_sip_total_needed", 0)
    gap = summary.get("corpus_gap", 0)

    corpus_cr = corpus / 10000000 if corpus else 0
    sip_k = sip / 1000 if sip else 0

    return {
        "summary_narration": (
            f"Tujhe retire hone ke liye ₹{corpus_cr:.1f} Cr ka corpus chahiye. "
            f"₹{sip_k:.0f}K/month SIP se tu {retire_age} saal ki umar mein retire kar sakta hai. "
            f"Aaj se shuru kar — compounding tera sabse bada dost hai."
        ),
        "consequence_narrative": "Consequence timeline available in the dashboard.",
        "glidepath_explanation": "Equity allocation will gradually shift to debt as you approach retirement for capital preservation.",
        "action_today": f"₹{sip_k:.0f}K/month SIP set up kar — aaj hi.",
    }


def _parse_json_response(raw: str) -> dict:
    """Parse LLM response to JSON, handling formatting issues."""
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


async def run_fire_agent(
    calculation_result: dict,
    financial_dna: dict,
) -> dict:
    """
    Generate narration for a FIRE calculation result.

    Args:
        calculation_result: Raw output from fire_engine.py (Ankit's code)
        financial_dna: User's financial profile

    Returns:
        {
            "narration": dict,            # summary, consequence, glidepath, action
            "compliance_flags": list[str], # populated later by RegulatorGuard
        }
    """
    summary = calculation_result.get("summary", {})

    prompt = FIRE_NARRATION_PROMPT.format(
        calculation_result=json.dumps(calculation_result, indent=2, default=str),
        age=financial_dna.get("age", "N/A"),
        salary=financial_dna.get("annual_salary", "N/A"),
        retire_age=summary.get("estimated_retire_age_with_plan", "N/A"),
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    narration = _parse_json_response(raw_response)

    # Validate — if LLM hallucinated numbers, use template
    if not narration or not _validate_narration_numbers(
        narration.get("summary_narration", ""), calculation_result
    ):
        logger.warning("FIRE narration validation failed — using template fallback")
        narration = _build_template_narration(calculation_result, financial_dna)

    return {
        "narration": narration,
        "compliance_flags": [],  # RegulatorGuard fills this later
    }


async def generate_stop_sip_consequence(
    planned_retire_age: float,
    stop_retire_age: float,
    additional_saving: float,
    goal_name: str,
) -> str:
    """Generate a consequence message for stopping SIP."""
    delta_years = stop_retire_age - planned_retire_age

    prompt = FIRE_CONSEQUENCE_STOP_SIP_PROMPT.format(
        planned_retire_age=planned_retire_age,
        stop_retire_age=stop_retire_age,
        delta_years=delta_years,
        additional_saving=additional_saving,
        goal_name=goal_name,
    )

    return await safe_invoke_quality(
        prompt,
        fallback=(
            f"SIP rokne se retirement {delta_years:.1f} saal delay hogi. "
            f"₹{additional_saving:,.0f} extra chahiye hoga. Continue karo bhai. 💪"
        ),
    )
