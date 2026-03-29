# Demo Verifier Usage

## Script
- Path: `scripts/demo_verifier.py`

## What it verifies
- `/health` + DB readiness
- `/api/onboard` + `/api/chat`
- `/api/fire` + `/api/tax`
- `/api/portfolio/xray` async poll
- `/api/behavioral/seed`
- `/api/intervention/simulate`
- `/api/arth-score/{user_id}`
- `/api/cams/agent/start` + `/api/jobs/{job_id}`
- `/api/form16/agent/start` + `/api/jobs/{job_id}/user-step`
- `WS /ws/{user_id}` handshake

## Run sequence
1. Start backend:
```bash
source services/backend/.venv/bin/activate
cd services/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. In another terminal run verifier:
```bash
source services/backend/.venv/bin/activate
python scripts/demo_verifier.py http://127.0.0.1:8000
```

3. Expected final line:
```text
=== VERIFIER RESULT ===
PASS
```

## Failure meaning
- Any `[FAIL]` line is integration-blocking for demo.
- Fix that endpoint/infra and rerun until PASS.
