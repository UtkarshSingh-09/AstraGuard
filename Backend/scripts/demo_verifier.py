#!/usr/bin/env python3
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
USER_ID = "usr_verifier_001"


def post(path, payload, timeout=25):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get(path, timeout=25):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ok(label, cond, details=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}{' :: ' + details if details else ''}")
    return cond


async def ws_check(base_url, user_id):
    try:
        import websockets
    except Exception as e:
        return False, f"websockets module missing: {e}"

    uri = base_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws/{user_id}"
    try:
        async with websockets.connect(uri, open_timeout=6) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=6)
            return True, msg
    except Exception as e:
        return False, str(e)


def main():
    print(f"Running AstraGuard verifier against: {BASE}")
    all_ok = True

    try:
        health = get("/health")
        all_ok &= ok("health.status", health.get("status") == "ok", str(health))
        db = health.get("db", {})
        all_ok &= ok("health.mongo_ready", db.get("mongo_ready") is True)
        all_ok &= ok("health.redis_ready", db.get("redis_ready") is True, db.get("redis_error", ""))
    except Exception as e:
        ok("health", False, str(e))
        return 1

    onboard = post(
        "/api/onboard",
        {
            "session_id": "sess_verifier_1",
            "conversation_history": [{"role": "user", "content": "I am 28 and earn 18 lakh"}],
            "extraction_complete": False,
            "user_id": USER_ID,
        },
    )
    all_ok &= ok("onboard", onboard.get("status") in {"gathering", "complete"}, onboard.get("status", ""))

    chat = post(
        "/api/chat",
        {
            "session_id": "sess_verifier_1",
            "conversation_history": [{"role": "user", "content": "continue"}],
            "extraction_complete": False,
            "user_id": USER_ID,
        },
    )
    all_ok &= ok("chat_alias", chat.get("status") in {"gathering", "complete"}, chat.get("status", ""))

    fire = post(
        "/api/fire",
        {
            "user_id": USER_ID,
            "inputs": {
                "age": 34,
                "annual_salary": 2400000,
                "monthly_expenses": 80000,
                "existing_mf": 1800000,
                "existing_ppf": 600000,
                "existing_epf": 200000,
                "monthly_sip_current": 20000,
                "target_monthly_draw": 150000,
                "target_retire_age": 50,
                "inflation_rate": 0.06,
                "equity_return": 0.12,
                "debt_return": 0.07,
            },
        },
    )
    all_ok &= ok("fire", fire.get("status") == "success", fire.get("status", ""))
    all_ok &= ok("fire.calculation_id", bool(fire.get("calculation_id")))

    tax = post(
        "/api/tax",
        {
            "user_id": USER_ID,
            "inputs": {
                "base_salary": 1800000,
                "hra_received": 360000,
                "rent_paid_monthly": 0,
                "city_type": "metro",
                "investments_80c": 150000,
                "nps_80ccd1b": 50000,
                "home_loan_interest_24b": 40000,
                "health_insurance_80d_self": 0,
                "health_insurance_80d_parents": 0,
                "lta_exemption": 0,
                "other_income": 0,
                "financial_year": "2026-27",
            },
        },
    )
    all_ok &= ok("tax", tax.get("status") == "success", tax.get("status", ""))
    all_ok &= ok("tax.calculation_id", bool(tax.get("calculation_id")))

    portfolio_inputs = {
        "as_of_date": "2026-03-28",
        "funds": [
            {
                "name": "Axis Bluechip Fund",
                "isin": "INF846K01EW2",
                "invested": 300000,
                "current_value": 387000,
                "transactions": [{"date": "2021-01-01", "amount": -100000, "type": "BUY"}],
                "plan_type": "DIRECT",
                "expense_ratio": 0.44,
                "holdings": [{"stock": "Reliance Industries", "weight": 8.2}],
            }
        ],
    }
    px = post("/api/portfolio/xray", {"user_id": USER_ID, "mode": "mock", "inputs": portfolio_inputs})
    px_id = px.get("job_id")
    all_ok &= ok("portfolio.start", px.get("status") == "processing", str(px))
    all_ok &= ok("portfolio.job_id", bool(px_id))
    px_poll = get(f"/api/portfolio/xray/{px_id}") if px_id else {}
    all_ok &= ok("portfolio.poll", px_poll.get("status") == "complete", px_poll.get("status", ""))

    seed = post(
        "/api/behavioral/seed",
        {
            "user_id": USER_ID,
            "update_type": "self_reported",
            "data": {
                "panic_threshold": -17.0,
                "behavior_type": "panic_prone",
                "last_panic_event": "COVID 2020",
                "behavioral_discipline_score": 55,
            },
        },
    )
    all_ok &= ok("behavioral.seed", seed.get("status") == "updated", seed.get("status", ""))

    sim = post(
        "/api/intervention/simulate",
        {"user_id": USER_ID, "market_drop_pct": 7.2, "send_whatsapp": False, "send_push": False},
    )
    all_ok &= ok("intervention.simulate", "risk_state" in sim)

    arth = get(f"/api/arth-score/{USER_ID}")
    all_ok &= ok("arth.score", bool(arth.get("arth_score")))

    cams = post(
        "/api/cams/agent/start",
        {"user_id": USER_ID, "pan": "ABCDE1234F", "email": "demo@example.com", "mode": "mock"},
    )
    cams_id = cams.get("job_id")
    all_ok &= ok("cams.start", cams.get("status") == "processing", str(cams))
    all_ok &= ok("cams.job_id", bool(cams_id))
    cams_state = {}
    for _ in range(6):
        time.sleep(0.7)
        cams_state = get(f"/api/jobs/{cams_id}")
        if cams_state.get("job_status") == "complete":
            break
    all_ok &= ok("cams.complete", cams_state.get("job_status") == "complete", cams_state.get("job_status", ""))

    form = post(
        "/api/form16/agent/start",
        {
            "user_id": USER_ID,
            "username": "demo_user",
            "password": "demo_pass",
            "mode": "assisted",
            "portal_url": "https://www.tdscpc.gov.in/",
        },
    )
    form_id = form.get("job_id")
    all_ok &= ok("form16.start", form.get("status") == "processing", str(form))
    all_ok &= ok("form16.job_id", bool(form_id))
    form_state = {}
    for _ in range(8):
        time.sleep(0.6)
        form_state = get(f"/api/jobs/{form_id}")
        if form_state.get("job_status") == "awaiting_user_step":
            post(f"/api/jobs/{form_id}/user-step", {"step_type": "otp", "value": "123456"})
        if form_state.get("job_status") == "complete":
            break
    form_state = get(f"/api/jobs/{form_id}")
    all_ok &= ok("form16.complete", form_state.get("job_status") == "complete", form_state.get("job_status", ""))

    ws_ok, ws_detail = asyncio.run(ws_check(BASE, USER_ID))
    all_ok &= ok("websocket.connected", ws_ok, ws_detail)

    print("\n=== VERIFIER RESULT ===")
    print("PASS" if all_ok else "FAIL")
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
