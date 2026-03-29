from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import error_response
from app.engines.tax_engine import calculate_tax_comparison
from app.repositories.users_repo import UsersRepository
from app.services.audit_service import persist_audit_trail

from agents.orchestrator import run_orchestrator

router = APIRouter(prefix="/api", tags=["tax"])
users_repo = UsersRepository()


class TaxRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    inputs: dict


@router.post("/tax")
async def tax_plan(request: TaxRequest):
    try:
        result = calculate_tax_comparison(request.inputs)
        calculation_id = await persist_audit_trail(
            user_id=request.user_id,
            calculation_type="tax",
            audit_trail=result.get("audit_trail", []),
        )
        result["calculation_id"] = calculation_id
        result["sebi_disclaimer"] = settings.sebi_disclaimer
        result["user_id"] = request.user_id
        await users_repo.upsert_user(
            request.user_id,
            {
                "latest_tax_result": result.get("comparison", {}),
                "latest_tax_calculation_id": calculation_id,
            },
        )
        
        user = await users_repo.get_user(request.user_id) or {}
        ai_response = await run_orchestrator(
            user_id=request.user_id,
            message="Tax comparison karo",
            financial_dna=user.get("financial_dna"),
            calculation_result=result
        )
        result.update(ai_response)
        
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=error_response("invalid_tax_input", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=error_response("tax_engine_failed", "Unable to calculate tax", {"reason": str(exc)}),
        ) from exc
