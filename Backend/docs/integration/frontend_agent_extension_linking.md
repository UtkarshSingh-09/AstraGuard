# Frontend + Agent + Extension Linking Guide

Date: 2026-03-28
Consumers: Devraj (Frontend), Uttu (Agents)

## Objective
Seamlessly connect:
1. Next.js frontend
2. FastAPI backend job system
3. Chrome extension guided assistant
4. Uttu AI guidance (`ai_next_step`)

## Runtime Sequence (Recommended)
1. Frontend creates/loads `user_id`.
2. Frontend opens websocket: `ws://<backend>/ws/{user_id}`.
3. Frontend starts ingestion job:
   - CAMS: `POST /api/cams/agent/start`
   - Form16: `POST /api/form16/agent/start`
4. Frontend renders live `job_update` events.
5. If `job_status=awaiting_user_step`:
   - show `result.ai_next_step.instruction`
   - offer challenge input UI
   - call `POST /api/jobs/{job_id}/user-step`
6. If user wants portal help, launch extension guide.
7. Extension guides step-by-step on KFin/TRACES.
8. User completes portal action and returns with file/upload or continues assisted flow.

## Frontend -> Extension Data Contract (current practical)
Current extension reads from popup storage. For integration now:
- `userId`
- `backendUrl`
- `guideType` (`auto|cams|form16`)
- `lang` (`en|hinglish|hi`)

Near-term improvement (optional):
- use `window.postMessage` bridge with extension content script listener for one-click launch from frontend.

## What Devraj should render
- Job timeline component per `job_id`.
- `awaiting_user_step` panel with:
  - primary instruction: `result.ai_next_step.instruction`
  - confidence badge
  - step_type chip (`otp`, `captcha`, etc.)
- Fallback upload CTA always visible.

## What Uttu should implement
- Keep `ai_next_step` schema stable.
- Replace fallback text only; do not mutate deterministic payloads.
- For low confidence, provide safe/manual instruction.

## Failure-safe UX Rules
1. Never block user only on automation.
2. Always present manual upload fallback.
3. Preserve prior job result while next attempt runs.
4. Show explicit source: `groq|fallback|langgraph`.

## Extension Readiness Notes
- Extension supports:
  - auto site detect
  - wait-remind loop
  - page-load resume
  - multilingual instruction display
- Backend is not modified by extension operations.

## Known Constraints
- TRACES and CAMS may require manual auth/captcha/otp.
- Extension guides actions; it does not bypass security controls.
