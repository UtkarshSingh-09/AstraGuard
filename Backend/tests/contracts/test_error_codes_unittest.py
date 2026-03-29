import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts" / "python"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))

from errors import ERROR_CODES  # noqa: E402


class ErrorCodeContractTests(unittest.TestCase):
    def test_required_error_codes_exist(self):
        required = {
            "invalid_fire_input",
            "invalid_tax_input",
            "invalid_portfolio_input",
            "job_not_found",
            "user_not_found",
            "audit_not_found",
            "internal_error",
        }
        self.assertTrue(required.issubset(set(ERROR_CODES.keys())))


if __name__ == "__main__":
    unittest.main()
