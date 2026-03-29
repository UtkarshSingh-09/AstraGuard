# AstraGuard Hybrid CAS Strategy (Build vs Buy)

Date: 2026-03-28  
Owner: Ankit (Backend)  
Consumers: Utkarsh (AI), Devraj (Frontend)

## 1) Decision (Approved)
- Use a hybrid ingestion architecture.
- Primary path: Managed CAS provider API (high reliability).
- Secondary path: In-house assisted Playwright agent (innovation + fallback).
- Tertiary path: Manual file upload (always-on safety net).

## 2) Why Hybrid
- Pure Playwright is brittle due portal layout changes, anti-bot checks, captcha, and dynamic flows.
- Pure third-party provider reduces innovation visibility and creates vendor dependency.
- Hybrid gives both demo reliability and technical depth.

## 3) Build vs Buy Matrix

| Option | Reliability | Dev Speed | Cost | Control | Demo Risk |
|---|---:|---:|---:|---:|---:|
| In-house Playwright only | Medium-Low | Medium | Low | High | High |
| Third-party CAS API only | High | High | Medium | Medium-Low | Low |
| Hybrid (recommended) | High | Medium-High | Medium | High | Low |

## 4) Runtime Routing Contract

`POST /api/cams/agent/start`

Request extension:
```json
{
  "user_id": "usr_demo_001",
  "pan": "ABCDE1234F",
  "email": "user@example.com",
  "mode": "real",
  "provider_mode": "auto",
  "priority": ["provider_api", "assisted_playwright", "upload_fallback"]
}
```

Behavior:
- `provider_mode=auto`: try provider first, then Playwright, then upload fallback.
- `provider_mode=provider_only`: no Playwright fallback.
- `provider_mode=playwright_only`: current in-house flow only.

Response:
```json
{
  "status": "processing",
  "job_id": "job_xxx",
  "job_type": "cams_fetch",
  "message": "CAMS background agent started"
}
```

## 5) Unified Job State Model

States:
- `queued`
- `running`
- `awaiting_user_step`
- `downloaded`
- `parsed`
- `complete`
- `failed`

Result envelope:
```json
{
  "status": "success",
  "job_id": "job_xxx",
  "job_status": "complete",
  "result": {
    "source": "provider_api|assisted_playwright|upload_fallback",
    "document_type": "cams_statement",
    "attachment": {
      "path": "artifacts/...",
      "filename": "statement.pdf",
      "confidence": 0.95
    }
  }
}
```

## 6) Frontend Contract (Devraj)
- Start one job from dashboard/form.
- Listen over WebSocket for progress updates.
- Show step timeline in UI:
  - `request_submitted`
  - `portal_navigation`
  - `awaiting_user_step` (if any)
  - `document_received`
  - `parsed`
  - `done`
- If source switches to fallback, show non-blocking banner:
  - "Auto-fetch unstable, upload route activated."

## 7) Utkarsh Integration Contract
- Utkarsh does not change ingestion math or parser output schema.
- Utkarsh can consume:
  - `job_status`
  - `result.source`
  - `error.code`
  - `evidence.steps`
- Utkarsh adds only:
  - narration for user status updates
  - confidence explanation text
  - intervention suggestions when ingestion fails repeatedly

## 8) Security Controls
- Credentials only in ephemeral in-memory secret store with TTL.
- No PAN/email/password persistence in audit logs.
- Masked hints only in payload (`pan_last4`, `email_hint`).
- Purge secret context on job completion/failure.

## 9) Rollout Plan
1. Keep current Playwright flow as baseline.
2. Add provider adapter interface:
   - `ProviderCASClient.request_statement()`
   - `ProviderCASClient.poll_statement()`
3. Add router in CAMS agent for `provider_mode`.
4. Keep upload fallback default enabled.
5. Add health metric counters:
   - provider success rate
   - playwright success rate
   - fallback activation rate

## 10) Immediate Next Task
- Implement progress push over WebSocket for ingestion jobs so frontend does not rely on polling only.
