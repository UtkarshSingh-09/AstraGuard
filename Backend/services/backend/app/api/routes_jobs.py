from fastapi import APIRouter, HTTPException

from app.core.errors import error_response
from app.models.contracts import (
    ApiStatus,
    JobCreateRequest,
    JobCreateResponse,
    JobStatus,
    JobType,
    JobUserStepRequest,
)
from app.services.interactive_step_service import interactive_steps
from app.services.job_registry import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse)
async def create_job(request: JobCreateRequest) -> JobCreateResponse:
    job = job_service.create_job(request)
    return JobCreateResponse(
        status=ApiStatus.PROCESSING,
        job_id=job.job_id,
        job_type=job.job_type,
        job_status=job.status,
        message="Job created successfully",
    )


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=error_response("job_not_found", "No job found for provided job_id"),
        )
    return {
        "status": ApiStatus.PROCESSING if job.status != JobStatus.COMPLETE else ApiStatus.SUCCESS,
        "job_id": job.job_id,
        "job_status": job.status,
        "message": job.message,
        "result": job.result,
        "error": job.error,
    }


@router.post("/{job_id}/user-step")
async def submit_user_step(job_id: str, request: JobUserStepRequest):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=error_response("job_not_found", "No job found for provided job_id"),
        )
    job.payload[f"user_step_{request.step_type.value}"] = request.value
    interactive_steps.submit(job_id, request.step_type.value, request.value)
    if job.job_type == JobType.CAMS_FETCH:
        job_service.update_job(
            job_id,
            status=JobStatus.AWAITING_USER_STEP,
            message="CAMS step acknowledged. Complete manual CAS request and upload PDF.",
            result={
                "status": "awaiting_user_step",
                "source": "assisted_playwright",
                "required_step": "upload_cas_pdf",
                "next_step": "Use upload fallback once CAS is received",
            },
        )
        return {
            "status": ApiStatus.SUCCESS,
            "job_id": job_id,
            "job_status": JobStatus.AWAITING_USER_STEP,
            "message": "CAMS step acknowledged; waiting for upload/manual completion",
        }
    job_service.update_job(
        job_id,
        status=JobStatus.RUNNING,
        message=f"Received user step: {request.step_type.value}. Resuming automation.",
    )
    return {
        "status": ApiStatus.SUCCESS,
        "job_id": job_id,
        "job_status": JobStatus.RUNNING,
        "message": "User step accepted",
    }
