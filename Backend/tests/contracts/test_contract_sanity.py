import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.core.errors import error_response


def test_error_response_shape():
    payload = error_response("invalid_input", "Bad input", details={"field": "age"})
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["message"] == "Bad input"
    assert payload["error"]["details"]["field"] == "age"
    assert "timestamp" in payload
