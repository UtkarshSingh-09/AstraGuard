from __future__ import annotations

from app.models.contracts import JobStatus
from app.services.job_registry import job_service


class Form16Pipeline:
    """
    Assisted background pipeline contract for Form16 retrieval.
    """

    @staticmethod
    def start(job_id: str) -> None:
        job_service.update_job(job_id, status=JobStatus.RUNNING, message="Starting Form16 assisted fetch")

    @staticmethod
    def await_otp_or_captcha(job_id: str) -> None:
        job_service.update_job(
            job_id,
            status=JobStatus.AWAITING_USER_STEP,
            message="Form16 flow awaiting OTP/captcha/user challenge input",
        )

    @staticmethod
    def mark_downloaded(job_id: str) -> None:
        job_service.update_job(job_id, status=JobStatus.DOWNLOADED, message="Form16 downloaded")

    @staticmethod
    def fail(job_id: str, reason: str) -> None:
        job_service.update_job(job_id, status=JobStatus.FAILED, message=f"Form16 pipeline failed: {reason}")
