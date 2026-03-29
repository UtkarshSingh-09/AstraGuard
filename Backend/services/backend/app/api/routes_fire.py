from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import error_response
from app.engines.fire_engine import calculate_fire_plan
from app.repositories.users_repo import UsersRepository
from app.services.audit_service import persist_audit_trail

from agents.orchestrator import run_orchestrator

router = APIRouter(prefix="/api", tags=["fire"])
users_repo = UsersRepository()


class FireRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    inputs: dict


@router.post("/fire")
async def fire_plan(request: FireRequest):
    try:
        result = calculate_fire_plan(request.inputs)
        calculation_id = await persist_audit_trail(
            user_id=request.user_id,
            calculation_type="fire",
            audit_trail=result.get("audit_trail", []),
        )
        result["calculation_id"] = calculation_id
        result["sebi_disclaimer"] = settings.sebi_disclaimer
        result["user_id"] = request.user_id
        await users_repo.upsert_user(
            request.user_id,
            {
                "latest_fire_result": result["summary"],
                "latest_fire_calculation_id": calculation_id,
            },
        )
        
        user = await users_repo.get_user(request.user_id) or {}
        ai_response = await run_orchestrator(
            user_id=request.user_id,
            message="FIRE plan calculate karo",
            financial_dna=user.get("financial_dna"),
            calculation_result=result
        )
        result.update(ai_response)
        
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=error_response("invalid_fire_input", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=error_response("fire_engine_failed", "Unable to calculate FIRE plan", {"reason": str(exc)}),
        ) from exc
