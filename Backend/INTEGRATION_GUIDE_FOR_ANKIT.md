# 🔗 AstraGuard — Backend ↔ AI Agents Integration Guide

> **For: Ankit (Backend Developer)**
> **From: Uttu (AI/ML)**
> **Last Updated: 28 March 2026**

---

## 📌 TL;DR — What Ankit Needs to Do

1. **Copy the `agents/`, `prompts/`, `integrations/`, `schemas/`, `data/`, `scripts/` folders** into your FastAPI project
2. **Install dependencies** from `requirements.txt`
3. **Set env variables** (GROQ_API_KEY, Twilio, ChromaDB)
4. **Seed ChromaDB** once: `python3 scripts/seed_chromadb.py`
5. **Call ONE function** from your FastAPI routes: `run_orchestrator()`
6. The AI system handles everything else — intent detection, LLM narration, compliance, literacy

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ANKIT'S FASTAPI                              │
│                                                                     │
│  POST /api/onboard     ──┐                                         │
│  POST /api/fire         ─┤                                         │
│  POST /api/tax          ─┤── All routes call ──▶ run_orchestrator() │
│  POST /api/portfolio    ─┤                                         │
│  POST /api/intervene    ─┤                                         │
│  POST /api/life-event   ─┘                                         │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     UTTU'S AI AGENT SYSTEM                          │
│                                                                     │
│  run_orchestrator()                                                 │
│       │                                                             │
│       ├── detect_intent (llama3-8b)                                │
│       ├── route to agent ──▶ [DNA|FIRE|Tax|Portfolio|Behavioral     │
│       │                       |LifeSim|General]                     │
│       ├── regulator_check (ChromaDB RAG + llama3-8b)               │
│       ├── audit_narrate (llama-3.3-70b)                            │
│       ├── literacy (llama-3.3-70b)                                 │
│       └── format_output ──▶ return final_response dict             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Files to Copy

Copy these folders/files INTO your FastAPI project root:

```
agents/                 ← 10 agent files + state.py + __init__.py
├── __init__.py
├── state.py
├── orchestrator.py     ← MAIN ENTRY POINT
├── dna_agent.py
├── fire_agent.py
├── tax_agent.py
├── portfolio_agent.py
├── behavioral_guard.py
├── regulator_guard.py
├── literacy_agent.py
├── life_simulator.py
└── audit_narrator.py

prompts/                ← all LLM prompt templates
├── __init__.py
├── dna_prompts.py
├── narration_prompts.py
├── behavioral_prompts.py
├── regulator_prompts.py
├── literacy_prompts.py
├── simulator_prompts.py
└── audit_prompts.py

integrations/           ← Groq, Twilio, ChromaDB, Life Events
├── __init__.py
├── groq_client.py
├── twilio_whatsapp.py
├── chromadb_rag.py
└── life_events.py

schemas/                ← Pydantic models (shared data contracts)
├── __init__.py
├── financial_dna.py
├── arth_score.py
└── api_contracts.py

data/sebi_rules/        ← 11 regulatory docs for ChromaDB RAG
├── sebi_mf_regulations.txt
├── sebi_ia_guidelines.txt
├── sebi_return_claims.txt
├── income_tax_80c.txt
├── income_tax_new_regime.txt
├── income_tax_old_regime.txt
├── income_tax_ltcg_stcg.txt
├── income_tax_deductions.txt
├── income_tax_hra.txt
├── emergency_fund_guidelines.txt
└── insurance_guidelines.txt

scripts/
├── seed_chromadb.py    ← run once to populate vector store
└── test_twilio.py      ← test WhatsApp delivery

requirements.txt        ← pip dependencies
.env.example            ← env variable template
```

---

## ⚙️ Setup on Ankit's Machine

### Step 1: Install Python Dependencies

```bash
# Add these to YOUR existing requirements.txt or install separately
pip install langchain-groq langgraph chromadb twilio tenacity python-dotenv pydantic
```

Or use the full `requirements.txt` I've provided:

```bash
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

Add these to your `.env` file:

```env
# === REQUIRED ===
GROQ_API_KEY=gsk_your_groq_api_key_here

# === TWILIO (for WhatsApp interventions) ===
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# === CHROMADB ===
CHROMADB_PERSIST_DIR=./chroma_data
```

### Step 3: Seed ChromaDB (One Time)

```bash
python3 scripts/seed_chromadb.py
```

Output:
```
📂 Found 11 document files
✅ Successfully seeded 41 document chunks into ChromaDB!
```

This creates the `./chroma_data/` folder. Do NOT delete it.

---

## 🔌 THE MAIN FUNCTION — `run_orchestrator()`

This is the **ONLY function you need to import**:

```python
from agents.orchestrator import run_orchestrator
```

### Function Signature

```python
async def run_orchestrator(
    user_id: str,                                    # REQUIRED — from MongoDB
    message: str,                                    # REQUIRED — user's chat message
    session_id: str = "",                            # optional — session tracking
    conversation_history: list[dict] | None = None,  # optional — previous messages
    financial_dna: dict | None = None,               # optional — from MongoDB
    behavioral_dna: dict | None = None,              # optional — from MongoDB
    calculation_result: dict | None = None,           # optional — from YOUR math engines
    literacy_scores: dict | None = None,              # optional — from MongoDB
    intervention_data: dict | None = None,            # optional — for behavioral guard
) -> dict:
```

### It Returns a `dict` — Always

The response always contains:

```python
{
    # === ALWAYS PRESENT ===
    "sebi_disclaimer": "⚠️ Disclaimer: This is AI-generated guidance...",
    "compliance_flags": [],  # list of any compliance issues found

    # === PRESENT BASED ON INTENT ===
    "llm_narration": "...",  # the LLM-generated text to show the user

    # === OPTIONAL (depend on the flow) ===
    "audit_narration": {...},    # humanized audit trail
    "literacy_insight": {...},   # micro-lesson + quiz
    "error": null,               # or error string if something failed
}
```

---

## 📡 Route-by-Route Integration

### 1. POST `/api/chat` — General Chat / Onboarding

The orchestrator auto-detects intent. Just pass the message.

```python
# In your FastAPI route:
from agents.orchestrator import run_orchestrator

@app.post("/api/chat")
async def chat(user_id: str, message: str, session_id: str = ""):
    # Load user profile from MongoDB (if exists)
    user = await db.users.find_one({"_id": user_id})

    result = await run_orchestrator(
        user_id=user_id,
        message=message,
        session_id=session_id,
        conversation_history=user.get("conversation_history", []) if user else [],
        financial_dna=user.get("financial_dna") if user else None,
        behavioral_dna=user.get("behavioral_dna") if user else None,
    )

    # Save updated conversation to MongoDB
    await db.users.update_one(
        {"_id": user_id},
        {"$push": {"conversation_history": {"role": "user", "content": message}}},
        upsert=True,
    )

    return result
```

**What happens inside:**
- If user says "Meri umar 28 hai" → intent = `onboard` → DNA agent extracts age
- If user says "Tax kaise bachun?" → intent = `tax` → needs `calculation_result`
- If user says "Market gir raha hai, SIP rokun?" → intent = `behavioral`

---

### 2. POST `/api/fire` — FIRE Plan

**YOUR math engine calculates first, THEN the AI narrates.**

```python
@app.post("/api/fire")
async def fire_plan(request: FireRequest):
    # Step 1: YOUR math engine calculates
    calc_result = fire_engine.calculate(
        age=request.inputs["age"],
        salary=request.inputs["annual_salary"],
        monthly_expense=request.inputs["monthly_expenses"],
        # ... etc
    )
    # calc_result should look like:
    # {
    #     "summary": {
    #         "corpus_needed": 52000000,
    #         "monthly_sip_total_needed": 42000,
    #         "estimated_retire_age_with_plan": 48,
    #         "estimated_retire_age_current": 52,
    #         "corpus_gap": 18000000,
    #     },
    #     "glidepath": [...],
    #     "consequence_timeline": [...],
    #     "audit_trail": [
    #         {"step": "inflation_adjusted_monthly_need", "formula": "150000 × (1.06^16)", "result": 381000},
    #         {"step": "total_corpus_needed", "formula": "381000 × 12 / 0.04", "result": 114300000},
    #         ...
    #     ]
    # }

    # Step 2: AI narrates the result
    user = await db.users.find_one({"_id": request.user_id})

    result = await run_orchestrator(
        user_id=request.user_id,
        message="FIRE plan calculate karo",  # or pass actual user message
        financial_dna=user.get("financial_dna"),
        calculation_result=calc_result,       # ← YOUR ENGINE'S OUTPUT
    )

    return result
    # AI returns:
    # {
    #     "narration": { "summary_narration": "...", "consequence_narrative": "..." },
    #     "llm_narration": "Tujhe retire hone ke liye ₹5.2 Cr chahiye...",
    #     "audit_narration": { "narrated_steps": [...] },  ← humanized audit
    #     "literacy_insight": { "micro_lesson": {...}, "quiz": {...} },
    #     "sebi_disclaimer": "⚠️ Disclaimer...",
    #     "compliance_flags": [],
    # }
```

---

### 3. POST `/api/tax` — Tax Calculation

```python
@app.post("/api/tax")
async def tax_plan(request: TaxRequest):
    # Step 1: YOUR tax engine calculates
    calc_result = tax_engine.calculate(
        annual_salary=request.inputs["annual_salary"],
        # ... deductions
    )
    # calc_result should look like:
    # {
    #     "old_regime": { "total_tax": 147680, "deductions_used": {...} },
    #     "new_regime": { "total_tax": 162500 },
    #     "comparison": { "optimal_regime": "OLD", "savings_with_optimal": 14820 },
    #     "missed_deductions": [
    #         { "section": "80CCD(1B)", "max_limit": 50000, "current_usage": 0,
    #           "potential_tax_saving": 15600, "action": "Open NPS account" }
    #     ],
    #     "audit_trail": [...]
    # }

    # Step 2: AI narrates
    result = await run_orchestrator(
        user_id=request.user_id,
        message="Tax comparison karo",
        calculation_result=calc_result,
    )

    return result
```

---

### 4. POST `/api/portfolio` — Portfolio X-Ray

```python
@app.post("/api/portfolio")
async def portfolio_xray(request: PortfolioXrayRequest):
    # Step 1: YOUR portfolio engine analyzes
    calc_result = portfolio_engine.analyze(
        funds=request.funds,
        # ...
    )
    # calc_result should look like:
    # {
    #     "portfolio_summary": { "portfolio_xirr": 14.2, "total_value": 850000 },
    #     "overlap_analysis": { "overlap_severity": "HIGH", "overlap_pairs": [...] },
    #     "expense_analysis": { "total_annual_expense_drag": 4200 },
    #     "rebalancing_plan": [...],
    #     "funds": [
    #         { "fund_name": "HDFC Top 100", "plan_type": "REGULAR", ... }
    #     ],
    #     "audit_trail": [...]
    # }

    # Step 2: AI narrates
    result = await run_orchestrator(
        user_id=request.user_id,
        message="Portfolio review karo",
        calculation_result=calc_result,
    )

    return result
```

---

### 5. POST `/api/intervene` — Behavioral Intervention (WhatsApp)

**Call this when market drops significantly.**

```python
@app.post("/api/intervene")
async def intervene(request: InterventionSimulateRequest):
    user = await db.users.find_one({"_id": request.user_id})
    fire_result = await db.fire_results.find_one({"user_id": request.user_id})

    result = await run_orchestrator(
        user_id=request.user_id,
        message="Market gir raha hai",
        behavioral_dna=user.get("behavioral_dna"),
        calculation_result=fire_result,             # latest FIRE result
        intervention_data={
            "market_drop_pct": request.market_drop_pct,  # e.g., 7.2
            "send_whatsapp": request.send_whatsapp,
            "phone_number": user.get("phone_number"),     # "+917565960168"
        },
    )

    return result
    # AI returns:
    # {
    #     "risk_state": {"severity": "HARD", "proximity_to_threshold_pct": 85.0},
    #     "consequence_simulation": {"retire_age_delta": 3.2, "additional_saving_needed": 1840000},
    #     "intervention_message": {
    #         "whatsapp_message": "📉 Market 7.2% gira. SIP rok diya toh 3.2 saal aur kaam...",
    #         "severity_emoji": "📉",
    #         "cta_text": "Continue My SIP 💪"
    #     },
    #     "whatsapp_sent": true,
    #     "whatsapp_sid": "SM1234..."
    # }
```

**Severity Tiers for Behavioral Guard:**

| Proximity to Panic | Severity  | Action |
|---|---|---|
| < 40% | NONE | No intervention |
| 40–60% | NUDGE | Light reassurance |
| 60–80% | SOFT | Reference past behavior |
| 80–100% | HARD | Full consequence binding |
| ≥ 100% | CRITICAL | Maximum personalization + WhatsApp |

---

### 6. POST `/api/life-event` — Life Simulator

```python
@app.post("/api/life-event")
async def life_event(request: LifeSimulatorRequest):
    user = await db.users.find_one({"_id": request.user_id})
    fire_result = await db.fire_results.find_one({"user_id": request.user_id})

    result = await run_orchestrator(
        user_id=request.user_id,
        message=request.event_description,  # "Mujhe 5 lakh ka bonus mila"
        financial_dna=user.get("financial_dna"),
        behavioral_dna=user.get("behavioral_dna"),
        calculation_result=fire_result,
    )

    return result
    # AI returns:
    # {
    #     "event_type": "income_increase",
    #     "adjusted_financial_dna": {...},  ← USE THIS TO RECALCULATE FIRE/TAX
    #     "domains_to_recalculate": ["fire", "tax"],  ← which engines to rerun
    #     "narration": "5 lakh ka bonus mila! Tax impact...",
    #     "recommended_actions": [
    #         {"action": "Emergency fund top up", "urgency": "TODAY", "amount": "₹1L"},
    #         {"action": "SIP increase", "urgency": "THIS_MONTH", "amount": "₹8K/month"}
    #     ],
    #     "urgency": "MEDIUM"
    # }
```

**Supported Life Events:**
`income_increase`, `income_loss`, `marriage`, `new_child`, `home_purchase`, `inheritance`, `medical_emergency`, `education`, `early_retirement`

---

## 📋 Math Engine Output Format (What I NEED from You)

### FIRE Engine — Expected Output Structure

```python
{
    "summary": {
        "corpus_needed": 52000000,           # total retirement corpus
        "monthly_sip_total_needed": 42000,   # monthly SIP to reach corpus
        "estimated_retire_age_with_plan": 48, # if SIP continues
        "estimated_retire_age_current": 52,   # if SIP stops now
        "corpus_gap": 18000000,              # shortfall
        "current_corpus": 1500000,            # existing investments total
    },
    "glidepath": [
        {"age": 28, "equity_pct": 80, "debt_pct": 20},
        {"age": 35, "equity_pct": 70, "debt_pct": 30},
        # ...
    ],
    "consequence_timeline": [
        {"age": 30, "event": "Emergency fund secured", "amount": 500000},
        {"age": 36, "event": "₹4.2L compounding advantage", "amount": 420000},
        # ...
    ],
    "insurance_gap": {
        "current_cover": 5000000,
        "recommended_cover": 18000000,
        "gap": 13000000,
    },
    "emergency_fund": {
        "current": 200000,
        "recommended": 480000,
        "gap": 280000,
    },
    "audit_trail": [
        {
            "step": "inflation_adjusted_monthly_need",
            "formula": "150000 × (1.06^16)",
            "inputs": {"monthly_draw": 150000, "inflation": 0.06, "years": 16},
            "result": 381000,
            "timestamp": "2026-03-28T00:15:00Z"
        },
        {
            "step": "total_corpus_needed",
            "formula": "381000 × 12 / 0.04",
            "inputs": {"monthly_need": 381000, "swr": 0.04},
            "result": 114300000,
            "timestamp": "2026-03-28T00:15:00Z"
        }
        # ... more steps
    ]
}
```

### Tax Engine — Expected Output Structure

```python
{
    "old_regime": {
        "gross_income": 1800000,
        "total_deductions": 250000,
        "taxable_income": 1550000,
        "tax_before_cess": 202500,
        "cess": 8100,
        "total_tax": 210600,
        "effective_rate": 11.7,
        "deductions_used": {
            "80C": 150000,
            "80CCD_1B": 50000,
            "80D": 25000,
            "standard_deduction": 50000,
            "hra": 0
        }
    },
    "new_regime": {
        "gross_income": 1800000,
        "standard_deduction": 75000,
        "taxable_income": 1725000,
        "tax_before_cess": 222500,
        "cess": 8900,
        "total_tax": 231400,
        "effective_rate": 12.9
    },
    "comparison": {
        "optimal_regime": "OLD",
        "savings_with_optimal": 20800,
        "old_tax": 210600,
        "new_tax": 231400
    },
    "missed_deductions": [
        {
            "section": "80CCD(1B)",
            "max_limit": 50000,
            "current_usage": 0,
            "potential_tax_saving": 15600,
            "action": "Open NPS Tier 1 and invest ₹50,000"
        },
        {
            "section": "80D",
            "max_limit": 25000,
            "current_usage": 0,
            "potential_tax_saving": 7800,
            "action": "Buy health insurance — family floater ₹8,000–12,000/year premium"
        }
    ],
    "audit_trail": [
        {
            "step": "gross_income_calculation",
            "formula": "salary + hra + special_allowance",
            "result": 1800000
        }
        # ...
    ]
}
```

### Portfolio Engine — Expected Output Structure

```python
{
    "portfolio_summary": {
        "total_invested": 850000,
        "current_value": 980000,
        "portfolio_xirr": 14.2,
        "nifty_benchmark_xirr": 12.5,
        "alpha": 1.7,
        "total_funds": 5
    },
    "funds": [
        {
            "fund_name": "HDFC Top 100 Fund - Regular Growth",
            "plan_type": "REGULAR",
            "category": "Large Cap",
            "invested": 300000,
            "current_value": 340000,
            "xirr": 12.1,
            "expense_ratio": 1.82,
            "direct_expense_ratio": 0.95,
            "holding_days": 380,
            "gain_type": "LTCG"
        }
        # ...
    ],
    "overlap_analysis": {
        "overlap_severity": "HIGH",
        "overlap_percentage": 45.2,
        "overlap_pairs": [
            {"fund_a": "HDFC Top 100", "fund_b": "ICICI Bluechip", "overlap_pct": 62}
        ]
    },
    "expense_analysis": {
        "total_annual_expense_drag": 4200,
        "potential_saving_direct": 2800,
        "annual_expense_drag_10yr_compound": 47000
    },
    "rebalancing_plan": [
        {
            "fund_name": "HDFC Top 100 Fund - Regular Growth",
            "action": "SWITCH",
            "reason": "Regular plan — switch to direct for ₹2,800/yr saving",
            "immediate_action": "Switch to HDFC Top 100 Fund - Direct Growth",
            "after_ltcg_action": "Safe to switch — holding > 1 year, LTCG applies"
        }
    ],
    "audit_trail": [...]
}
```

---

## 🔐 Twilio WhatsApp Setup

Already configured:

| Key | Value |
|---|---|
| Account SID | `your_twilio_sid_here` |
| Auth Token | `your_twilio_auth_token_here` |
| Sandbox Number | `+14155238886` |
| Test WhatsApp | `+917565960168` |

**Important:** Any user who wants to receive WhatsApp messages must first send `join <sandbox-word>` to `+14155238886` on WhatsApp. This is a Twilio sandbox limitation.

Test command:
```bash
python3 scripts/test_twilio.py --to "+917565960168" --message "🚀 Test from AstraGuard!"
```

---

## 🗄️ MongoDB Schema Recommendations

### `users` Collection

```json
{
    "_id": "usr_abc123",
    "phone_number": "+917565960168",
    "financial_dna": {
        "age": 28,
        "annual_salary": 1800000,
        "monthly_expenses": 60000,
        "existing_investments": {
            "mutual_funds": 500000,
            "ppf": 100000,
            "fd": 200000,
            "stocks": 0,
            "epf": 300000,
            "nps": 0
        },
        "goals": [
            {
                "name": "Retirement",
                "target_amount": 50000000,
                "target_year": 2050,
                "emotional_label": "Freedom 🏖️"
            }
        ],
        "insurance_cover": 5000000,
        "risk_profile": "moderate",
        "city_type": "metro",
        "has_home_loan": false,
        "rent_paid_monthly": 25000,
        "hra_received": 30000
    },
    "behavioral_dna": {
        "panic_threshold": -15.0,
        "behavior_type": "panic_prone",
        "last_panic_event": "COVID March 2020 — sold 50% equity in panic",
        "action_rate": 0.7,
        "recovery_awareness": "LOW",
        "sip_pauses_last_12m": 2,
        "panic_portfolio_checks": 5
    },
    "literacy_scores": {
        "tax": 35,
        "mutual_funds": 20,
        "fire": 10,
        "insurance": 15,
        "overall": 20
    },
    "conversation_history": [
        {"role": "user", "content": "Meri salary 18 lakh hai"},
        {"role": "assistant", "content": "Accha! Aur monthly expenses kitna hai?"}
    ],
    "created_at": "2026-03-28T00:00:00Z"
}
```

---

## ⚠️ Critical Rules

1. **NEVER let the AI do math** — All calculations come from YOUR deterministic Python engines. The AI only narrates.

2. **Always pass `calculation_result`** for FIRE/Tax/Portfolio routes — without it the AI has nothing to narrate and will return a generic response.

3. **Include `audit_trail`** in your calculation results — the AuditNarrator agent converts these into human-readable educational walkthroughs. Without it, no trace.

4. **Save `financial_dna` to MongoDB** after onboarding — the DNA agent extracts it from conversation but doesn't save it. Your backend handles persistence.

5. **SEBI Disclaimer** is auto-injected into every response. Don't strip it — the frontend MUST display it.

6. **Compliance flags** — if `compliance_flags` is not empty, there were issues in the AI output. The `llm_narration` field will contain the corrected version.

7. **Life Simulator returns `adjusted_financial_dna`** — after a life event, you should use this adjusted DNA to re-run your math engines (FIRE/Tax/Portfolio) and call the orchestrator again with the new results.

---

## 🧪 Quick Integration Test

Once you have everything set up, test with:

```python
import asyncio
from agents.orchestrator import run_orchestrator

async def test():
    result = await run_orchestrator(
        user_id="test_user_1",
        message="Meri salary 18 lakh hai aur age 28",
        conversation_history=[],
    )
    print(result)

asyncio.run(test())
```

This should detect intent as `onboard`, extract age=28 and salary=1800000, and ask the next question.

---

## 🚀 Deployment Notes (Digital Ocean)

1. **ChromaDB data**: Include `chroma_data/` folder in deployment. It's ~5MB.
2. **Groq API**: Free tier = 30 requests/minute. Rate limiter is built into `groq_client.py`.
3. **Twilio Sandbox**: Works immediately. Production needs Meta Business Verification (2-7 days).
4. **Python version**: Must be 3.13+ (uses `X | None` syntax).
5. **Memory**: ChromaDB embedding model uses ~200MB RAM on first load, ~50MB after.

---

## 🆘 Troubleshooting

| Issue | Fix |
|---|---|
| `GROQ_API_KEY not found` | Add it to `.env` file |
| `ChromaDB collection empty` | Run `python3 scripts/seed_chromadb.py` |
| `Twilio 21608 error` | Recipient hasn't joined sandbox |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Rate limit exceeded` | Built-in 30 RPM limiter handles this. Wait 60s. |
| AI response is empty | Check if `calculation_result` was passed for FIRE/Tax/Portfolio |

---

## 📞 Quick Contact

- **Uttu**: AI agent questions, LLM behavior, prompt tweaks
- **Ankit**: Math engines, API routes, MongoDB, deployment

**The AI system is 100% ready. Ankit just needs to wire it up to your FastAPI routes.** 🚀
