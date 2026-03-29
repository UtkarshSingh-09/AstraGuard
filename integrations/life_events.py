"""
Life Event Detection — regex + LLM intent classification.
Used by LifeSimulatorAgent to detect financial life events from chat.
"""

from __future__ import annotations

import re
import json
import logging

from integrations.groq_client import safe_invoke_fast
from prompts.simulator_prompts import LIFE_EVENT_CLASSIFY_PROMPT

logger = logging.getLogger("astraguard.integrations.life_events")

# ─── Regex-based fast detection ───────────────────────────────────────────────

TRIGGER_PATTERNS = {
    r"bonus|increment|raise|promotion|hike|appraisal": "income_increase",
    r"shaadi|wedding|marriage|engaged|engagement": "marriage",
    r"baby|pregnant|bachha|child|kid|adoption": "new_child",
    r"ghar|flat|home|property|house|real\s*estate|home\s*loan": "home_purchase",
    r"resign|job\s*change|layoff|fired|quit|unemploy|lost\s*job|salary\s*cut": "income_loss",
    r"retire|early\s*retirement|fire\s*plan": "early_retirement",
    r"inherit|will|ancestral|gift\s*money": "inheritance",
    r"hospital|illness|surgery|medical\s*emergency|accident": "medical_emergency",
    r"mba|college|school|education|degree|course": "education",
}

# ─── Amount extraction regex ─────────────────────────────────────────────────

AMOUNT_PATTERNS = [
    r"₹\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|L)",       # ₹5 lakh
    r"₹\s*([\d,]+(?:\.\d+)?)\s*(?:crore|Cr|cr)",       # ₹1 crore
    r"₹\s*([\d,]+(?:\.\d+)?)\s*(?:k|K|thousand)",      # ₹50K
    r"([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|L)\b",           # 5 lakh (no ₹)
    r"([\d,]+(?:\.\d+)?)\s*(?:crore|Cr|cr)\b",          # 1 crore (no ₹)
    r"₹\s*([\d,]+(?:\.\d+)?)\b",                        # ₹500000
]

MULTIPLIERS = {
    "lakh": 100000, "lac": 100000, "L": 100000,
    "crore": 10000000, "Cr": 10000000, "cr": 10000000,
    "k": 1000, "K": 1000, "thousand": 1000,
}


def _extract_amount(text: str) -> float | None:
    """Extract a monetary amount from text."""
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace(",", "")
            try:
                num = float(num_str)
            except ValueError:
                continue

            # Check for multiplier
            rest = text[match.end():match.end() + 20].strip().lower()
            for word, mult in MULTIPLIERS.items():
                if word.lower() in rest or word.lower() in text[match.start():match.end() + 20].lower():
                    return num * mult

            # If number is small and no multiplier, it might be in lakhs context
            if num < 100:
                return num * 100000  # assume lakhs
            return num

    return None


def _regex_detect(text: str) -> tuple[str, float]:
    """Fast regex-based event detection. Returns (event_type, confidence)."""
    text_lower = text.lower()

    for pattern, event_type in TRIGGER_PATTERNS.items():
        if re.search(pattern, text_lower):
            return event_type, 0.7  # regex gives 0.7 confidence

    return "none", 0.0


async def detect_life_event(
    user_message: str,
) -> dict:
    """
    Detect a life event from user message.

    Strategy:
    1. First pass: regex match (fast, no API call)
    2. If no regex match: call llama3-8b for classification

    Args:
        user_message: The user's chat message

    Returns:
        {
            "event_type": str,
            "confidence": float,
            "extracted_amount": float | None,
            "extracted_timeline": str | None,
        }
    """
    # Phase 1: Regex
    event_type, confidence = _regex_detect(user_message)
    amount = _extract_amount(user_message)

    if confidence >= 0.7:
        return {
            "event_type": event_type,
            "confidence": confidence,
            "extracted_amount": amount,
            "extracted_timeline": None,
        }

    # Phase 2: LLM classification
    prompt = LIFE_EVENT_CLASSIFY_PROMPT.format(user_message=user_message)
    raw_response = await safe_invoke_fast(prompt, fallback='{"event_type":"none","confidence":0.0}')

    try:
        if "```json" in raw_response:
            raw_response = raw_response.split("```json")[1].split("```")[0].strip()
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        try:
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            result = json.loads(raw_response[start:end])
        except (json.JSONDecodeError, ValueError):
            result = {"event_type": "none", "confidence": 0.0}

    # Merge with our amount extraction
    if not result.get("extracted_amount") and amount:
        result["extracted_amount"] = amount

    return {
        "event_type": result.get("event_type", "none"),
        "confidence": result.get("confidence", 0.0),
        "extracted_amount": result.get("extracted_amount"),
        "extracted_timeline": result.get("extracted_timeline"),
    }
