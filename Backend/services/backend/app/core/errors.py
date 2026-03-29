from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def error_response(
    code: str,
    message: str,
    status: str = "error",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "error": {
            "code": code,
            "message": message,
        },
        "timestamp": utc_now_iso(),
    }
    if details:
        payload["error"]["details"] = details
    return payload
