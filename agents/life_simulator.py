"""
Agent 9: Life Simulator Agent 🔥
The "Surprise Scenario" killer — handles complex "what-if" queries by
chaining multiple agents for compound impact analysis.
Uses llama3-8b for event detection, llama-3.3-70b for narration.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_fast, safe_invoke_quality
from integrations.life_events import detect_life_event
from prompts.simulator_prompts import (
    LIFE_SIMULATION_PROMPT,
    EVENT_ADJUSTMENTS,
)

logger = logging.getLogger("astraguard.agents.life_simulator")


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


def _adjust_dna_for_event(
    event_type: str,
    financial_dna: dict,
    extracted_amount: float | None = None,
) -> dict:
    """
    Create an adjusted copy of financial_dna based on the life event.
    This adjusted DNA is passed to math engines for "what-if" recalculation.
    """
    adjusted = json.loads(json.dumps(financial_dna))  # deep copy

    if event_type == "income_increase" and extracted_amount:
        current_salary = adjusted.get("annual_salary", 0) or 0
        adjusted["annual_salary"] = current_salary + extracted_amount

    elif event_type == "income_loss":
        if extracted_amount:
            adjusted["annual_salary"] = extracted_amount
        else:
            adjusted["annual_salary"] = 0

    elif event_type == "marriage":
        # Add spouse financial considerations
        adjusted["dependents"] = (adjusted.get("dependents", 0) or 0) + 1
        adjusted["monthly_expenses"] = (adjusted.get("monthly_expenses", 0) or 0) * 1.4

    elif event_type == "new_child":
        adjusted["dependents"] = (adjusted.get("dependents", 0) or 0) + 1
        adjusted["monthly_expenses"] = (adjusted.get("monthly_expenses", 0) or 0) * 1.2
        # Add education goal
        goals = adjusted.get("goals", [])
        goals.append({
            "name": "Child Education Fund",
            "target_amount": 5000000,  # ₹50L for higher education
            "target_year": 2044,  # ~18 years
            "emotional_label": "Future Builder 🎓",
        })
        adjusted["goals"] = goals

    elif event_type == "home_purchase":
        adjusted["has_home_loan"] = True
        if extracted_amount:
            adjusted["home_loan_interest_annual"] = extracted_amount * 0.085  # ~8.5% rate estimate
            adjusted["monthly_expenses"] = (
                (adjusted.get("monthly_expenses", 0) or 0)
                + (extracted_amount * 0.085 / 12)
            )

    elif event_type == "inheritance" and extracted_amount:
        inv = adjusted.get("existing_investments", {})
        inv["mutual_funds"] = (inv.get("mutual_funds", 0) or 0) + extracted_amount
        adjusted["existing_investments"] = inv

    return adjusted


async def run_life_simulator(
    user_id: str,
    event_description: str,
    financial_dna: dict,
    behavioral_dna: dict,
    current_fire_result: dict | None = None,
    current_tax_result: dict | None = None,
) -> dict:
    """
    Simulate the financial impact of a life event.

    This agent:
    1. Detects the event type
    2. Adjusts financial DNA based on the event
    3. Returns the adjusted DNA for Ankit's math engines to recalculate
    4. Generates a narrated impact report

    Args:
        user_id: User identifier
        event_description: Free-text description of the event
        financial_dna: Current financial profile
        behavioral_dna: Current behavioral profile
        current_fire_result: Latest FIRE calculation (for comparison)
        current_tax_result: Latest tax calculation (for comparison)

    Returns:
        {
            "event_type": str,
            "adjusted_financial_dna": dict,  # for recalculation by math engines
            "domains_to_recalculate": list[str],  # ["fire", "tax", "portfolio"]
            "narration": str,
            "recommended_actions": list[str],
            "urgency": str,
        }
    """
    # Step 1: Detect event type
    event = await detect_life_event(event_description)
    event_type = event.get("event_type", "none")
    extracted_amount = event.get("extracted_amount")
    extracted_timeline = event.get("extracted_timeline")

    if event_type == "none":
        return {
            "event_type": "none",
            "adjusted_financial_dna": financial_dna,
            "domains_to_recalculate": [],
            "narration": "Yeh koi specific life event nahi lag raha. Kuch aur detail de?",
            "recommended_actions": [],
            "urgency": "LOW",
        }

    # Step 2: Get event-specific config
    event_config = EVENT_ADJUSTMENTS.get(event_type, {})
    domains_to_recalc = event_config.get("recalc", ["fire"])

    # Step 3: Adjust DNA
    adjusted_dna = _adjust_dna_for_event(event_type, financial_dna, extracted_amount)

    # Step 4: Generate narration
    # NOTE: In the full integrated flow, Ankit's backend would:
    #   1. Receive the adjusted_dna
    #   2. Run math engines with it
    #   3. Pass the new results back to this agent for narration
    # For now, we generate a preliminary narration based on the adjustment

    impact_summary = {
        "event_type": event_type,
        "original_salary": financial_dna.get("annual_salary"),
        "adjusted_salary": adjusted_dna.get("annual_salary"),
        "original_expenses": financial_dna.get("monthly_expenses"),
        "adjusted_expenses": adjusted_dna.get("monthly_expenses"),
        "domains_affected": domains_to_recalc,
    }

    prompt = LIFE_SIMULATION_PROMPT.format(
        event_type=event_type,
        event_description=event_description,
        amount=extracted_amount or "Not specified",
        timeline=extracted_timeline or "Not specified",
        age=financial_dna.get("age", "N/A"),
        salary=financial_dna.get("annual_salary", "N/A"),
        retire_age=current_fire_result.get("summary", {}).get("estimated_retire_age_with_plan", "N/A") if current_fire_result else "N/A",
        current_sip=current_fire_result.get("summary", {}).get("monthly_sip_total_needed", "N/A") if current_fire_result else "N/A",
        emergency_fund=financial_dna.get("existing_investments", {}).get("fd", 0),
        impact_results=json.dumps(impact_summary, indent=2, default=str),
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    narration_data = _parse_json_response(raw_response)

    return {
        "event_type": event_type,
        "adjusted_financial_dna": adjusted_dna,
        "domains_to_recalculate": domains_to_recalc,
        "narration": narration_data.get("impact_summary", "Simulation complete — see detailed impacts below."),
        "cross_domain_effects": narration_data.get("cross_domain_effects", {}),
        "recommended_actions": narration_data.get("recommended_actions", []),
        "urgency": narration_data.get("overall_urgency", "MEDIUM"),
    }
