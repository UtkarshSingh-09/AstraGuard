"""
LangGraph shared state definition.
This TypedDict flows through every agent node in the orchestrator graph.
"""

from __future__ import annotations

from typing import TypedDict, Annotated
from operator import add


class AstraGuardState(TypedDict, total=False):
    """
    Shared state flowing through the LangGraph StateGraph.
    Every agent reads from and writes to this state.

    Fields marked total=False are optional and may be None.
    """

    # ─── User Identity ────────────────────────────────────────────────
    user_id: str
    session_id: str

    # ─── Intent Detection ─────────────────────────────────────────────
    intent: str  # onboard, fire, tax, portfolio, behavioral, life_event, general
    sub_intent: str  # more specific, e.g., "bonus_flow", "marriage_flow"

    # ─── User Profile (loaded from DB or extracted live) ──────────────
    financial_dna: dict | None
    behavioral_dna: dict | None
    literacy_scores: dict | None

    # ─── Conversation ─────────────────────────────────────────────────
    conversation_history: list[dict]  # [{role: "user"/"assistant", content: str}]
    current_message: str  # latest user message

    # ─── Agent Execution ──────────────────────────────────────────────
    current_agent: str  # which agent is currently active
    calculation_result: dict | None  # raw result from math engines
    narration: str | None  # LLM-generated text
    audit_trail: list[dict]  # step-by-step calculation trace

    # ─── Compliance (RegulatorGuard) ──────────────────────────────────
    compliance_flags: list[str]  # e.g., ["FLAG_HIGH_RETURN_ASSUMPTION"]
    compliance_adjusted_output: str | None
    is_compliant: bool

    # ─── Financial Literacy ───────────────────────────────────────────
    literacy_insight: dict | None  # micro-lesson + quiz from LiteracyAgent

    # ─── Life Simulation ──────────────────────────────────────────────
    simulation_result: dict | None  # from LifeSimulatorAgent

    # ─── Behavioral Guard ─────────────────────────────────────────────
    intervention_data: dict | None  # intervention message + risk state
    whatsapp_sent: bool

    # ─── Output ───────────────────────────────────────────────────────
    final_response: dict | None  # the structured response to send to frontend
    sebi_disclaimer: str
    error: str | None

    # ─── Internal message bus ─────────────────────────────────────────
    messages: Annotated[list[dict], add]  # accumulates across nodes


# ─── Constants ────────────────────────────────────────────────────────────────

SEBI_DISCLAIMER = (
    "⚠️ Disclaimer: This is AI-generated guidance for educational purposes only. "
    "Not licensed financial advice under SEBI (Investment Advisers) Regulations, 2013. "
    "Past performance does not guarantee future results. "
    "Consult a SEBI-registered investment adviser before making financial decisions."
)

SEBI_DISCLAIMER_SHORT = (
    "⚠️ AI guidance only. Not SEBI-registered advice. Consult a professional."
)

# Valid intents for orchestrator routing
VALID_INTENTS = [
    "onboard",
    "fire",
    "tax",
    "portfolio",
    "behavioral",
    "life_event",
    "general",
]
