"""
Agent 2: DNA Extraction Agent
Extracts Financial DNA + Behavioral DNA from conversational chat history.
Uses llama3-8b for fast, structured JSON extraction.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from integrations.groq_client import safe_invoke_fast
from prompts.dna_prompts import (
    DNA_SYSTEM_PROMPT,
    DNA_EXTRACTION_PROMPT,
    QUESTION_FLOW,
    BEHAVIORAL_QUESTIONS,
)
from schemas.financial_dna import FinancialDNA, BehavioralDNA

logger = logging.getLogger("astraguard.agents.dna")

# ─── Schema Template for LLM Prompt ──────────────────────────────────────────

DNA_JSON_SCHEMA = """{
    "age": "int|null",
    "annual_salary": "float|null",
    "monthly_expenses": "float|null",
    "existing_investments": {"mutual_funds": 0, "ppf": 0, "fd": 0, "stocks": 0, "epf": 0, "nps": 0},
    "goals": [{"name": "str", "target_amount": "float|null", "target_year": "int|null", "emotional_label": "str|null"}],
    "insurance_cover": "float|null",
    "risk_profile": "conservative|moderate|aggressive|null",
    "city_type": "metro|non-metro|null",
    "rent_paid_monthly": "float|null",
    "hra_received": "float|null",
    "has_home_loan": "bool",
    "home_loan_interest_annual": "float|null"
}"""

# ─── Field tracking for completion ────────────────────────────────────────────

REQUIRED_FIELDS = ["age", "annual_salary", "monthly_expenses"]
IMPORTANT_FIELDS = [
    "goals", "insurance_cover", "risk_profile", "city_type",
    "existing_investments",
]
BEHAVIORAL_FIELDS = ["panic_threshold", "behavior_type", "last_panic_event"]

TOTAL_TRACKABLE_FIELDS = len(REQUIRED_FIELDS) + len(IMPORTANT_FIELDS) + len(BEHAVIORAL_FIELDS)


def _calculate_completion(extracted: dict) -> int:
    """Calculate completion percentage based on filled fields."""
    filled = 0
    total = TOTAL_TRACKABLE_FIELDS

    fin = extracted.get("financial_dna", {})
    beh = extracted.get("behavioral_dna", {})

    for field in REQUIRED_FIELDS:
        if fin.get(field) is not None:
            filled += 1

    for field in IMPORTANT_FIELDS:
        val = fin.get(field)
        if field == "goals" and isinstance(val, list) and len(val) > 0:
            filled += 1
        elif field == "existing_investments" and isinstance(val, dict):
            if any(v > 0 for v in val.values() if isinstance(v, (int, float))):
                filled += 1
        elif val is not None:
            filled += 1

    for field in BEHAVIORAL_FIELDS:
        if beh.get(field) is not None:
            filled += 1

    return int((filled / total) * 100)


def _is_extraction_complete(extracted: dict) -> bool:
    """Check if minimum required fields are filled."""
    fin = extracted.get("financial_dna", {})
    # Minimum: age + salary + expenses + at least 1 goal
    has_required = all(fin.get(f) is not None for f in REQUIRED_FIELDS)
    has_goals = isinstance(fin.get("goals"), list) and len(fin.get("goals", [])) > 0
    return has_required and has_goals


def _get_next_question(extracted: dict, turn_count: int) -> str:
    """Determine the next question based on what's missing."""
    fin = extracted.get("financial_dna", {})
    beh = extracted.get("behavioral_dna", {})

    # Check required fields first
    if fin.get("age") is None:
        return QUESTION_FLOW[0]
    if fin.get("annual_salary") is None:
        return QUESTION_FLOW[1]
    if fin.get("monthly_expenses") is None:
        return QUESTION_FLOW[2]
    if fin.get("city_type") is None:
        return QUESTION_FLOW[3]

    # Then investments
    inv = fin.get("existing_investments", {})
    if not any(v > 0 for v in inv.values() if isinstance(v, (int, float))):
        return QUESTION_FLOW[4]

    # Goals
    goals = fin.get("goals", [])
    if not goals:
        return QUESTION_FLOW[6]

    # Insurance
    if fin.get("insurance_cover") is None:
        return QUESTION_FLOW[8]

    # Behavioral DNA (the differentiator)
    if beh.get("last_panic_event") is None:
        return BEHAVIORAL_QUESTIONS[0]["question"]
    if beh.get("panic_threshold") is None:
        return QUESTION_FLOW[11]

    # HRA/rent
    if fin.get("rent_paid_monthly") is None and fin.get("has_home_loan") is None:
        return QUESTION_FLOW[12]

    # Fallback
    return "Aur kuch batana hai? Ya main tera plan banana start karun? 🚀"


def _parse_llm_response(raw: str) -> dict:
    """Parse LLM response, handling various JSON formatting issues."""
    # Try to extract JSON from markdown code blocks
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass

    logger.warning(f"Failed to parse LLM response as JSON: {raw[:200]}")
    return {}


# ─── Main Agent Function ─────────────────────────────────────────────────────

async def run_dna_agent(
    session_id: str,
    conversation_history: list[dict],
) -> dict:
    """
    Extract Financial DNA + Behavioral DNA from conversation.

    Args:
        session_id: Unique session identifier
        conversation_history: List of {role, content} message dicts

    Returns:
        {
            "status": "gathering" | "complete",
            "next_question": str | None,
            "extracted_so_far": dict,  # FinancialDNA fields
            "behavioral_dna": dict | None,
            "completion_percentage": int,
        }
    """
    turn_count = len([m for m in conversation_history if m.get("role") == "user"])

    # Format conversation for LLM
    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation_history
    )

    # Build LLM prompt
    system = DNA_SYSTEM_PROMPT.format(schema=DNA_JSON_SCHEMA)
    prompt = f"{system}\n\n{DNA_EXTRACTION_PROMPT.format(conversation_history=conv_text)}"

    # Call fast LLM
    raw_response = await safe_invoke_fast(prompt, fallback="{}")
    extracted = _parse_llm_response(raw_response)

    # Calculate completion
    completion = _calculate_completion(extracted)
    is_complete = _is_extraction_complete(extracted)

    # Determine next question (use LLM's suggestion or our logic)
    if is_complete:
        next_q = None
        status = "complete"
    else:
        llm_next_q = extracted.get("next_question")
        fallback_q = _get_next_question(extracted, turn_count)
        next_q = llm_next_q if llm_next_q else fallback_q
        status = "gathering"

    return {
        "status": status,
        "next_question": next_q,
        "extracted_so_far": extracted.get("financial_dna", {}),
        "behavioral_dna": extracted.get("behavioral_dna"),
        "completion_percentage": completion,
    }
