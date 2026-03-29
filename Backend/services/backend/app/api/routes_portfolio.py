from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import error_response
from app.engines.portfolio_engine import analyze_portfolio
from app.models.contracts import ApiStatus, JobCreateRequest, JobStatus, JobType
from app.services.job_registry import job_service
from app.services.audit_service import persist_audit_trail
from app.repositories.users_repo import UsersRepository

from agents.orchestrator import run_orchestrator

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
users_repo = UsersRepository()


class PortfolioXrayRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    mode: str = Field(default="mock")
    mock_scenario: str | None = None
    inputs: dict = Field(default_factory=dict)


@router.post("/xray")
async def start_xray(request: PortfolioXrayRequest):
    job = job_service.create_job(
        JobCreateRequest(
            user_id=request.user_id,
            job_type=JobType.CAMS_FETCH if request.mode == "cams_auto" else JobType.DOCUMENT_PARSE,
            payload={"mode": request.mode, "mock_scenario": request.mock_scenario, "inputs": request.inputs},
        )
    )

    # Step-5 behavior: compute immediately for mock mode; keep async status for cams_auto.
    if request.mode == "mock":
        try:
            job_service.update_job(job.job_id, status=JobStatus.RUNNING, message="Analyzing portfolio")
            result = analyze_portfolio(request.inputs)
            calc_id = await persist_audit_trail(
                user_id=request.user_id,
                calculation_type="portfolio",
                audit_trail=result.get("audit_trail", []),
            )
            result["calculation_id"] = calc_id
            result["sebi_disclaimer"] = settings.sebi_disclaimer
            await users_repo.upsert_user(
                request.user_id,
                {
                    "latest_portfolio_summary": result.get("portfolio_summary", {}),
                    "latest_portfolio_calculation_id": calc_id,
                },
            )
            
            user = await users_repo.get_user(request.user_id) or {}
            ai_response = await run_orchestrator(
                user_id=request.user_id,
                message="Portfolio review karo",
                financial_dna=user.get("financial_dna"),
                calculation_result=result
            )
            result.update(ai_response)
            
            job_service.update_job(
                job.job_id,
                status=JobStatus.COMPLETE,
                message="Analysis complete",
                result=result,
            )
        except ValueError as exc:
            job_service.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                message="Invalid input",
                error=error_response("invalid_portfolio_input", str(exc)),
            )
        except Exception as exc:
            job_service.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                message="Engine failure",
                error=error_response("portfolio_engine_failed", "Unable to analyze portfolio", {"reason": str(exc)}),
            )

    return {
        "status": ApiStatus.PROCESSING,
        "job_id": job.job_id,
        "estimated_seconds": 45 if request.mode == "cams_auto" else 3,
        "message": "Portfolio job started",
    }


@router.get("/xray/{job_id}")
async def get_xray(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=error_response("job_not_found", "No xray job found for provided job_id"),
        )
    if job.status == JobStatus.COMPLETE:
        return job.result
    if job.status == JobStatus.FAILED:
        return {
            "status": ApiStatus.ERROR,
            "job_id": job_id,
            "error": job.error,
        }
    return {
        "status": ApiStatus.PROCESSING,
        "job_id": job_id,
        "message": job.message,
    }
