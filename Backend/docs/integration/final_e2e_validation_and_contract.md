# Final E2E Validation + Integration Contract

Date: 2026-03-28
Environment: Local FastAPI (`127.0.0.1:8000`)

## 1) Final validation result
Status: PASS (core path)

Validated as working:
- Health + DB readiness (`mongo_ready=true`, `redis_ready=true`, `atlas_configured=true`)
- Onboarding + chat alias
- FIRE + Tax deterministic engines
- Portfolio xray async flow with valid mock funds
- CAMS mock agent job lifecycle
- Form16 assisted agent lifecycle + user-step completion
- WebSocket connection event (`connected`)

Sample run IDs:
- `portfolio_job_id`: `job_8aad6558a6eb`
- `cams_job_id`: `job_e11a1e4ee747`
- `form16_job_id`: `job_fd046ce7cad0`
- `fire_calc_id`: `calc_fire_207426049a`
- `tax_calc_id`: `calc_tax_a6f8e15a68`

---

## 2) Canonical endpoints for integration

## Base
- Backend base URL: `http://<host>:8000`

## Onboarding
- `POST /api/onboard`
- `POST /api/chat` (alias)

## Financial engines
- `POST /api/fire`
- `POST /api/tax`
- `POST /api/portfolio/xray`
- `GET /api/portfolio/xray/{job_id}`

## Behavioral
- `POST /api/behavioral/seed`
- `POST /api/intervention/simulate`
- `GET /api/arth-score/{user_id}`

## Async jobs
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/user-step`

## Ingestion start
- `POST /api/cams/agent/start`
- `POST /api/form16/agent/start`

## Realtime
- `WS /ws/{user_id}`

## Platform
- `GET /health`

---

## 3) JSON contract snippets (use as-is)

## CAMS start
```json
{
  "user_id": "usr_demo_001",
  "pan": "ABCDE1234F",
  "email": "demo@example.com",
  "mode": "mock",
  "provider_mode": "auto"
}
```

## Form16 start
```json
{
  "user_id": "usr_demo_001",
  "username": "demo_user",
  "password": "demo_pass",
  "mode": "assisted",
  "portal_url": "https://www.tdscpc.gov.in/"
}
```

## User-step submit
```json
{
  "step_type": "otp",
  "value": "123456"
}
```

## Portfolio xray (valid minimum)
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
          {"date": "2021-01-01", "amount": -100000, "type": "BUY"}
        ],
        "plan_type": "DIRECT",
        "expense_ratio": 0.44,
        "holdings": [
          {"stock": "Reliance Industries", "weight": 8.2}
        ]
      }
    ]
  }
}
```

## WebSocket first event
```json
{
  "type": "connected",
  "data": {
    "user_id": "usr_demo_001"
  }
}
```

---

## 4) Integration-critical caveats

1. Portfolio route returns `invalid_portfolio_input` if `inputs.funds` is empty.
2. CAMS/TRACES real portal automation is assisted by design; keep upload fallback visible.
3. Frontend must handle `awaiting_user_step` status and display `ai_next_step` when present.
4. Deterministic numeric outputs (FIRE/Tax/Portfolio math) must not be overwritten by LLM.
5. Keep SEBI disclaimer visible in all user-facing calculated outputs.

---

## 5) Extension integration status

Extension package path:
- `tools/chrome_guide_extension`

Verified here:
- `manifest.json` valid (MV3)
- `content.js` syntax valid
- `popup.js` syntax valid

Behavior implemented:
- Auto-by-site detect (KFin/TRACES)
- TRACES flow: `Tax Payer -> Login -> credentials -> captcha/otp -> download path`
- Wait/remind loop until user acts
- Auto resume after page changes
- Multi-language instruction mode

Note:
- Browser-level runtime behavior must still be validated manually on target portal pages after extension reload.

---

## 6) Devraj + Uttu handoff map

Devraj:
- Implement endpoint wiring from this file only.
- Add timeline UI for async jobs and user-step panel.
- Do not assume portfolio mock works with empty funds.

Uttu:
- Integrate narration and `ai_next_step` generation.
- Keep deterministic backend math untouched.
- Ensure fallback instruction always exists when AI fails/rate-limits.

