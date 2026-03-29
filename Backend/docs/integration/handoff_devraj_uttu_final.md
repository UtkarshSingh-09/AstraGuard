# AstraGuard Final Handoff (Backend -> Devraj + Uttu)

Date: 2026-03-28
Owner: Ankit (Backend)
Consumers: Devraj (Frontend), Uttu (AI/LangGraph)

## 1) Verified Current Backend State

## Health
- Endpoint: `GET /health`
- Latest verified response summary:
  - `mongo_ready=true`
  - `redis_ready=false` (connection reset currently)
  - `atlas_configured=true`

Note: Core APIs are functioning with Mongo even while Redis is down, but Redis-backed reliability features are degraded.

## Core APIs (smoke-tested)
- `POST /api/onboard` -> `status=gathering`
- `POST /api/chat` (alias) -> `status=gathering`
- `POST /api/fire` -> `status=success` + `calculation_id`
- `POST /api/tax` -> `status=success` + `calculation_id`
- `POST /api/behavioral/seed` -> `status=updated`
- `POST /api/intervention/simulate` -> valid risk payload
- `GET /api/arth-score/{user_id}` -> valid score payload
- `POST /api/cams/agent/start` (mock) + `GET /api/jobs/{job_id}` -> `complete`
- `POST /api/form16/agent/start` (assisted) + `/api/jobs/{job_id}/user-step` -> `complete`

## Important contract caveat
- `POST /api/portfolio/xray` with `mode=mock` requires `inputs.funds` with at least 1 fund.
- If `funds=[]` or missing, poll returns:
  - `status=error`
  - `code=invalid_portfolio_input`
  - message: `At least one fund is required`

---

## 2) API Contracts Devraj Should Use

## A. Onboarding
- `POST /api/onboard`
- Alias: `POST /api/chat`
- Keep same payload between both.

## B. FIRE
- `POST /api/fire`
- Call on input changes (debounce on frontend).
- Render `summary`, `glidepath`, `month_by_month_plan`, `consequence_timeline`, `audit_trail`.

## C. Tax
- `POST /api/tax`
- Render old/new slabs + `comparison` + `missed_deductions` + `audit_trail`.

## D. Portfolio
- `POST /api/portfolio/xray` then poll `GET /api/portfolio/xray/{job_id}`.
- For demo reliability use deterministic mock payload with funds.

## E. Ingestion Agents
- `POST /api/cams/agent/start`
- `POST /api/form16/agent/start`
- Track via `GET /api/jobs/{job_id}`
- Continue challenge via `POST /api/jobs/{job_id}/user-step`

## F. Live updates
- `WS /ws/{user_id}`
- Listen for:
  - `connected`
  - `job_update`
  - (behavioral push) `market_event`

---

## 3) Payloads to Copy (Known Working)

## CAMS start (mock)
```json
{
  "user_id": "usr_demo_001",
  "pan": "ABCDE1234F",
  "email": "demo@example.com",
  "mode": "mock",
  "provider_mode": "auto"
}
```

## Form16 start (assisted)
```json
{
  "user_id": "usr_demo_001",
  "username": "demo_user",
  "password": "demo_pass",
  "mode": "assisted",
  "portal_url": "https://www.tdscpc.gov.in/"
}
```

## Submit user step
```json
{
  "step_type": "otp",
  "value": "123456"
}
```

## Portfolio mock (minimum valid)
```json
{
  "user_id": "usr_demo_001",
  "mode": "mock",
  "inputs": {
    "as_of_date": "2026-03-28",
    "funds": [
      {
        "name": "Axis Bluechip Fund",
        "isin": "INF846K01EW2",
        "invested": 300000,
        "current_value": 387000,
        "transactions": [
          {"date": "2021-01-01", "amount": -100000, "type": "BUY"},
          {"date": "2022-01-01", "amount": -100000, "type": "BUY"},
          {"date": "2023-01-01", "amount": -100000, "type": "BUY"}
        ],
        "plan_type": "DIRECT",
        "expense_ratio": 0.44,
        "holdings": [
          {"stock": "Reliance Industries", "weight": 8.2},
          {"stock": "Infosys", "weight": 6.3}
        ]
      }
    ]
  }
}
```

---

## 4) What Uttu Should Integrate Now

## Env and AI bridge
- Required envs now include:
  - `GROQ_API_KEY`
  - `GROQ_BASE_URL` (optional)
  - `GROQ_MODEL` (optional)
  - `GROQ_TIMEOUT_SECONDS` (optional)

## Existing guidance hook
- Backend now adds `result.ai_next_step` in blocked/degraded ingestion states.
- Uttu can replace or enrich this by wiring LangGraph inference into same shape:
```json
{
  "instruction": "...",
  "step_type": "navigate|input|otp|captcha|upload|retry|contact_support",
  "needs_user_input": true,
  "confidence": 0.0,
  "reason": "...",
  "source": "groq|fallback|langgraph"
}
```

## Integration rule
- Keep deterministic math untouched.
- AI should only narrate/guide/recover.
- Never alter `fire_engine.py` / `tax_engine.py` numeric outputs from LLM.

---

## 5) Chrome Extension Handoff (Devraj + Uttu)

Path:
- `tools/chrome_guide_extension`

What it does now:
- Auto site detect (KFin/TRACES)
- On-page overlay tutorial
- Wait/remind loop until user acts
- Auto resume across page loads
- Multi-language selector (en/hinglish/hi)
- Optional websocket status display via backend URL + user_id

Important for frontend integration:
- Frontend can pass `user_id`, `backendUrl`, language via extension popup storage for now.
- Next phase: message bridge from frontend webapp to extension (window postMessage/native messaging) if needed.

---

## 6) Open Risks Before Demo

1. Redis not healthy in latest test (`connection reset`).
2. CAMS real mode remains portal-change sensitive (assisted fallback is stable path).
3. TRACES is assisted by design (captcha/otp/manual steps expected).
4. Portfolio route needs explicit valid `funds` input even in mock mode.

---

## 7) Go-Live Checklist (Team)

1. Confirm `/health` is green for both mongo and redis.
2. Frontend uses exact payload keys above (no drift).
3. Frontend handles `awaiting_user_step` and renders `ai_next_step` text.
4. Uttu attaches AI narration without modifying deterministic outputs.
5. Demo path uses:
   - KFin assisted guide + upload fallback
   - TRACES assisted guide + upload fallback
6. Keep SEBI disclaimer visible for user-facing outputs.

