import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.models.contracts import JobCreateRequest, JobStatus, JobType  # noqa: E402
from app.pipelines.cams_agent import CAMSAgent  # noqa: E402
from app.pipelines.form16_agent import Form16Agent  # noqa: E402
from app.services.interactive_step_service import interactive_steps  # noqa: E402
from app.services.job_registry import job_service  # noqa: E402
from app.services.secret_store import secret_store  # noqa: E402


class IngestionAgentsTests(unittest.IsolatedAsyncioTestCase):
    async def test_cams_agent_mock_completes(self):
        job = job_service.create_job(JobCreateRequest(user_id="usr1", job_type=JobType.CAMS_FETCH, payload={"mode": "mock"}))
        secret_store.put(job.job_id, {"pan": "ABCDE1234F", "email": "a@b.com"})
        agent = CAMSAgent()
        await agent.run(job.job_id, job.payload)
        final_job = job_service.get_job(job.job_id)
        self.assertIsNotNone(final_job)
        self.assertEqual(final_job.status, JobStatus.COMPLETE)

    async def test_form16_agent_assisted_waits_for_user_step(self):
        job = job_service.create_job(
            JobCreateRequest(user_id="usr1", job_type=JobType.FORM16_FETCH, payload={"mode": "assisted"})
        )
        secret_store.put(job.job_id, {"username": "demo", "password": "demo"})
        agent = Form16Agent()

        task = asyncio.create_task(agent.run(job.job_id, job.payload))
        await asyncio.sleep(0.2)
        interactive_steps.submit(job.job_id, "otp", "123456")
        await task

        final_job = job_service.get_job(job.job_id)
        self.assertIsNotNone(final_job)
        self.assertEqual(final_job.status, JobStatus.COMPLETE)


if __name__ == "__main__":
    unittest.main()
