import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.engines.portfolio_engine import analyze_portfolio  # noqa: E402


class PortfolioEngineTests(unittest.TestCase):
    def test_portfolio_analysis_shape(self):
        inputs = {
            "as_of_date": "2026-03-28",
            "benchmark_xirr_nifty50": 12.8,
            "funds": [
                {
                    "name": "Axis Bluechip Fund",
                    "isin": "INF846K01EW2",
                    "invested": 300000,
                    "current_value": 387000,
                    "plan_type": "DIRECT",
                    "expense_ratio": 0.44,
                    "transactions": [
                        {"date": "2023-01-01", "amount": 100000, "type": "BUY"},
                        {"date": "2023-06-01", "amount": 200000, "type": "BUY"},
                    ],
                    "holdings": [
                        {"stock": "Reliance Industries", "weight": 8.2},
                        {"stock": "Infosys", "weight": 6.3},
                    ],
                },
                {
                    "name": "HDFC Top 100 Fund",
                    "isin": "INF179K01VN3",
                    "invested": 250000,
                    "current_value": 298000,
                    "plan_type": "REGULAR",
                    "expense_ratio": 1.68,
                    "direct_plan_expense_ratio": 0.51,
                    "transactions": [
                        {"date": "2025-10-20", "amount": 250000, "type": "BUY"},
                    ],
                    "holdings": [
                        {"stock": "Reliance Industries", "weight": 7.8},
                        {"stock": "Infosys", "weight": 6.9},
                    ],
                },
                {
                    "name": "Mirae Large Cap",
                    "isin": "INF769K01KT0",
                    "invested": 200000,
                    "current_value": 241000,
                    "plan_type": "DIRECT",
                    "expense_ratio": 0.56,
                    "transactions": [
                        {"date": "2024-06-20", "amount": 200000, "type": "BUY"},
                    ],
                    "holdings": [
                        {"stock": "Reliance Industries", "weight": 6.4},
                        {"stock": "TCS", "weight": 5.1},
                    ],
                },
            ],
        }
        result = analyze_portfolio(inputs)
        self.assertEqual(result["status"], "complete")
        self.assertIn("portfolio_summary", result)
        self.assertIn("overlap_analysis", result)
        self.assertIn("rebalancing_plan", result)
        self.assertGreater(result["portfolio_summary"]["current_value"], 0)
        self.assertGreater(len(result["audit_trail"]), 0)

    def test_overlap_and_regular_plan_actions_present(self):
        inputs = {
            "as_of_date": "2026-03-28",
            "funds": [
                {
                    "name": "Fund A",
                    "invested": 300000,
                    "current_value": 350000,
                    "plan_type": "REGULAR",
                    "expense_ratio": 1.5,
                    "direct_plan_expense_ratio": 0.5,
                    "transactions": [{"date": "2025-12-01", "amount": 300000, "type": "BUY"}],
                    "holdings": [{"stock": "Reliance Industries", "weight": 10.0}],
                },
                {
                    "name": "Fund B",
                    "invested": 300000,
                    "current_value": 360000,
                    "plan_type": "DIRECT",
                    "expense_ratio": 0.4,
                    "transactions": [{"date": "2024-01-01", "amount": 300000, "type": "BUY"}],
                    "holdings": [{"stock": "Reliance Industries", "weight": 9.5}],
                },
            ],
        }
        result = analyze_portfolio(inputs)
        actions = [a["action"] for a in result["rebalancing_plan"]]
        self.assertIn("SWITCH_TO_DIRECT", actions)
        self.assertIn(result["overlap_analysis"]["overlap_severity"], {"LOW", "MEDIUM", "HIGH"})

    def test_empty_funds_rejected(self):
        with self.assertRaises(ValueError):
            analyze_portfolio({"funds": []})


if __name__ == "__main__":
    unittest.main()
