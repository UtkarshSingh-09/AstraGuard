# Portal Feasibility and Background Agent Strategy

Date: 2026-03-28  
Scope: CAMS/CAS, MF Central, TRACES/Form16

## Decision Summary
- CAMS/CAS background agent: feasible in assisted mode with async jobs.
- MF Central: feasible as user-guided channel; do not rely on full unattended automation first.
- TRACES/Form16: feasible only as assisted fetch + upload fallback for reliability.

## What We Will Build
1. Background job orchestration for assisted fetch.
2. User-step continuation (`OTP/captcha/manual`) via API.
3. Upload fallback always available.
4. Deterministic document monitor before parser.

## Why This Is Realistic
- Mutual fund ecosystem supports consolidated statement flows and central investor service channels.
- TRACES supports Form16 view/download capabilities but operational flow depends on login/challenges and user context.
- Therefore, production-safe approach is assisted automation + fallback, not hard dependency on unattended crawling.

## Source Notes
- AMFI investor center references industry eCAS channels and investor services:
  - https://www.amfiindia.com/investor-corner/online-centre-for-investors
- MF Central investor sign-in channel:
  - https://app.mfcentral.com/investor/signin
- TRACES official portal capabilities include view/download of Form16 and other TDS forms:
  - https://nriservices.tdscpc.gov.in/en/home.html

## Implementation Constraints
- Do not persist portal passwords in database.
- Keep credentials in short-lived job context only.
- Store only metadata in audit logs.
- If auto-fetch stalls or fails, prompt upload path immediately.
