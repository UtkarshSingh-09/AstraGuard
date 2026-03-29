# CAMS Real Flow Edge Cases (2026)

## Target UX
- User stays on AstraGuard frontend.
- Inputs PAN + registered email.
- Backend agent navigates CAMS flow.
- If challenge appears, frontend asks user and resumes.
- No credential persistence in DB.

## State Machine
1. `queued`
2. `running` -> `submitting_request`
3. `awaiting_user_step` (if verification/captcha gate appears)
4. `running` (resume)
5. `complete` (request accepted) or `failed`

## Critical Edge Cases
1. Selector drift on CAMS page:
- Mitigation: multi-selector strategy (`name/id/placeholder/label`).

2. Captcha/verification gate:
- Mitigation: mark job `awaiting_user_step`, ask user to complete challenge, resume.

3. Mailback accepted but document delayed:
- Mitigation: mark `processing` with explicit next step: upload received CAS PDF fallback.

4. Portal timeout/network failure:
- Mitigation: retry with exponential backoff (`max_attempts`).

5. Missing PAN/email:
- Mitigation: fail fast with `cams_fetch_failed`.

## Security
- PAN/email kept in ephemeral secret store (TTL).
- No secrets written to Mongo collections.

## Recommended Frontend
- Job progress timeline UI.
- “Resume Verification” CTA when status is `awaiting_user_step`.
- “Upload CAS Instead” fallback CTA always visible.
