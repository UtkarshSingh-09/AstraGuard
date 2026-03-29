import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.engines.tax_engine import calculate_tax_comparison  # noqa: E402


class TaxEngineTests(unittest.TestCase):
    def test_tax_engine_returns_expected_shape(self):
        inputs = {
            "base_salary": 1800000,
            "hra_received": 360000,
            "rent_paid_monthly": 0,
            "city_type": "metro",
            "investments_80c": 150000,
            "nps_80ccd1b": 50000,
            "home_loan_interest_24b": 40000,
            "health_insurance_80d_self": 0,
            "health_insurance_80d_parents": 0,
            "other_income": 0,
            "financial_year": "2026-27",
        }
        result = calculate_tax_comparison(inputs)
        self.assertEqual(result["status"], "success")
        self.assertIn("old_regime", result)
        self.assertIn("new_regime", result)
        self.assertIn("comparison", result)
        self.assertGreater(len(result["audit_trail"]), 0)

    def test_known_case_values(self):
        inputs = {
            "base_salary": 1800000,
            "hra_received": 360000,
            "rent_paid_monthly": 0,
            "city_type": "metro",
            "investments_80c": 150000,
            "nps_80ccd1b": 50000,
            "home_loan_interest_24b": 40000,
            "health_insurance_80d_self": 0,
            "health_insurance_80d_parents": 0,
            "other_income": 0,
            "financial_year": "2026-27",
        }
        result = calculate_tax_comparison(inputs)
        self.assertEqual(result["old_regime"]["total_tax"], 147680)
        self.assertEqual(result["new_regime"]["total_tax"], 150800)
        self.assertEqual(result["comparison"]["optimal_regime"], "OLD")
        self.assertEqual(result["comparison"]["savings_with_optimal"], 3120)

    def test_negative_salary_rejected(self):
        with self.assertRaises(ValueError):
            calculate_tax_comparison({"base_salary": -1})


if __name__ == "__main__":
    unittest.main()
