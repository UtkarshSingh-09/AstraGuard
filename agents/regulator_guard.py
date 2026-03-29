"""
Agent 7: Regulator Guard Agent 🔥
Compliance watchdog — every output passes through this before reaching the user.
Uses ChromaDB RAG over SEBI/Tax rules + llama3-8b for fast classification.
"""

from __future__ import annotations

import json
import logging
import re

from integrations.groq_client import safe_invoke_fast
from integrations.chromadb_rag import query_regulations
from prompts.regulator_prompts import (
    COMPLIANCE_CHECK_PROMPT,
    BLOCKED_PHRASES,
    REGULATORY_LIMITS,
)
from agents.state import SEBI_DISCLAIMER

logger = logging.getLogger("astraguard.agents.regulator_guard")


def _check_blocked_phrases(text: str) -> list[dict]:
    """Check for hard-blocked phrases (no LLM needed, pure regex)."""
    flags = []
    text_lower = text.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase in text_lower:
            flags.append({
                "type": "BLOCK",
                "rule": "SEBI_PROHIBITED_CLAIMS",
                "issue": f"Contains prohibited phrase: '{phrase}'",
                "original_text": phrase,
                "suggested_fix": f"Remove or rephrase '{phrase}' — no financial claims should use absolute language.",
            })
    return flags


def _check_return_assumptions(text: str) -> list[dict]:
    """Check for unrealistic return assumptions using regex."""
    flags = []

    # Look for percentage patterns like "15%" or "16% return"
    pct_patterns = re.findall(r'(\d{2,3})%?\s*(?:return|CAGR|growth|earning)', text, re.IGNORECASE)
    for pct in pct_patterns:
        pct_val = int(pct)
        max_equity = REGULATORY_LIMITS["equity_return_max_assumption"] * 100
        if pct_val > max_equity:
            flags.append({
                "type": "FLAG",
                "rule": "SEBI_RETURN_ASSUMPTION",
                "issue": f"{pct_val}% return assumption exceeds historical Nifty CAGR of ~12-13%",
                "original_text": f"{pct_val}%",
                "suggested_fix": f"Use {int(max_equity)}% as conservative equity return estimate per historical data.",
            })

    return flags


def _check_section_limits(text: str) -> list[dict]:
    """Check for wrong tax section limits in the text."""
    flags = []
    limits = {
        "80C": REGULATORY_LIMITS["80C_max"],
        "80CCD(1B)": REGULATORY_LIMITS["80CCD_1B_max"],
        "80CCD_1B": REGULATORY_LIMITS["80CCD_1B_max"],
        "80D": REGULATORY_LIMITS["80D_self_max"],
    }

    for section, max_val in limits.items():
        # Look for patterns like "80C ₹2,00,000" or "80C limit 200000"
        pattern = rf'{re.escape(section)}[^₹\d]*[₹]?\s*(\d[\d,]*)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            amount = int(match.replace(",", ""))
            if amount > max_val * 1.1:  # 10% tolerance for rounding
                flags.append({
                    "type": "BLOCK",
                    "rule": f"INCOME_TAX_{section}_LIMIT",
                    "issue": f"Section {section} limit stated as ₹{amount:,} — actual limit is ₹{max_val:,}",
                    "original_text": f"₹{amount:,}",
                    "suggested_fix": f"Correct to ₹{max_val:,} as per Income Tax Act.",
                })

    return flags


def _apply_fixes(text: str, flags: list[dict]) -> str:
    """Apply suggested fixes to the output text."""
    adjusted = text

    for flag in flags:
        if flag["type"] == "BLOCK" and "PROHIBITED_CLAIMS" in flag.get("rule", ""):
            # Remove the blocked phrase
            adjusted = adjusted.replace(flag["original_text"], "[removed — prohibited claim]")

        elif flag["type"] == "FLAG" and "RETURN_ASSUMPTION" in flag.get("rule", ""):
            # Replace high return assumption with conservative one
            old_pct = flag["original_text"]
            adjusted = adjusted.replace(old_pct, "12%")

    return adjusted


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


async def run_regulator_guard(
    output_text: str,
    calculation_type: str = "general",
) -> dict:
    """
    Check output for SEBI/RBI/Tax compliance before it reaches the user.

    Args:
        output_text: The text/narration to check
        calculation_type: "fire", "tax", "portfolio", or "general"

    Returns:
        {
            "is_compliant": bool,
            "adjusted_output": str,
            "flags": list[dict],
            "sebi_disclaimer": str,
            "rules_referenced": list[dict],
        }
    """
    all_flags = []

    # ── Phase 1: Fast regex checks (no LLM needed) ───────────────────
    all_flags.extend(_check_blocked_phrases(output_text))
    all_flags.extend(_check_return_assumptions(output_text))
    all_flags.extend(_check_section_limits(output_text))

    # If we already found BLOCK-level violations, fix immediately
    has_blocks = any(f["type"] == "BLOCK" for f in all_flags)

    # ── Phase 2: RAG-enhanced LLM check ──────────────────────────────
    rules_referenced = []
    try:
        relevant_rules = await query_regulations(output_text, n_results=3)
        rules_text = "\n".join(
            f"- {r.get('document', '')}" for r in relevant_rules
        )
        rules_referenced = [
            {"rule": r.get("metadata", {}).get("source", "Unknown"), "relevance": r.get("distance", 0)}
            for r in relevant_rules
        ]
    except Exception as e:
        logger.warning(f"ChromaDB query failed: {e}. Proceeding without RAG.")
        rules_text = "No regulatory context available."

    # LLM compliance check (only if no obvious blocks found)
    if not has_blocks:
        prompt = COMPLIANCE_CHECK_PROMPT.format(
            output_text=output_text,
            relevant_rules=rules_text,
        )
        raw_response = await safe_invoke_fast(prompt, fallback='{"verdict":"COMPLIANT","flags":[]}')
        llm_result = _parse_json_response(raw_response)

        if llm_result.get("flags"):
            all_flags.extend(llm_result["flags"])

    # ── Phase 3: Apply fixes ──────────────────────────────────────────
    adjusted_output = _apply_fixes(output_text, all_flags)

    # Determine overall compliance
    has_any_blocks = any(f["type"] == "BLOCK" for f in all_flags)
    is_compliant = len(all_flags) == 0

    return {
        "is_compliant": is_compliant,
        "adjusted_output": adjusted_output,
        "flags": all_flags,
        "sebi_disclaimer": SEBI_DISCLAIMER,
        "rules_referenced": rules_referenced,
    }
