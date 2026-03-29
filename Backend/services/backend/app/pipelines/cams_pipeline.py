from __future__ import annotations

from app.models.contracts import JobStatus
from app.services.job_registry import job_service


class CAMSPipeline:
    """
    Assisted background pipeline contract for CAMS/CAS retrieval.
    Real browser automation and mailbox integration are added in later steps.
    """

    @staticmethod
    def start(job_id: str) -> None:
        job_service.update_job(job_id, status=JobStatus.RUNNING, message="Submitting CAMS mailback request")
        job_service.update_job(job_id, status=JobStatus.RUNNING, message="Awaiting CAS document")

    @staticmethod
    def require_user_step(job_id: str, reason: str = "manual_confirmation") -> None:
        job_service.update_job(
            job_id,
            status=JobStatus.AWAITING_USER_STEP,
            message=f"CAMS flow requires user step: {reason}",
        )

    @staticmethod
    def mark_downloaded(job_id: str) -> None:
        job_service.update_job(job_id, status=JobStatus.DOWNLOADED, message="CAMS document downloaded")

    @staticmethod
    def fail(job_id: str, reason: str) -> None:
        job_service.update_job(job_id, status=JobStatus.FAILED, message=f"CAMS pipeline failed: {reason}")
