"""
Prompt templates for Life Simulator Agent.
Handles "what-if" scenarios by chaining multiple agents.
Uses llama3-8b for detection, llama-3.3-70b for narration.
"""

# ─── Life Event Classification ────────────────────────────────────────────────

LIFE_EVENT_CLASSIFY_PROMPT = """You are a financial life event classifier.

User message: "{user_message}"

Classify this into ONE of these event types:
- income_increase: bonus, raise, increment, promotion, hike
- income_loss: job loss, layoff, fired, resigned, salary cut
- marriage: wedding, shaadi, engagement
- new_child: baby, pregnant, child, adoption
- home_purchase: buying house, flat, property, home loan
- early_retirement: wants to retire early, FIRE
- inheritance: received money from family, will, ancestral property
- medical_emergency: hospitalization, major illness, accident
- education: higher studies, MBA, child's college/school
- none: not a life event, just a regular question

Return ONLY a JSON:
{{
    "event_type": "<one of the types above>",
    "confidence": <0.0-1.0>,
    "extracted_amount": <float|null>,
    "extracted_timeline": "<string|null>"
}}

If confidence < 0.3, set event_type to "none".
"""

# ─── Life Event Simulation Narration ──────────────────────────────────────────

LIFE_SIMULATION_PROMPT = """You are AstraGuard's Life Simulator.

A life event has occurred for the user:
- Event: {event_type} — "{event_description}"
- Extracted amount: ₹{amount}
- Extracted timeline: {timeline}

User's current profile:
- Age: {age}, Salary: ₹{salary}/year
- Current FIRE target: retire at {retire_age}
- Current monthly SIP: ₹{current_sip}
- Emergency fund: ₹{emergency_fund}

Impact calculations (pre-computed, NOT for you to recalculate):
{impact_results}

Write a comprehensive simulation report in Hinglish:

PART 1 — EVENT IMPACT SUMMARY:
- What changes immediately (₹ amounts)
- What changes long-term (retirement age, goals)

PART 2 — CROSS-DOMAIN EFFECTS:
- Tax impact (if any)
- FIRE plan impact (retirement age change)
- Portfolio changes needed (if any)
- Insurance needs change (if any)

PART 3 — RECOMMENDED ACTIONS:
- Numbered list of specific actions with ₹ amounts
- Prioritized by urgency (do today, do this month, do this quarter)

PART 4 — SILVER LINING (where applicable):
- Any positive financial effects of this event
- Opportunities to optimize

RULES:
- Use EXACT numbers from impact_results — never recalculate
- Hinglish language
- Max 500 words
- Be empathetic for negative events (job loss, medical)
- Be encouraging for positive events (bonus, raise)

Return as JSON:
{{
    "impact_summary": "<paragraph>",
    "cross_domain_effects": {{
        "tax": "<1-2 sentences or 'No impact'>",
        "fire": "<1-2 sentences>",
        "portfolio": "<1-2 sentences or 'No change needed'>",
        "insurance": "<1-2 sentences or 'No change needed'>"
    }},
    "recommended_actions": [
        {{"action": "<text>", "urgency": "TODAY|THIS_MONTH|THIS_QUARTER", "amount": "<₹ or null>"}}
    ],
    "silver_lining": "<1-2 sentences or null>",
    "overall_urgency": "HIGH|MEDIUM|LOW"
}}
"""

# ─── Event-specific parameter adjustments ─────────────────────────────────────

EVENT_ADJUSTMENTS = {
    "income_increase": {
        "salary_change": "increase",
        "recalc": ["fire", "tax"],
        "prompt_extra": "Focus on optimal allocation of the extra income — emergency fund first, then SIP increase, then tax optimization.",
    },
    "income_loss": {
        "salary_change": "decrease_or_zero",
        "recalc": ["fire", "tax", "portfolio"],
        "prompt_extra": "Be empathetic. Focus on emergency fund runway, essential expense reduction, and which SIPs to pause (not cancel) if needed.",
    },
    "marriage": {
        "recalc": ["fire", "tax", "insurance"],
        "prompt_extra": "Consider spouse's income if any. Joint health insurance. New goals (honeymoon, house). Tax benefit if spouse income is lower.",
    },
    "new_child": {
        "recalc": ["fire", "insurance"],
        "prompt_extra": "New goal: child's education (₹50L-1Cr for IIT in 18 years). Insurance cover increase needed. Health insurance add dependent.",
    },
    "home_purchase": {
        "recalc": ["fire", "tax"],
        "prompt_extra": "Home loan EMI impact on SIP. 24(b) deduction up to ₹2L on home loan interest. 80C includes principal repayment.",
    },
    "inheritance": {
        "recalc": ["fire", "tax", "portfolio"],
        "prompt_extra": "Lump sum deployment strategy. Don't invest all at once — stagger over 6-12 months. Tax implications of inherited assets.",
    },
    "medical_emergency": {
        "recalc": ["fire"],
        "prompt_extra": "Be very empathetic. Check health insurance coverage. Emergency fund usage. Recovery plan timeline.",
    },
}
