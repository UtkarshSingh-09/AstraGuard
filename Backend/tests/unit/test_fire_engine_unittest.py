import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.engines.fire_engine import calculate_fire_plan  # noqa: E402


class FireEngineTests(unittest.TestCase):
    def test_fire_engine_returns_expected_shape(self):
        inputs = {
            "age": 34,
            "annual_salary": 2400000,
            "monthly_expenses": 80000,
            "existing_mf": 1800000,
            "existing_ppf": 600000,
            "existing_epf": 200000,
            "monthly_sip_current": 20000,
            "target_monthly_draw": 150000,
            "target_retire_age": 50,
            "inflation_rate": 0.06,
            "equity_return": 0.12,
            "debt_return": 0.07,
            "insurance_cover_existing": 8000000,
        }
        result = calculate_fire_plan(inputs)
        self.assertEqual(result["status"], "success")
        self.assertIn("summary", result)
        self.assertIn("audit_trail", result)
        self.assertGreater(len(result["audit_trail"]), 0)
        self.assertGreater(result["summary"]["corpus_needed"], 0)

    def test_retire_age_increase_reduces_sip_requirement(self):
        base = {
            "age": 34,
            "annual_salary": 2400000,
            "monthly_expenses": 80000,
            "existing_mf": 1800000,
            "existing_ppf": 600000,
            "existing_epf": 200000,
            "monthly_sip_current": 20000,
            "target_monthly_draw": 150000,
            "inflation_rate": 0.06,
            "equity_return": 0.12,
            "debt_return": 0.07,
        }
        r50 = calculate_fire_plan({**base, "target_retire_age": 50})
        r55 = calculate_fire_plan({**base, "target_retire_age": 55})
        self.assertLess(
            r55["summary"]["monthly_sip_total_needed"],
            r50["summary"]["monthly_sip_total_needed"],
        )

    def test_invalid_retire_age_raises(self):
        with self.assertRaises(ValueError):
            calculate_fire_plan(
                {
                    "age": 40,
                    "annual_salary": 1200000,
                    "monthly_expenses": 50000,
                    "existing_mf": 100000,
                    "existing_ppf": 100000,
                    "existing_epf": 0,
                    "monthly_sip_current": 10000,
                    "target_monthly_draw": 60000,
                    "target_retire_age": 35,
                }
            )


if __name__ == "__main__":
    unittest.main()
