"""
Agent 1: Orchestrator Agent
The brain of AstraGuard — LangGraph StateGraph that routes requests
to the correct agent and ensures compliance + literacy on every output.

Flow: START → detect_intent → [agent] → regulator_check → audit_narrate → literacy → END
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import StateGraph, END

from agents.state import AstraGuardState, SEBI_DISCLAIMER, VALID_INTENTS
from agents.dna_agent import run_dna_agent
from agents.fire_agent import run_fire_agent
from agents.tax_agent import run_tax_agent
from agents.portfolio_agent import run_portfolio_agent
from agents.behavioral_guard import run_behavioral_guard
from agents.regulator_guard import run_regulator_guard
from agents.literacy_agent import run_literacy_agent
from agents.life_simulator import run_life_simulator
from agents.audit_narrator import run_audit_narrator
from integrations.groq_client import safe_invoke_fast

logger = logging.getLogger("astraguard.agents.orchestrator")


# ═══════════════════════════════════════════════════════════════════════
# NODE FUNCTIONS — each node reads/writes to AstraGuardState
# ═══════════════════════════════════════════════════════════════════════

async def detect_intent_node(state: AstraGuardState) -> dict:
    """Detect user intent using llama3-8b, or use pre-populated state intent."""
    
    if state.get("intent"):
        logger.info(f"Bypassing LLM detection, intent forced to: {state.get('intent')}")
        return {"intent": state.get("intent"), "current_agent": state.get("intent")}

    message = state.get("current_message", "")
    conversation = state.get("conversation_history", [])

    if not message:
        return {"intent": "general", "error": None}

    prompt = f"""Classify this user message into exactly ONE intent.

Message: "{message}"

Recent conversation context (last 3 messages):
{json.dumps(conversation[-3:], default=str) if conversation else 'No context'}

VALID INTENTS:
- onboard: User is providing personal/financial information (age, salary, goals, investments)
- fire: User asking about retirement planning, FIRE, corpus, SIP amount
- tax: User asking about tax saving, regime comparison, deductions
- portfolio: User asking about mutual fund analysis, portfolio review, overlap
- behavioral: User expressing panic about market, wanting to stop SIP, market crash related
- life_event: User mentioning a life event (bonus, marriage, baby, job change, house purchase)
- general: General financial question or greeting

Return ONLY a JSON: {{"intent": "<one of the intents above>"}}"""

    raw = await safe_invoke_fast(prompt, fallback='{"intent": "general"}')

    try:
        if "```" in raw:
            raw = raw.split("```json")[-1].split("```")[0] if "```json" in raw else raw.split("```")[1].split("```")[0]
        result = json.loads(raw.strip())
        intent = result.get("intent", "general")
    except (json.JSONDecodeError, IndexError):
        # Try to find intent keyword in response
        raw_lower = raw.lower()
        intent = "general"
        for valid in VALID_INTENTS:
            if valid in raw_lower:
                intent = valid
                break

    if intent not in VALID_INTENTS:
        intent = "general"

    logger.info(f"Detected intent: {intent} for message: {message[:80]}")
    return {"intent": intent, "current_agent": intent}


async def onboard_node(state: AstraGuardState) -> dict:
    """Run DNA extraction agent."""
    try:
        result = await run_dna_agent(
            session_id=state.get("session_id", ""),
            conversation_history=state.get("conversation_history", []),
        )
        return {
            "financial_dna": result.get("extracted_so_far"),
            "behavioral_dna": result.get("behavioral_dna"),
            "final_response": result,
            "error": None,
        }
    except Exception as e:
        logger.error(f"DNA agent failed: {e}")
        return {"error": str(e), "final_response": {"error": str(e)}}


async def fire_node(state: AstraGuardState) -> dict:
    """Run FIRE narration agent."""
    try:
        calc_result = state.get("calculation_result") or {}
        fin_dna = state.get("financial_dna") or {}

        result = await run_fire_agent(
            calculation_result=calc_result,
            financial_dna=fin_dna,
        )

        narration_text = ""
        if isinstance(result.get("narration"), dict):
            narration_text = result["narration"].get("summary_narration", "")
        elif isinstance(result.get("narration"), str):
            narration_text = result["narration"]

        return {
            "narration": narration_text,
            "final_response": result,
            "audit_trail": calc_result.get("audit_trail", []),
            "error": None,
        }
    except Exception as e:
        logger.error(f"FIRE agent failed: {e}")
        return {"error": str(e), "final_response": {"error": str(e)}}


async def tax_node(state: AstraGuardState) -> dict:
    """Run Tax narration agent."""
    try:
        calc_result = state.get("calculation_result") or {}
        fin_dna = state.get("financial_dna") or {}

        result = await run_tax_agent(
            calculation_result=calc_result,
            financial_dna=fin_dna,
        )

        narration_text = ""
        if isinstance(result.get("narration"), dict):
            narration_text = result["narration"].get("key_insight", "")
        elif isinstance(result.get("narration"), str):
            narration_text = result["narration"]

        return {
            "narration": narration_text,
            "final_response": result,
            "audit_trail": calc_result.get("audit_trail", []),
            "error": None,
        }
    except Exception as e:
        logger.error(f"Tax agent failed: {e}")
        return {"error": str(e), "final_response": {"error": str(e)}}


async def portfolio_node(state: AstraGuardState) -> dict:
    """Run Portfolio narration agent."""
    try:
        calc_result = state.get("calculation_result") or {}
        fin_dna = state.get("financial_dna") or {}

        result = await run_portfolio_agent(
            calculation_result=calc_result,
            financial_dna=fin_dna,
        )

        narration_text = ""
        if isinstance(result.get("narration"), dict):
            narration_text = result["narration"].get("portfolio_health", "")
        elif isinstance(result.get("narration"), str):
            narration_text = result["narration"]

        return {
            "narration": narration_text,
            "final_response": result,
            "audit_trail": calc_result.get("audit_trail", []),
            "error": None,
        }
    except Exception as e:
        logger.error(f"Portfolio agent failed: {e}")
        return {"error": str(e), "final_response": {"error": str(e)}}


async def behavioral_node(state: AstraGuardState) -> dict:
    """Run Behavioral Guard agent."""
    try:
        intervention = state.get("intervention_data") or {}
        beh_dna = state.get("behavioral_dna") or {}
        fire_result = state.get("calculation_result") or {}

        result = await run_behavioral_guard(
            user_id=state.get("user_id", ""),
            market_drop_pct=intervention.get("market_drop_pct", 5.0),
            behavioral_dna=beh_dna,
            fire_result=fire_result,
            send_whatsapp=intervention.get("send_whatsapp", False),
            phone_number=intervention.get("phone_number"),
        )

        return {
            "intervention_data": result,
            "whatsapp_sent": result.get("whatsapp_sent", False),
            "final_response": result,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Behavioral guard failed: {e}")
        return {"error": str(e), "final_response": {"error": str(e)}}


async def life_event_node(state: AstraGuardState) -> dict:
    """Run Life Simulator agent."""
    try:
        result = await run_life_simulator(
            user_id=state.get("user_id", ""),
            event_description=state.get("current_message", ""),
            financial_dna=state.get("financial_dna") or {},
            behavioral_dna=state.get("behavioral_dna") or {},
            current_fire_result=state.get("calculation_result"),
        )

        return {
            "simulation_result": result,
            "narration": result.get("narration", ""),
            "final_response": result,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Life simulator failed: {e}")
        return {"error": str(e), "final_response": {"error": str(e)}}


async def general_node(state: AstraGuardState) -> dict:
    """Handle general financial questions with direct LLM response."""
    message = state.get("current_message", "")

    prompt = f"""You are AstraGuard, an AI financial companion.
Answer this question briefly in Hinglish (Hindi-English mix).
Be helpful but always add that this is not professional financial advice.

Question: {message}

Rules:
- Max 3 sentences
- Use ₹ with Indian number format
- NEVER say "guaranteed", "sure shot", "definitely"
- End with SEBI disclaimer

Answer:"""

    response = await safe_invoke_fast(prompt, fallback="Main is question ka answer generate nahi kar pa raha. Kripya thodi der baad try karein.")

    return {
        "narration": response,
        "final_response": {"response": response},
        "error": None,
    }


async def regulator_check_node(state: AstraGuardState) -> dict:
    """Run RegulatorGuard on the agent output."""
    narration = state.get("narration", "")
    intent = state.get("intent", "general")

    if not narration:
        return {
            "is_compliant": True,
            "compliance_flags": [],
            "sebi_disclaimer": SEBI_DISCLAIMER,
        }

    try:
        result = await run_regulator_guard(
            output_text=narration,
            calculation_type=intent,
        )

        return {
            "is_compliant": result.get("is_compliant", True),
            "compliance_flags": result.get("flags", []),
            "compliance_adjusted_output": result.get("adjusted_output"),
            "sebi_disclaimer": SEBI_DISCLAIMER,
        }
    except Exception as e:
        logger.error(f"Regulator guard failed: {e}")
        return {
            "is_compliant": True,  # fail-open for demo
            "compliance_flags": [],
            "sebi_disclaimer": SEBI_DISCLAIMER,
        }


async def audit_narrate_node(state: AstraGuardState) -> dict:
    """Narrate the audit trail if present."""
    audit_trail = state.get("audit_trail", [])
    intent = state.get("intent", "general")

    if not audit_trail:
        return {}

    try:
        result = await run_audit_narrator(
            audit_trail=audit_trail,
            calculation_type=intent,
        )

        # Attach to final response
        final = state.get("final_response") or {}
        final["audit_narration"] = result

        return {"final_response": final}
    except Exception as e:
        logger.error(f"Audit narrator failed: {e}")
        return {}


async def literacy_node(state: AstraGuardState) -> dict:
    """Generate literacy content if applicable."""
    intent = state.get("intent", "")
    calc_result = state.get("calculation_result")

    # Only generate for calculation-type intents
    if intent not in ("fire", "tax", "portfolio") or not calc_result:
        return {}

    try:
        result = await run_literacy_agent(
            user_id=state.get("user_id", ""),
            calculation_type=intent,
            calculation_result=calc_result,
            financial_dna=state.get("financial_dna") or {},
            current_literacy_scores=state.get("literacy_scores"),
        )

        final = state.get("final_response") or {}
        final["literacy_insight"] = result

        return {
            "literacy_insight": result,
            "final_response": final,
        }
    except Exception as e:
        logger.error(f"Literacy agent failed: {e}")
        return {}


async def format_output_node(state: AstraGuardState) -> dict:
    """Final formatting — inject SEBI disclaimer and structure output."""
    final = state.get("final_response") or {}

    # Inject compliance-adjusted narration if available
    adjusted = state.get("compliance_adjusted_output")
    if adjusted and adjusted != state.get("narration"):
        final["llm_narration"] = adjusted
        final["original_narration"] = state.get("narration")
    else:
        final["llm_narration"] = state.get("narration")

    # Inject SEBI disclaimer
    final["sebi_disclaimer"] = SEBI_DISCLAIMER

    # Inject compliance flags
    final["compliance_flags"] = state.get("compliance_flags", [])

    return {"final_response": final}


# ═══════════════════════════════════════════════════════════════════════
# ROUTING LOGIC
# ═══════════════════════════════════════════════════════════════════════

def route_by_intent(state: AstraGuardState) -> str:
    """Route to the appropriate agent node based on detected intent."""
    intent = state.get("intent", "general")

    route_map = {
        "onboard": "onboard",
        "fire": "fire",
        "tax": "tax",
        "portfolio": "portfolio",
        "behavioral": "behavioral",
        "life_event": "life_event",
        "general": "general",
    }

    return route_map.get(intent, "general")


# ═══════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════

def build_orchestrator_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for AstraGuard.

    Graph flow:
    START → detect_intent → [route to agent] → regulator_check
          → audit_narrate → literacy → format_output → END
    """
    graph = StateGraph(AstraGuardState)

    # ── Add nodes ─────────────────────────────────────────────────────
    graph.add_node("detect_intent", detect_intent_node)
    graph.add_node("onboard", onboard_node)
    graph.add_node("fire", fire_node)
    graph.add_node("tax", tax_node)
    graph.add_node("portfolio", portfolio_node)
    graph.add_node("behavioral", behavioral_node)
    graph.add_node("life_event", life_event_node)
    graph.add_node("general", general_node)
    graph.add_node("regulator_check", regulator_check_node)
    graph.add_node("audit_narrate", audit_narrate_node)
    graph.add_node("literacy", literacy_node)
    graph.add_node("format_output", format_output_node)

    # ── Entry point ───────────────────────────────────────────────────
    graph.set_entry_point("detect_intent")

    # ── Conditional routing from detect_intent ────────────────────────
    graph.add_conditional_edges(
        "detect_intent",
        route_by_intent,
        {
            "onboard": "onboard",
            "fire": "fire",
            "tax": "tax",
            "portfolio": "portfolio",
            "behavioral": "behavioral",
            "life_event": "life_event",
            "general": "general",
        },
    )

    # ── All agents → regulator_check ──────────────────────────────────
    for agent_node in ["onboard", "fire", "tax", "portfolio", "behavioral", "life_event", "general"]:
        graph.add_edge(agent_node, "regulator_check")

    # ── Sequential post-processing chain ──────────────────────────────
    graph.add_edge("regulator_check", "audit_narrate")
    graph.add_edge("audit_narrate", "literacy")
    graph.add_edge("literacy", "format_output")
    graph.add_edge("format_output", END)

    return graph


# ─── Compiled Graph (singleton) ───────────────────────────────────────────────

_compiled_graph = None


def get_orchestrator():
    """Get or create the compiled orchestrator graph."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_orchestrator_graph()
        _compiled_graph = graph.compile()
        logger.info("Orchestrator graph compiled successfully")
    return _compiled_graph


# ─── Main execution entry point ──────────────────────────────────────────────

async def run_orchestrator(
    user_id: str,
    message: str,
    session_id: str = "",
    conversation_history: list[dict] | None = None,
    financial_dna: dict | None = None,
    behavioral_dna: dict | None = None,
    calculation_result: dict | None = None,
    literacy_scores: dict | None = None,
    intervention_data: dict | None = None,
    force_intent: str | None = None,
) -> dict:
    """
    Main entry point — run a user message through the full agent pipeline.

    This is what Ankit's FastAPI routes call.

    Args:
        user_id: User identifier
        message: Current user message
        session_id: Session identifier
        conversation_history: Full conversation history
        financial_dna: User's financial profile (from DB)
        behavioral_dna: User's behavioral profile (from DB)
        calculation_result: Pre-computed math engine result (if applicable)
        literacy_scores: Current literacy scores (from DB)
        intervention_data: Market/intervention context (if applicable)

    Returns:
        The final_response dict from the graph execution
    """
    orchestrator = get_orchestrator()

    initial_state: AstraGuardState = {
        "user_id": user_id,
        "session_id": session_id,
        "current_message": message,
        "conversation_history": conversation_history or [],
        "financial_dna": financial_dna,
        "behavioral_dna": behavioral_dna,
        "calculation_result": calculation_result,
        "literacy_scores": literacy_scores,
        "intervention_data": intervention_data,
        "messages": [],
        "intent": force_intent or "",
        "sub_intent": "",
        "current_agent": "",
        "narration": None,
        "audit_trail": [],
        "compliance_flags": [],
        "compliance_adjusted_output": None,
        "is_compliant": True,
        "literacy_insight": None,
        "simulation_result": None,
        "whatsapp_sent": False,
        "final_response": None,
        "sebi_disclaimer": SEBI_DISCLAIMER,
        "error": None,
    }

    try:
        final_state = await orchestrator.ainvoke(initial_state)
        return final_state.get("final_response", {"error": "No response generated"})
    except Exception as e:
        logger.error(f"Orchestrator execution failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "sebi_disclaimer": SEBI_DISCLAIMER,
        }
