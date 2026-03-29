import uuid
import inspect
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.models.contracts import JobCreateRequest, JobState, JobStatus


class InMemoryJobService:
    """
    Step-2 scaffold.
    Replace this with Redis-backed storage and worker queue in Step-6.
    """

    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[JobState, datetime]] = {}
        self._listener: Callable[[JobState], None] | Callable[[JobState], object] | None = None

    def set_listener(self, listener: Callable[[JobState], None] | Callable[[JobState], object] | None) -> None:
        self._listener = listener

    def create_job(self, request: JobCreateRequest) -> JobState:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = JobState(
            job_id=job_id,
            user_id=request.user_id,
            job_type=request.job_type,
            status=JobStatus.QUEUED,
            message="Job queued",
            payload=request.payload,
        )
        self._store[job_id] = (job, self._expires_at())
        self._emit(job)
        return job

    def get_job(self, job_id: str) -> JobState | None:
        data = self._store.get(job_id)
        if not data:
            return None
        job, expires_at = data
        if expires_at < self._now():
            del self._store[job_id]
            return None
        return job

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        message: str | None = None,
        result: dict | None = None,
        error: dict | None = None,
    ) -> JobState | None:
        job = self.get_job(job_id)
        if not job:
            return None
        if status is not None:
            job.status = status
        if message is not None:
            job.message = message
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        self._store[job_id] = (job, self._expires_at())
        self._emit(job)
        return job

    def _emit(self, job: JobState) -> None:
        if self._listener is None:
            return
        try:
            result = self._listener(job)
            if inspect.isawaitable(result):
                # Listener decides whether to schedule internally.
                # If a coroutine was returned, try to schedule only when loop exists.
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(result)  # type: ignore[arg-type]
                except RuntimeError:
                    # No running loop in this context; safely skip.
                    return
        except Exception:
            # Event emission must never break job lifecycle.
            return

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _expires_at(self) -> datetime:
        return self._now() + timedelta(seconds=self._ttl_seconds)
