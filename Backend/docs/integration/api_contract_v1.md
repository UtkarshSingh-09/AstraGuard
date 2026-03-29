# AstraGuard API Contract v1

Date: 2026-03-28
Owner: Backend (Ankit)
Consumers: Frontend (Devraj), AI layer (Utkarsh)

## Locked Decisions
- DB: MongoDB + Redis
- Alias support: `/api/onboard` and `/api/chat`
- Document mode: assisted auto-fetch + upload fallback
- Canonical schema authority: backend contracts

## Core Endpoints
- `POST /api/onboard`
- `POST /api/chat` (alias of onboard for compatibility)
- `POST /api/fire`
- `POST /api/tax`
- `POST /api/portfolio/xray`
- `GET /api/portfolio/xray/{job_id}`
- `POST /api/behavioral/seed`
- `POST /api/intervention/simulate`
- `GET /api/arth-score/{user_id}`
- `GET /health`
- `GET /api/audit/{calculation_id}`
- `POST /api/documents/validate`
- `POST /api/cams/agent/start`
- `POST /api/form16/agent/start`
- `WS /ws/{user_id}`

## Unified Async Job Endpoints
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/user-step`

Purpose:
- CAMS/Form16 assisted automation status tracking
- OTP/captcha/manual step continuation
- Shared job framework for all ingestion workflows

## Error Envelope (canonical)
```json
{
  "status": "error",
  "error": {
    "code": "invalid_input",
    "message": "Monthly expense must be positive",
    "details": {
      "field": "monthly_expenses"
    }
  },
  "timestamp": "2026-03-28T06:20:00Z"
}
```

## Tax Engine Profile Note
- `POST /api/tax` supports optional input key `tax_profile`:
  - `contract_demo` (default) -> keeps current frontend/demo expected outputs.
  - `research_standard` -> uses source-backed rule profile from `docs/research/approved_math_spec_v1.md`.

## Portfolio X-Ray Mode Note
- `POST /api/portfolio/xray` supports:
  - `mode="mock"` -> immediate in-process analysis, result retrievable via poll endpoint.
  - `mode="cams_auto"` -> async placeholder flow (processing state) for CAMS pipeline integration in next steps.

## Ingestion Agent Notes
- `POST /api/cams/agent/start`
  - `mode=mock` (reliable demo completion)
  - `mode=real` (attempts Playwright CAMS request submission)
  - optional `provider_mode` = `auto | provider_only | playwright_only`
  - optional `auto_ingest_mailbox=true` with `mailbox_app_password` for mailbox polling and CAS auto-attach payload
- `POST /api/form16/agent/start`
  - `mode=assisted` (waits for challenge/OTP via `/api/jobs/{job_id}/user-step`)
  - `mode=mock` (reliable demo completion)
  - optional `portal_url` (default TRACES homepage)
- Secrets are stored in ephemeral in-memory secret store and not persisted to MongoDB.
- For recoverable agent states (`awaiting_user_step`, `degraded_mode`, some `failed` cases), payload may include:
  - `ai_next_step.instruction`
  - `ai_next_step.step_type`
  - `ai_next_step.needs_user_input`
  - `ai_next_step.confidence`
  - `ai_next_step.source` (`groq` or `fallback`)

## Persistence Notes
- Onboard/chat writes session conversation and extracted progress to `sessions`.
- FIRE/Tax/Portfolio writes audit trails to `audit_logs` with generated `calculation_id`.
- Latest summary snapshots are upserted to `users`.
- Health endpoint reports DB readiness flags.

## Atlas Note
- MongoDB is intended to run on Atlas (`mongodb+srv://...`).
- `/health` reports `atlas_configured` flag based on connection string format.
