import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.services.arth_score_service import calculate_arth_score  # noqa: E402


class ArthScoreServiceTests(unittest.TestCase):
    def test_default_score_for_missing_user(self):
        score = calculate_arth_score(None)
        self.assertEqual(score["max"], 1000)
        self.assertGreater(score["total"], 0)

    def test_score_shape_for_user(self):
        user = {
            "financial_dna": {"monthly_expenses": 50000, "emergency_fund": 150000, "goals": [{"name": "Retirement"}]},
            "behavioral_dna": {"behavioral_discipline_score": 60, "sip_pauses_last_12m": 1},
            "latest_tax_result": {"savings_with_optimal": 5000},
            "latest_portfolio_summary": {"outperformance": 1.2, "portfolio_xirr": 14.2, "overlap_severity": "HIGH"},
            "latest_fire_result": {"insurance_gap": 1200000},
        }
        score = calculate_arth_score(user)
        self.assertIn("breakdown", score)
        self.assertIn("behavioral_discipline", score["breakdown"])
        self.assertLessEqual(score["total"], 1000)


if __name__ == "__main__":
    unittest.main()
