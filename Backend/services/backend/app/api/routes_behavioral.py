from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.errors import error_response
from app.repositories.interventions_repo import InterventionsRepository
from app.repositories.users_repo import UsersRepository
from app.services.websocket_service import ws_manager

from agents.orchestrator import run_orchestrator

router = APIRouter(prefix="/api", tags=["behavioral"])
users_repo = UsersRepository()
interventions_repo = InterventionsRepository()


class BehavioralSeedRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    update_type: str = "self_reported"
    data: dict


class InterventionSimulateRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    market_drop_pct: float
    send_whatsapp: bool = False
    send_push: bool = True


@router.post("/behavioral/seed")
async def behavioral_seed(request: BehavioralSeedRequest):
    user = await users_repo.get_user(request.user_id) or {}
    old_score = int((user.get("behavioral_dna", {}) or {}).get("behavioral_discipline_score", 50))
    merged = {**(user.get("behavioral_dna", {}) or {}), **request.data}
    await users_repo.update_behavioral_dna(request.user_id, merged)
    new_score = int(merged.get("behavioral_discipline_score", old_score))
    return {
        "status": "updated",
        "behavioral_dna": merged,
        "arth_score_change": {"from": old_score, "to": new_score, "reason": "Behavioral profile updated"},
    }


@router.post("/intervention/simulate")
async def intervention_simulate(request: InterventionSimulateRequest):
    user = await users_repo.get_user(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=error_response("user_not_found", "User not found"))

    behavioral = user.get("behavioral_dna", {}) or {}
    fire = user.get("latest_fire_result", {}) or {}
    threshold = abs(float(behavioral.get("panic_threshold", -17.0)))
    drop = abs(float(request.market_drop_pct))
    proximity = (drop / threshold) * 100 if threshold > 0 else 0

    if proximity >= 85:
        severity = "HIGH"
        risk_type = "panic_risk"
    elif proximity >= 60:
        severity = "MEDIUM"
        risk_type = "pre_panic_signal"
    else:
        severity = "LOW"
        risk_type = "none"

    base_age = float(fire.get("estimated_retire_age_with_plan", 50.0) or 50.0)
    stop_age = float(fire.get("estimated_retire_age_current", base_age + 2.0) or base_age + 2.0)
    delta = max(0.0, stop_age - base_age)
    additional = float(fire.get("corpus_gap", 0) or 0)

    message_preview = (
        f"Market -{drop:.1f}% hai. Agar SIP pause hua toh retirement {delta:.1f} years delay ho sakti hai."
    )
    if request.send_push:
        await ws_manager.send_to_user(
            request.user_id,
            {
                "type": "market_event",
                "severity": severity,
                "data": {
                    "nifty_change": -drop,
                    "message": message_preview,
                    "action_required": severity in {"HIGH", "MEDIUM"},
                    "intervention_type": "HARD" if severity == "HIGH" else "SOFT",
                },
            },
        )

    await interventions_repo.create(
        {
            "user_id": request.user_id,
            "risk_state": {"type": risk_type, "severity": severity, "proximity_to_threshold_pct": round(proximity, 1)},
            "market_drop_pct": request.market_drop_pct,
            "message_preview": message_preview,
            "send_whatsapp": request.send_whatsapp,
            "send_push": request.send_push,
        }
    )

    ai_result = await run_orchestrator(
        user_id=request.user_id,
        message="Market gir raha hai",
        behavioral_dna=user.get("behavioral_dna"),
        calculation_result=fire,
        intervention_data={
            "market_drop_pct": request.market_drop_pct,
            "send_whatsapp": request.send_whatsapp,
            "phone_number": user.get("phone_number"),
        },
    )

    return ai_result


class LifeSimulatorRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    event_description: str
    financial_dna: dict | None = None
    behavioral_dna: dict | None = None


@router.post("/life-event")
async def life_event(request: LifeSimulatorRequest):
    user = await users_repo.get_user(request.user_id) or {}
    fire_result = user.get("latest_fire_result")
    
    result = await run_orchestrator(
        user_id=request.user_id,
        message=request.event_description,
        financial_dna=request.financial_dna or user.get("financial_dna"),
        behavioral_dna=request.behavioral_dna or user.get("behavioral_dna"),
        calculation_result=fire_result,
    )
    return result
