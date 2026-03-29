"""
Prompt templates for the DNA extraction agent.
Uses llama3-8b for fast, structured JSON extraction from conversation.
"""

# ─── DNA Extraction System Prompt ─────────────────────────────────────────────

DNA_SYSTEM_PROMPT = """You are AstraGuard's Financial DNA Extractor.
Your job is to extract a user's financial profile from a natural conversation.

RULES:
1. Extract ONLY information explicitly stated by the user.
2. NEVER guess, assume, or hallucinate any numbers.
3. If a field is not mentioned, set it to null.
4. Return ONLY valid JSON. No explanation, no markdown, no extra text.
5. Respond in Hinglish (Hindi-English mix) for the next_question.
6. Be warm, conversational, and non-judgmental.
7. Ask ONE question at a time — never overwhelm the user.

JSON SCHEMA TO FILL:
{schema}

COMPLETION RULES:
- MINIMUM required fields for "complete": age, annual_salary, monthly_expenses, at least 1 goal
- Behavioral DNA needs: panic_threshold OR last_panic_event OR behavior description
- Track completion_percentage based on filled fields out of total expected fields
"""

# ─── DNA Extraction User Prompt ───────────────────────────────────────────────

DNA_EXTRACTION_PROMPT = """Conversation so far:
{conversation_history}

Based on this conversation, extract all financial information into the JSON schema.
Also determine:
1. completion_percentage (0-100): how much of the profile is filled
2. next_question: what to ask next to fill missing fields (in Hinglish)
3. status: "gathering" if still missing info, "complete" if all minimum fields filled

Return this exact JSON structure:
{{
    "status": "<gathering|complete>",
    "completion_percentage": <0-100>,
    "next_question": "<question in Hinglish or null if complete>",
    "financial_dna": {{
        "age": <int|null>,
        "annual_salary": <float|null>,
        "monthly_expenses": <float|null>,
        "existing_investments": {{
            "mutual_funds": <float|0>,
            "ppf": <float|0>,
            "fd": <float|0>,
            "stocks": <float|0>,
            "epf": <float|0>,
            "nps": <float|0>
        }},
        "goals": [
            {{
                "name": "<string>",
                "target_amount": <float|null>,
                "target_year": <int|null>,
                "emotional_label": "<string|null>"
            }}
        ],
        "insurance_cover": <float|null>,
        "risk_profile": "<conservative|moderate|aggressive|null>",
        "city_type": "<metro|non-metro|null>",
        "rent_paid_monthly": <float|null>,
        "hra_received": <float|null>,
        "has_home_loan": <bool>,
        "home_loan_interest_annual": <float|null>
    }},
    "behavioral_dna": {{
        "panic_threshold": <float|null>,
        "behavior_type": "<panic_prone|disciplined|impulsive|passive|null>",
        "last_panic_event": "<string|null>",
        "action_rate": <float|null>,
        "recovery_awareness": "<LOW|MEDIUM|HIGH|null>"
    }}
}}
"""

# ─── Question Flow (ordered by priority) ─────────────────────────────────────

QUESTION_FLOW = [
    # Basic profile
    "Chalo shuru karte hain! Pehle bata — teri umar kitni hai? 😊",
    "Aur salary kitni hai teri? Monthly ya yearly — jo bhi comfortable ho.",
    "Monthly expenses kitne hain approximately? Rent, groceries, EMI sab mila ke?",
    "Kaunse city mein rehta hai? Metro (Delhi/Mumbai/Bangalore) ya non-metro?",
    # Investments
    "Koi existing investments hain? Mutual funds, PPF, FD, stocks — jo bhi ho?",
    "EPF ya NPS mein kuch hai? Company deduct karti hai?",
    # Goals
    "Ab goals ki baat karte hain — kya achieve karna chahta hai? Retirement, ghar, bachche ki padhai, emergency fund — jo bhi ho?",
    "Iss goal ko kab tak achieve karna hai? Kitne saal mein?",
    # Insurance
    "Life insurance hai? Term plan ya koi bhi? Kitne ka cover hai?",
    "Health insurance? Family floater ya individual?",
    # Behavioral (the differentiator)
    "Ek important question — March 2020 mein jab COVID crash hua tha, tune kya kiya tha? SIP roka? Panic sell kiya? Ya continue kiya?",
    "Market kitna gire tab tak tu comfortable rehta hai? -5%? -10%? -15%?",
    # HRA / Home Loan
    "Rent deta hai? Kitna monthly? Aur company se HRA milta hai?",
    "Home loan hai? Annual interest kitna pay karta hai?",
]

# ─── Behavioral Seeding Questions ─────────────────────────────────────────────

BEHAVIORAL_QUESTIONS = [
    {
        "question": "Ek cheez bata — jab market girta hai, tu kitni baar portfolio check karta hai? Din mein ek baar? Har ghante? Ya ignore karta hai?",
        "extracts": "panic_portfolio_checks",
    },
    {
        "question": "Pichle 1 saal mein SIP miss ya pause kiya hai kabhi?",
        "extracts": "sip_pauses_last_12m",
    },
    {
        "question": "Jab market recovery hota hai crash ke baad — tujhe lagta hai market wapas aayega ya nahi?",
        "extracts": "recovery_awareness",
    },
]
