import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.models.contracts import JobCreateRequest, JobType  # noqa: E402
from app.services.job_service import InMemoryJobService  # noqa: E402


class JobServiceListenerTests(unittest.TestCase):
    def test_listener_receives_create_and_update_events(self):
        captured: list[tuple[str, str]] = []
        service = InMemoryJobService(ttl_seconds=300)

        def listener(job):
            captured.append((job.job_id, str(job.status)))

        service.set_listener(listener)
        job = service.create_job(
            JobCreateRequest(user_id="usr_listener", job_type=JobType.CAMS_FETCH, payload={})
        )
        service.update_job(job.job_id, message="running-check")

        self.assertGreaterEqual(len(captured), 2)
        self.assertEqual(captured[0][0], job.job_id)
        self.assertEqual(captured[1][0], job.job_id)


if __name__ == "__main__":
    unittest.main()
