# AstraGuard Integration Handoff (Ankit -> Utkarsh)

Date: 2026-03-28

## 1) Integration Principle
- Backend is source-of-truth for all deterministic math and contract payloads.
- AI layer should enrich narration/compliance text only.
- AI failure must never break deterministic payload.

## 2) Backend Endpoints Ready
- `POST /api/onboard`
- `POST /api/chat` (alias)
- `POST /api/fire`
- `POST /api/tax`
- `POST /api/portfolio/xray`
- `GET /api/portfolio/xray/{job_id}`
- `POST /api/behavioral/seed`
- `POST /api/intervention/simulate`
- `GET /api/arth-score/{user_id}`
- `GET /api/audit/{calculation_id}`
- `POST /api/documents/validate`
- `GET /health`
- `WS /ws/{user_id}`

## 3) AI Hook Surface
- `services/backend/app/services/ai_bridge.py`
- Integrate your orchestrator behind `NarrationProvider`.

## 4) Contract Notes
- FIRE and Tax responses include `audit_trail` and `sebi_disclaimer`.
- Tax route supports:
  - `tax_profile=contract_demo`
  - `tax_profile=research_standard`
- Portfolio xray supports:
  - `mode=mock` (immediate analysis)
  - `mode=cams_auto` (async placeholder pipeline)

## 5) Persistence Model
- MongoDB Atlas collections:
  - `users`
  - `sessions`
  - `audit_logs`
  - `interventions`
- Redis used for runtime queue/cache/session support.

## 6) WebSocket Events
- Connected event on open.
- Echo event for incoming text.
- Market event pushed from intervention simulation.
- Job updates pushed automatically on any async job state change:
  - event type: `job_update`
  - payload:
    - `job_id`
    - `job_type`
    - `job_status`
    - `message`
    - `result`
    - `error`

## 7) Known Pending Items
- Real Playwright CAMS/TRACES automation wiring.
- Twilio send function binding inside intervention route.
- Production retry/backoff queue policy.
