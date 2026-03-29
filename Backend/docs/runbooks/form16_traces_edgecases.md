# Form16/TRACES Assisted Flow Edge Cases (2026)

## Target UX
- User initiates from AstraGuard frontend.
- Backend agent handles portal sequence.
- When OTP/captcha/manual challenge occurs, frontend prompts user and submits via `/api/jobs/{job_id}/user-step`.
- Download/result metadata returns into same job stream.

## State Machine
1. `queued`
2. `running` -> `portal_login_started`
3. `awaiting_user_step` (OTP/captcha)
4. `running` (resume)
5. `complete` or `failed`

## Critical Edge Cases
1. Invalid credentials:
- return `failed` with clear reason and no credential echo.

2. OTP timeout:
- timeout window (300s), then `failed` with retry suggestion.

3. Captcha mismatch:
- stay in `awaiting_user_step`, allow multiple attempts.

4. Role/access mismatch (deductor vs taxpayer views):
- return informative error and fallback upload option.

5. Portal layout drift:
- keep assisted mode default; do not block user from upload path.

## Security
- Username/password only in ephemeral secret store (TTL).
- Never store raw password/OTP in Mongo logs.

## Recommended Frontend
- Dedicated modal for OTP/captcha.
- Retry submission without restarting entire job when possible.
- Keep upload fallback one-click accessible.
