"""
Agent 6: Behavioral Guard Agent
The key differentiator — proactive intervention when market drops
approach the user's panic threshold.

Generates personalized WhatsApp messages via Twilio.
Uses llama-3.3-70b-versatile for message quality.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_quality
from integrations.twilio_whatsapp import send_whatsapp_message
from prompts.behavioral_prompts import (
    BEHAVIORAL_INTERVENTION_PROMPT,
    SEVERITY_DESCRIPTIONS,
)
from agents.state import SEBI_DISCLAIMER_SHORT

logger = logging.getLogger("astraguard.agents.behavioral_guard")


# ─── Intervention Severity Tiers ──────────────────────────────────────────────

def _determine_severity(proximity_pct: float) -> str:
    """Determine intervention severity based on proximity to panic threshold."""
    if proximity_pct >= 100:
        return "CRITICAL"
    elif proximity_pct >= 80:
        return "HARD"
    elif proximity_pct >= 60:
        return "SOFT"
    elif proximity_pct >= 40:
        return "NUDGE"
    else:
        return "NONE"


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


def _build_fallback_message(
    market_drop: float, planned_retire_age: float,
    stop_retire_age: float, additional_saving: float,
) -> dict:
    """Template fallback when LLM is unavailable."""
    delta = stop_retire_age - planned_retire_age
    return {
        "whatsapp_message": (
            f"📉 Market aaj {market_drop}% gira. "
            f"SIP rok diya toh retirement {delta:.1f} saal delay hogi. "
            f"₹{additional_saving:,.0f} extra chahiye hoga. Stay strong! 💪\n"
            f"{SEBI_DISCLAIMER_SHORT}"
        ),
        "extended_message": (
            f"Market crash mein panic mat kar. Historically market hamesha recover karta hai. "
            f"Teri SIP hamesha low pe buy karti hai — yeh discount hai, loss nahi.\n"
            f"{SEBI_DISCLAIMER_SHORT}"
        ),
        "cta_text": "Continue My SIP 💪",
        "severity_emoji": "📉",
    }


async def run_behavioral_guard(
    user_id: str,
    market_drop_pct: float,
    behavioral_dna: dict,
    fire_result: dict,
    send_whatsapp: bool = True,
    phone_number: str | None = None,
) -> dict:
    """
    Evaluate market drop against user's panic threshold and generate intervention.

    Args:
        user_id: User identifier
        market_drop_pct: Today's market drop percentage (positive number, e.g., 7.2)
        behavioral_dna: User's behavioral profile
        fire_result: Latest FIRE calculation result
        send_whatsapp: Whether to send WhatsApp message
        phone_number: User's WhatsApp number (if sending)

    Returns:
        {
            "risk_state": dict,
            "consequence_simulation": dict,
            "intervention_message": dict,
            "whatsapp_sent": bool,
            "whatsapp_sid": str | None,
        }
    """
    panic_threshold = abs(behavioral_dna.get("panic_threshold", 17.0))
    proximity_pct = (market_drop_pct / panic_threshold) * 100 if panic_threshold else 0
    severity = _determine_severity(proximity_pct)

    # Build risk state
    risk_state = {
        "type": "panic_risk" if proximity_pct > 40 else "monitoring",
        "severity": severity,
        "proximity_to_threshold_pct": round(proximity_pct, 1),
        "market_drop": market_drop_pct,
        "user_threshold": panic_threshold,
    }

    # FIRE consequence if SIP stops
    summary = fire_result.get("summary", {})
    planned_retire_age = summary.get("estimated_retire_age_with_plan", 50)
    stop_retire_age = summary.get("estimated_retire_age_current", 52)
    additional_saving = summary.get("corpus_gap", 0)

    consequence = {
        "base_retire_age": planned_retire_age,
        "stop_sip_retire_age": stop_retire_age,
        "retire_age_delta": round(stop_retire_age - planned_retire_age, 1),
        "additional_saving_needed": additional_saving,
    }

    # No intervention needed
    if severity == "NONE":
        return {
            "risk_state": risk_state,
            "consequence_simulation": consequence,
            "intervention_message": {"type": "NONE", "message": "No intervention needed"},
            "whatsapp_sent": False,
            "whatsapp_sid": None,
        }

    # Generate intervention message via LLM
    prompt = BEHAVIORAL_INTERVENTION_PROMPT.format(
        panic_threshold=panic_threshold,
        last_panic_event=behavioral_dna.get("last_panic_event", "No data"),
        behavior_type=behavioral_dna.get("behavior_type", "unknown"),
        sip_pauses=behavioral_dna.get("sip_pauses_last_12m", 0),
        streak_days=behavioral_dna.get("streak_days", 0),
        market_drop=market_drop_pct,
        proximity_pct=round(proximity_pct, 1),
        stop_retire_age=stop_retire_age,
        planned_retire_age=planned_retire_age,
        additional_saving=additional_saving,
        goal_name=fire_result.get("consequence_timeline", [{}])[0].get("event", "Retirement"),
        severity=severity,
        severity_description=SEVERITY_DESCRIPTIONS.get(severity, ""),
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    message_data = _parse_json_response(raw_response)

    if not message_data:
        message_data = _build_fallback_message(
            market_drop_pct, planned_retire_age, stop_retire_age, additional_saving
        )

    # Send WhatsApp if requested
    whatsapp_sent = False
    whatsapp_sid = None

    if send_whatsapp and phone_number and severity in ("SOFT", "HARD", "CRITICAL"):
        try:
            result = await send_whatsapp_message(
                to_number=phone_number,
                message_body=message_data.get("whatsapp_message", ""),
            )
            whatsapp_sent = result.get("success", False)
            whatsapp_sid = result.get("sid")
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            whatsapp_sent = False

    return {
        "risk_state": risk_state,
        "consequence_simulation": consequence,
        "intervention_message": {
            "type": severity,
            "whatsapp_sent": whatsapp_sent,
            **message_data,
        },
        "whatsapp_sent": whatsapp_sent,
        "whatsapp_sid": whatsapp_sid,
    }
