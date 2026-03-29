# AstraGuard - Ankit Masterfile

Last updated: 2026-03-28 (Asia/Kolkata)
Owner: Ankit (Backend + Math)
Purpose: Single source of truth for backend build, integration handoff to Utkarsh, and step-by-step approved execution.

## 1) Operating Rules (Locked)
- We work in strict step approval mode.
- No next step starts until current step is completed and bug-checked.
- Every completed step updates this file.
- Backend is deterministic for all math; LLM is narration/compliance only.
- API contracts are source-of-truth and must stay stable for frontend and AI integration.

## 2) Reality Check - Feasibility Verdict
Status: FEASIBLE with constraints

### What is realistically possible now
- FastAPI deterministic math engines for FIRE, Tax, Portfolio X-Ray.
- AI orchestration handoff via a single bridge (`run_orchestrator` pattern).
- CAMS ingestion with async backend job + polling.
- Upload fallback flow for all document pipelines.
- Behavioral intervention simulation with WhatsApp trigger hooks.

### What needs fallback by design
- External portal automation (CAMS/TRACES/Form16) can fail due to captcha, OTP, latency, or policy changes.
- Therefore each auto-fetch flow must have upload/manual fallback and clear UI state.

## 3) Final Integration Shape (Ankit -> Utkarsh)
Primary rule: Utkarsh should plug in without changing your route contracts.

### You own
- Request validation and response schema enforcement.
- Deterministic computation outputs.
- Audit trail generation and persistence.
- Async job lifecycle and status.
- Error envelope consistency.

### Utkarsh owns
- Intent classification, narration, compliance text polish.
- Behavioral messaging templates.
- Optional life-event reasoning layer.

### Shared contract files (to be created)
- `contracts/schemas.py`
- `contracts/events.py`
- `contracts/errors.py`
- `docs/integration/integration_handoff.md`

## 4) API Contract Baseline (Current)
Primary endpoints committed:
- `POST /api/onboard`
- `POST /api/fire`
- `POST /api/tax`
- `POST /api/portfolio/xray`
- `GET /api/portfolio/xray/{job_id}`
- `POST /api/behavioral/seed`
- `POST /api/intervention/simulate`
- `GET /api/arth-score/{user_id}`
- `GET /health`
- `WS /ws/{user_id}`

Contract rule:
- Always return deterministic numeric core payloads.
- If LLM layer fails, return `narration_unavailable` and keep math payload valid.

## 5) Document Ingestion Strategy (CAMS + Form16/TRACES)
Locked approach:
- Option A: Assisted auto-fetch via backend browser automation job.
- Option B: Secure upload fallback (always available).
- Option B is mandatory for demo reliability and real-world resilience.

Validation monitor ownership:
- Backend deterministic monitor owned by Ankit.
- Optional semantic fallback classifier can be added by Utkarsh later.

Minimum monitor checks:
- File type and magic-bytes check.
- Password/encryption status.
- Parse success and required marker checks.
- Document-type confidence scoring.
- Reject invalid docs with explicit reason.

## 6) Step Plan (Approval Gate)
Step 1: Freeze decisions and contract version (`api_contract_v1`)
Status: completed

Step 2: Scaffold backend structure + config + error envelope
Status: completed

Step 3: FIRE engine + tests + audit trail format
Status: completed

Step 4: Tax engine + tests + slab trace verification
Status: completed

Step 4.5: Research validation pack (Perplexity prompts + intake templates)
Status: completed

Step 4.6: Approve source-backed math spec (`approved_math_spec_v1`)
Status: completed

Step 5: Portfolio X-Ray engine + overlap + tax-aware rebalancing
Status: completed

Step 6: CAMS/Form16 pipeline interfaces + job runner + fallback upload
Status: completed

Step 7: DB integration (`users`, `sessions`, `audit_logs`, `interventions`)
Status: completed

Step 8: Route integration + websocket events + health checks
Status: completed

Step 9: Utkarsh handoff package + integration tests + bug pass
Status: completed

Step 10: Hybrid router implementation (provider-first with fallback)
Status: completed

Step 11: WebSocket live job-progress push (no poll dependency)
Status: completed

Step 12: Agent Lab WS-first live timeline UI
Status: completed

Step 13: CAMS authenticity gate (no false-positive complete)
Status: completed

## 7) Bugs and Risks Tracker
- R-001: Tax rules vary by FY updates; must pin exact FY in engine config.
- R-002: CAMS/TRACES automation instability; must keep upload fallback first-class.
- R-003: Numeric mismatch between docs can break trust; enforce test vectors.
- R-004: Secrets exposure risk if credentials are committed in markdown/code.

## 8) Improvement Backlog (Live)
- Add canonical `ErrorResponse` schema for all endpoints.
- Add idempotency key for async portfolio jobs.
- Add structured event log IDs across API + audit logs.
- Add golden test fixtures for judge scenarios.
- Add contract tests to ensure frontend-safe payload stability.
- Add hybrid CAS provider adapter with routed fallback chain.

## 9) Handoff Requirements for Utkarsh
- Stable schema docs and typed models.
- Sample request/response JSON for each endpoint.
- AI bridge interface with no business logic leakage.
- Failure matrix and fallback behavior documentation.

## 10) Change Log
- 2026-03-28: Created masterfile, locked workflow, feasibility verdict, step-gated plan, risk tracker, and integration ownership boundaries.
- 2026-03-28: Step 1 completed with approved decisions:
  - DB: MongoDB + Redis
  - Endpoint aliases: both supported (`/api/onboard` and `/api/chat`)
  - Document strategy: assisted auto-fetch + upload fallback
  - Contract ownership: backend schema is source-of-truth for Utkarsh integration
- 2026-03-28: Step 2 completed:
  - Backend scaffold created under `services/backend/app`
  - Canonical error envelope helper added
  - Unified async job API scaffold added (`/api/jobs`, `/api/jobs/{job_id}`, `/api/jobs/{job_id}/user-step`)
  - Onboard alias routes scaffolded (`/api/onboard` and `/api/chat`)
  - Deterministic document monitor scaffold added
  - Contract baseline doc created (`docs/integration/api_contract_v1.md`)
  - Initial contract sanity test added
- 2026-03-28: Step 3 completed:
  - Deterministic FIRE engine added (`services/backend/app/engines/fire_engine.py`)
  - FIRE endpoint connected (`POST /api/fire`)
  - Audit trail emitted from engine output
  - Test packaging bug fixed (tests not discovered) by adding `__init__.py` files
  - `unittest` suite passing for FIRE engine behavior
- 2026-03-28: Step 4 completed:
  - Deterministic Tax engine added (`services/backend/app/engines/tax_engine.py`)
  - Tax endpoint connected (`POST /api/tax`)
  - Tax unit tests added (`tests/unit/test_tax_engine_unittest.py`)
  - Bug fixed: Infinity slab label formatting crash
  - Contract alignment fix: old regime slab behavior set to match provided expected judge output
  - Full unittest suite pass (FIRE + Tax)
- 2026-03-28: Step 4.5 completed:
  - Added Perplexity prompt pack (`docs/research/perplexity_prompt_pack_v1.md`)
  - Added approved spec template (`docs/research/approved_math_spec_v1.md`)
  - Added research intake checklist (`docs/research/research_intake_checklist.md`)
  - Next gate: run prompts, paste raw outputs, then freeze formulas in Step 4.6
- 2026-03-28: Step 4.6 started:
  - Added raw research intake files for FIRE/Tax/Portfolio
  - Added intake status tracker in `approved_math_spec_v1.md`
  - Waiting on Perplexity raw outputs before formula freeze and engine refactor
- 2026-03-28: Step 4.6 completed:
  - Ingested FIRE/Tax/Portfolio raw research outputs
  - Finalized approved formula spec (`docs/research/approved_math_spec_v1.md`)
  - Refactor completed: FIRE engine supports configurable `safe_withdrawal_rate`
  - Refactor completed: Tax engine supports `tax_profile` switch (`contract_demo` / `research_standard`)
  - Full compile and unittest pass after refactor
- 2026-03-28: Step 5 completed:
  - Implemented Portfolio X-Ray deterministic engine (`services/backend/app/engines/portfolio_engine.py`)
  - Added async xray endpoints (`POST /api/portfolio/xray`, `GET /api/portfolio/xray/{job_id}`)
  - Reused shared in-memory job registry across job routes and portfolio routes
  - Added portfolio unit tests (`tests/unit/test_portfolio_engine_unittest.py`)
  - Full test suite pass (9 tests)
- 2026-03-28: Step 6 completed:
  - Upgraded document monitor with PDF signature validation and deterministic marker classification
  - Added CAMS pipeline interface scaffold (`services/backend/app/pipelines/cams_pipeline.py`)
  - Added Form16 pipeline interface scaffold (`services/backend/app/pipelines/form16_pipeline.py`)
  - Added document validation endpoint (`POST /api/documents/validate`)
  - Added portal feasibility runbook with official links (`docs/runbooks/portal_feasibility_and_background_agents.md`)
  - Full test suite pass (12 tests)
- 2026-03-28: Step 7 completed:
  - Added MongoDB + Redis manager (`services/backend/app/core/database.py`)
  - Added repositories for `users`, `sessions`, `audit_logs`, `interventions`
  - Added audit persistence service and `GET /api/audit/{calculation_id}` endpoint
  - Wired onboarding/fire/tax/portfolio routes to persist to DB when configured
  - Updated health endpoint with DB readiness flags
  - Added beginner setup guide for MongoDB + Redis
  - Full test suite pass (12 tests)
- 2026-03-28: Step 8 completed:
  - Added behavioral routes: `/api/behavioral/seed`, `/api/intervention/simulate`
  - Added Arth Score route: `GET /api/arth-score/{user_id}`
  - Added WebSocket route: `WS /ws/{user_id}` with connection manager
  - Updated health check to include `atlas_configured` flag
  - Added Arth Score service + tests
  - Full test suite pass (14 tests)
- 2026-03-28: Environment integration update:
  - Added Atlas and Redis Cloud credentials to root `.env` and `services/backend/.env`
  - Runtime config load check attempted; blocked due missing local dependency `pydantic_settings`
  - Next action: install backend dependencies and verify `/health` shows `mongo_ready=true`, `redis_ready=true`, `atlas_configured=true`
- 2026-03-28: Step 9 completed:
  - Added AI bridge protocol for Utkarsh integration (`services/backend/app/services/ai_bridge.py`)
  - Added handoff docs:
    - `docs/integration/integration_handoff.md`
    - `docs/integration/failure_matrix.md`
    - `docs/integration/utkarsh_env_contract.md`
  - Added shared contract files:
    - `packages/contracts/python/schemas.py`
    - `packages/contracts/python/events.py`
    - `packages/contracts/python/errors.py`
  - Added contract test for required error codes
  - Final compile + unittest bug pass complete (15 tests)
- 2026-03-28: Post-step bug fix:
  - Fixed `/api/audit/{calculation_id}` JSON serialization issue for Mongo `ObjectId`
  - Added safe response serializer in `routes_audit.py`
  - Re-ran compile + unittest pass (15 tests)
- 2026-03-28: Agent hardening upgrade:
  - Added secure ephemeral secret store for portal credentials (`services/backend/app/services/secret_store.py`)
  - Added interactive user-step service for OTP/captcha continuation (`services/backend/app/services/interactive_step_service.py`)
  - Added background task runner (`services/backend/app/services/background_runner.py`)
  - Added CAMS background agent (`services/backend/app/pipelines/cams_agent.py`)
  - Added Form16 assisted background agent (`services/backend/app/pipelines/form16_agent.py`)
  - Added ingestion start routes (`POST /api/cams/agent/start`, `POST /api/form16/agent/start`)
  - Wired job user-step endpoint to unblock assisted flows
  - Full unittest pass (17 tests)
- 2026-03-28: Agent hardening v2 (real-mode robustness):
  - CAMS real-mode hardened with retry loop, selector fallbacks, and challenge detection (`awaiting_user_step`)
  - Deprecated UTC calls replaced with timezone-aware timestamps in ingestion agents
  - Added runbooks:
    - `docs/runbooks/cams_real_flow_edgecases.md`
    - `docs/runbooks/form16_traces_edgecases.md`
  - Added unified ingestion state machine spec (`docs/integration/ingestion_state_machine.md`)
  - Re-ran full compile + unittest pass (17 tests)
- 2026-03-28: Agent Lab execution harness:
  - Added temporary frontend harness (`tools/agent_lab/index.html`)
  - Added backend route to serve harness (`GET /agent-lab`)
  - Mounted `/artifacts` static path for CAMS real-mode evidence screenshots
  - CAMS agent now returns evidence block (`visited_url`, `steps`, `screenshots`) for real-mode verification
- 2026-03-28: CAMS auto-ingest upgrade:
  - Added mailbox ingestion service (`services/backend/app/services/mailbox_ingestion.py`)
  - CAMS agent can now auto-poll mailbox and attach CAS PDF metadata to job result
  - Added optional CAMS start payload fields:
    - `auto_ingest_mailbox`
    - `mailbox_app_password`
    - `imap_host`, `imap_port`
  - Agent Lab updated with mailbox auto-ingest controls
  - Added monitor test for expected-type filename hint
  - Full compile + unittest pass (18 tests)
- 2026-03-28: Runtime dependency installation:
  - Installed Playwright package in backend venv
  - Installed Chromium browser runtime for Playwright
  - Verified import check output: `playwright_ok`
- 2026-03-28: CAMS real-mode bugfix (live):
  - Fixed navigation crash in CAMS agent: `Frame.goto() missing 1 required positional argument: 'url'`
  - Switched to browser-context page creation (`context.new_page()`) and added `_safe_goto()` fallback wrapper
  - Added traceback capture in job error payload for faster diagnostics via `/api/jobs/{job_id}`
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS URL normalization fix (live):
  - Fixed `Invalid CAMS URL provided for navigation` when `cams_url` is omitted/null
  - CAMS agent now normalizes and defaults URL safely to `https://www.camsonline.com/Investors/MailbackServices`
  - Ingestion route now omits `cams_url` from payload unless explicitly provided
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS selector hardening fix (live):
  - Fixed PAN/email field targeting bug where `get_by_label()` matched non-input `<div>` elements
  - Replaced loose label fallback with input-only deterministic matching by `name/id/placeholder/aria-label/type`
  - Added editable-input guard to avoid hidden/button/readonly-like elements
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS real-flow robustness v3 (live):
  - Added frame-aware input handling (search/fill across page + iframes)
  - Added overlay dismissal for common cookie/consent popups before form interaction
  - Added guided click-through to CAS/Mailback sections when landing page does not directly expose PAN/email form
  - Submit action is now frame-aware as well
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS real-flow robustness v4 (live):
  - Added candidate URL chain fallback (`MailbackServices`, `Statements`, `Investors`) across retry attempts
  - Added desktop viewport context to avoid mobile/condensed layouts hiding controls
  - Added per-attempt HTML dump artifact for DOM-level diagnosis
  - Added heuristic PAN/email input detection when explicit markers are unavailable
  - Added extra navigation labels (`Consolidated Account Statement`, `Mailback Services`, `Request Statement`)
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS marker-check fix (live):
  - Fixed false-negative form detection by allowing PAN and Email markers across different frames/targets
  - Moved screenshot + HTML artifact dump before form-marker validation so failures always leave evidence
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: Hybrid CAS strategy freeze (approved):
  - Added `docs/integration/hybrid_cas_strategy_v1.md`
  - Locked architecture: provider-first + assisted Playwright + upload fallback
  - Defined runtime routing contract (`provider_mode`, `priority`) and unified job result envelope
  - Defined explicit ownership split for Devraj (UI) and Utkarsh (AI status narration)
- 2026-03-28: Step 10 completed (hybrid router implementation):
  - Added provider adapter stub service (`services/backend/app/services/cas_provider.py`)
  - Added CAMS request controls in ingestion API: `provider_mode`, `priority`
  - Added payload propagation for `user_id` and routing metadata
  - Wired CAMS agent provider-first execution path with graceful fallback:
    - `auto`: provider -> Playwright
    - `provider_only`: provider only, no Playwright fallback
    - `playwright_only`: skip provider path
  - Added provider config keys to `.env.example`
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS live portal blocker fix (disclaimer gate):
  - Root cause found from HTML artifacts: CAMS Disclaimer modal blocked navigation to statement form
  - Added explicit disclaimer acceptance flow: select `ACCEPT` + click `PROCEED`
  - Added direct text navigation to `CAS - CAMS+KFintech` tiles before role-based fallbacks
  - Added re-check disclaimer handling after navigation clicks
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS disclaimer stacking fix (live):
  - Root cause found: multiple `mat-dialog` disclaimer overlays can stack (`mat-dialog-0`, `mat-dialog-1`, ...)
  - Replaced single-pass disclaimer handler with looped modal-clear routine (`max_rounds`)
  - Added force-check/force-click for Angular hidden radio/button controls in modal
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS direct-route navigation hardening (live):
  - Added direct candidate routes:
    - `/Investors/Statements/Consolidated-Account-Statement`
    - `/Investors/Statements/CAS-CAMS`
  - Added explicit direct-route goto phase before click-based navigation
  - Added final href extraction fallback (`a[href*='Consolidated-Account-Statement']`)
  - Added second disclaimer-clear pass right before form-marker detection
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: CAMS graceful-assist mode upgrade (live):
  - Replaced hard terminal failure on marker-miss with `awaiting_user_step`
  - Job now returns guided assist payload (direct links + instruction + evidence + last_error)
  - Secrets are preserved while job is in `awaiting_user_step` (not purged in `finally`)
  - Updated `/api/jobs/{job_id}/user-step` behavior for CAMS:
    - acknowledges step
    - keeps status in `awaiting_user_step`
    - guides to upload/manual completion rather than fake `running` state
  - Validation pass: compile OK + root unittest suite passing (`18/18`)
- 2026-03-28: Step 11 completed (real-time job updates):
  - Added job-service listener hook in `InMemoryJobService` (`set_listener`)
  - Emitted listener callbacks on both `create_job` and `update_job`
  - Added websocket publisher `publish_job_update` in `websocket_service.py`
  - Wired listener at app startup (`job_service -> ws_manager.publish_job_update`)
  - Cleared listener on shutdown
  - Updated integration handoff doc with `job_update` event contract
  - Added unit test: `tests/unit/test_job_service_listener_unittest.py`
  - Validation pass: compile OK + full test suite pass (`19/19`)
- 2026-03-28: WebSocket runtime fix:
  - Root cause diagnosed for browser WS handshake failure: missing websocket protocol dependency in backend venv
  - Installed `websockets==12.0` and pinned it in `services/backend/requirements.txt`
  - Result: WS route can now negotiate browser websocket connections on uvicorn
- 2026-03-28: Step 12 completed (Agent Lab live UI):
  - Refactored `tools/agent_lab/index.html` to WS-first model
  - Added real-time job timeline panels for CAMS and Form16 cards
  - Added `job_update` event handling and job-to-widget watcher map
  - Kept polling as fallback only when WS is unavailable/disconnected
  - Added evidence/screenshot rendering in separate panel
  - Validation: backend py_compile OK + runtime markers verified
- 2026-03-28: Step 13 completed (authenticity enforcement):
  - Added strict post-submit authenticity assessment in CAMS agent:
    - `confirmed` only when deterministic success markers are detected
    - `rejected` when explicit failure markers detected
    - `unverified` when neither is present
  - Added submitted-page HTML evidence dump (`*_submitted.html`)
  - Removed false-positive completion behavior:
    - no `COMPLETE` on mere submission attempt
    - `AWAITING_USER_STEP` used when authenticity is unverified/rejected
  - Mailbox wait edge-cases now remain actionable instead of closed:
    - missing app password -> `AWAITING_USER_STEP`
    - timeout waiting CAS email -> `AWAITING_USER_STEP`
  - `COMPLETE` reserved for verified terminal outcomes (e.g., validated CAS auto-ingest)
  - Validation pass: compile OK + full test suite pass (`19/19`)

## 11) Step 1 - Decision Freeze (Locked)
1. Database: MongoDB for primary persistence + Redis for cache/queues/rate-limit.
2. Endpoint aliases: support both `/api/onboard` and `/api/chat`.
3. Docs ingestion mode: Assisted auto-fetch (beta) + upload fallback (stable).
4. Handoff governance: Backend JSON contracts are canonical and versioned.

## 12) CAMS and Form16 Agent Blueprint (Realistic)
### CAMS
- Input (frontend): PAN, registered email, statement period, consent.
- Backend starts async job and returns `job_id`.
- Worker (Playwright) submits CAMS mailback request.
- Job state model:
  - `queued`
  - `submitting_request`
  - `request_accepted`
  - `awaiting_document`
  - `downloaded` (if automated mailbox path enabled)
  - `parsed`
  - `failed`
- If not retrieved within SLA timeout, auto-switch to upload fallback with retained job context.

### Form16 / TRACES
- Input (frontend): user chooses `assisted_fetch` or `upload_pdf`.
- Assisted fetch is stateful and may require user-in-loop steps (OTP/captcha/manual auth).
- Job state model:
  - `queued`
  - `portal_login_started`
  - `awaiting_user_step` (OTP/captcha/manual)
  - `downloaded`
  - `parsed`
  - `failed`
- If portal automation fails or user aborts, upload fallback is offered immediately.

### Security + Compliance Constraints
- Credentials are never persisted to MongoDB.
- Credentials only kept in encrypted in-memory job context with short TTL.
- Audit log stores only metadata (no password, no raw OTP).
- All parsed artifacts are document-classified before downstream processing.

## 13) Portal Feasibility Decision
### CAMS/KFin CAS
- Strongly feasible using official mailback request flow.
- Preferred implementation: submit CAS request and process received PDF (auto mailbox path or user upload path).
- Official ecosystem references include AMFI Anytime e-CAS and KFin CAS service links.

### MF Central
- Feasible for user-facing retrieval but requires user registration/login.
- Better as user-guided channel than full unattended backend automation.

### TRACES/Form16
- Feasible only in assisted mode due login complexity (and potential OTP/captcha/KYC process).
- Must keep upload fallback as primary reliability path for demo.

### Document Monitor Protocol (Deterministic)
- Validate MIME + magic bytes.
- Validate extension and page count bounds.
- Parse text and detect required markers:
  - CAMS: folio/AMC/transaction structures.
  - Form16: PAN/TAN/Part A/Part B + FY markers.
- Produce confidence score and rejection reason on failure.

## 14) 2026-03-28 Live Upgrade: Two-Site Agent Hardening (CAMS + Form16)
- Added Groq-backed step advisor service:
  - File: `services/backend/app/services/groq_step_advisor.py`
  - Purpose: generate one concrete "next best step" when automation gets blocked.
  - Safe fallback: deterministic instruction if Groq key unavailable/fails.
- Added new backend config for advisor:
  - `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`, `GROQ_TIMEOUT_SECONDS`
- Integrated advisor into CAMS agent (`services/backend/app/pipelines/cams_agent.py`) for:
  - Playwright unavailable/degraded mode
  - verification challenge detected
  - authenticity unverified after submit
  - full navigation marker-miss after retries
  - Each of these now returns `result.ai_next_step` for frontend guidance.
- Integrated advisor into Form16 agent (`services/backend/app/pipelines/form16_agent.py`) for:
  - initial `awaiting_user_step` challenge phase
  - terminal failures with guided recovery action
- Extended Form16 start payload:
  - `portal_url` supported in `POST /api/form16/agent/start` (default TRACES URL)
- Handoff docs updated for Utkarsh:
  - `docs/integration/api_contract_v1.md`
  - `docs/integration/utkarsh_env_contract.md`
- Security cleanup for handoff:
  - Sanitized root `.env.example` to remove hardcoded secrets and switched to placeholders.
- Validation run:
  - `py_compile` passed for updated files.
  - Could not run pytest in local venv because `pytest` package is not installed in that environment.

## 15) 2026-03-28 Extension Track Started (Non-Breaking)
- Added isolated Chrome extension module (no backend route changes):
  - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension/manifest.json`
  - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension/popup.html`
  - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension/popup.js`
  - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension/content.js`
  - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension/styles.css`
  - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension/README.md`
- Scope implemented:
  - Proactive on-page tutorial overlay for CAMS and TRACES/Form16.
  - Step highlighting, manual next/stop, auto-progress hooks on click/input.
  - Optional live backend WS job-status display in overlay (`/ws/{user_id}`).
- Safety objective met:
  - Existing backend ingestion flow remains untouched and operational.

## 16) 2026-03-28 Target Lock Finalized (KFin CAS + TRACES)
- Extension target hosts locked to:
  - `mfs.kfintech.com` (CAS)
  - `*.tdscpc.gov.in` (TRACES/Form16)
- Updated extension manifest host permissions and match patterns accordingly.
- Replaced generic CAMS step pack with KFin CAS-specific step pack:
  - statement type selection
  - PAN
  - email
  - CAS password + confirm
  - submit
- Hardened TRACES pack with login/captcha/download-oriented selectors.
- Added strict host guardrails in content script:
  - KFin guide only starts on KFin host
  - Form16 guide only starts on TRACES host
- Updated extension docs and popup labels to reflect locked targets.
- Validation run: JS syntax checks passed for content/popup scripts.

## 17) 2026-03-28 Extension UX + TRACES Hardening
- Improved TRACES step guidance with stronger target matching:
  - login selector expansion
  - explicit downloads/form16 navigation step
  - request/status/download follow-up step
  - text-token scoring and visibility filtering to avoid wrong-click targets
- Added guide persistence + auto-resume:
  - extension saves active guide state in `chrome.storage.local`
  - on new page load/navigation, guide resumes at previous step for same target host
- Added URL watcher during active guide to re-render guidance after route/page changes.
- Added multi-language option in popup:
  - English (default), Hinglish, Hindi
- UI polish:
  - improved popup theme and controls
  - refined overlay styling
- Files updated:
  - `tools/chrome_guide_extension/content.js`
  - `tools/chrome_guide_extension/popup.html`
  - `tools/chrome_guide_extension/popup.js`
  - `tools/chrome_guide_extension/styles.css`
  - `tools/chrome_guide_extension/README.md`

## 18) 2026-03-28 TRACES Start/Injection Reliability Fix
- Fixed popup false-positive start state:
  - `popup.js` now marks started only if content message delivery succeeds.
  - Previously it could show “Started” even when no content script receiver existed.
- Added guide type auto-detection by active tab URL:
  - `auto -> cams` on `kfintech.com`
  - `auto -> form16` on `tdscpc.gov.in`
- Added content-level support for `guideType=auto`.
- Expanded extension URL match/permissions for TRACES/KFin:
  - added both `http` and `https` patterns
  - includes wildcard TRACES subdomains.
- Added full step-instruction multilingual mapping for Hindi/Hinglish.
- Validation run:
  - JS syntax checks passed for `content.js` and `popup.js`.

## 19) 2026-03-28 Hotfix: Auto Start on Already-Open TRACES/KFin Tabs
- Root issue fixed: popup could report start while content script was not attached on current tab context.
- Added content readiness handshake:
  - `ASTRA_PING` check from popup to content script.
  - If missing, popup now force-injects `content.js` + `styles.css` via `chrome.scripting`.
  - Start proceeds only after successful handshake.
- Improved TRACES login target detection:
  - Added left-panel/login-specific selectors.
  - Added scoring bonus for `id/class` containing `login`.
- Result:
  - Auto-by-site now works reliably even when target page was already open before clicking Start.

## 20) 2026-03-28 TRACES Flow Alignment to UI (Requested)
- Form16 guide sequence updated to match TRACES homepage UX:
  1. click top `Tax Payer`
  2. click left-side `Login`
  3. enter user/pan
  4. enter password
  5. captcha/otp
  6. downloads/form16 request-download path
- Added multilingual entries for new `Tax Payer` step.
- Validation: JS syntax check passed (`content.js`).

## 21) 2026-03-28 Action-Wait Reminder Loop (Stability Upgrade)
- Added per-step wait mode:
  - after highlighting a target, guide now waits for required click/input.
  - does not auto-skip silently.
- Added periodic reminders (every ~7s) while waiting:
  - overlay reiterates exact instruction + waiting duration.
  - highlighted target is brought back into view and tooltip refreshed.
- Advance logic:
  - on required user action, reminder loop stops and guide moves to next step.
  - on manual `Next`, `Stop`, or URL/page change, reminder loop is safely cleared.
- Goal achieved:
  - extension keeps guiding continuously and reduces “silent stop” behavior.

## 22) 2026-03-28 Form16 Progress-Control Fix (No Premature Skip)
- Added singleton guard to avoid duplicate script instances (`window.__astraGuideLoaded`).
- Added anti-double-advance throttle in `nextStep()` to stop accidental multi-skip.
- Input progression changed from immediate-first-keystroke to completion-aware:
  - waits for blur/change or ~1s typing idle window
  - validates minimum length before advancing
  - mode-specific checks:
    - PAN strict format validation
    - Email shape validation
    - Password/OTP generic minimum length checks
- Result:
  - after `Tax Payer` click, guide reliably moves to `Login` step
  - typing in fields no longer jumps to next step on first character

## 23) 2026-03-28 Final Readiness Audit + Handoff Pack
- Performed live backend smoke verification on local server:
  - `onboard`, `chat`, `fire`, `tax`, `behavioral/seed`, `intervention/simulate`, `arth-score` -> success path verified
  - CAMS mock agent -> complete
  - Form16 assisted flow + user-step -> complete
  - Portfolio route caveat confirmed: mock mode needs at least one fund input
- Current infra status during audit:
  - MongoDB ready
  - Redis not ready (connection reset); app still serves core APIs
- Extension verification completed:
  - JS syntax checks for `content.js` and `popup.js`
  - manifest validation passed (MV3 + expected match patterns)
- Added final integration docs:
  - `docs/integration/handoff_devraj_uttu_final.md`
  - `docs/integration/frontend_agent_extension_linking.md`

## 24) 2026-03-28 Final Non-Break Regression Check
- Ran backend server and executed live endpoint traffic; server logs confirm 200 responses across:
  - `/health`
  - `/api/onboard`, `/api/chat`
  - `/api/fire`, `/api/tax`
  - `/api/portfolio/xray` + poll
  - `/api/behavioral/seed`, `/api/intervention/simulate`
  - `/api/cams/agent/start`, `/api/form16/agent/start`, `/api/jobs/{id}`, `/api/jobs/{id}/user-step`
- Verified extension build integrity:
  - `content.js` syntax OK
  - `popup.js` syntax OK
  - `manifest.json` valid and match patterns present
- No backend route contract was changed by extension work (extension remains isolated in `tools/chrome_guide_extension`).

## 25) 2026-03-28 Final Full E2E Pass (Start -> End)
- Executed full final smoke sequence with valid payloads:
  - onboarding + chat alias
  - fire + tax calculations
  - portfolio xray with valid funds
  - behavioral seed + intervention simulate + arth score
  - CAMS mock async job to completion
  - Form16 assisted async job to completion via user-step OTP
  - WebSocket handshake event verified (`connected`)
- Infra state during final pass:
  - `mongo_ready=true`
  - `redis_ready=true`
  - `atlas_configured=true`
- Added final integration contract/checklist doc:
  - `docs/integration/final_e2e_validation_and_contract.md`

## 26) 2026-03-28 One-Command Demo Verifier Added
- Added executable verifier script:
  - `scripts/demo_verifier.py`
- Purpose:
  - repeatable end-to-end integration validation before demo/handoff
  - checks backend APIs, async jobs, and websocket handshake
- Live run result:
  - `VERIFIER RESULT = PASS`
- Added usage doc:
  - `docs/integration/verifier_usage.md`
