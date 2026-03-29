from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.repositories.audit_repo import AuditRepository

audit_repo = AuditRepository()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def persist_audit_trail(
    *,
    user_id: str,
    calculation_type: str,
    audit_trail: list[dict[str, Any]],
    calculation_id: str | None = None,
) -> str:
    calc_id = calculation_id or f"calc_{calculation_type}_{uuid4().hex[:10]}"
    rows: list[dict[str, Any]] = []
    for idx, step in enumerate(audit_trail):
        rows.append(
            {
                "user_id": user_id,
                "calculation_id": calc_id,
                "calculation_type": calculation_type,
                "step_index": idx,
                "step": step.get("step"),
                "formula": step.get("formula"),
                "inputs": step.get("inputs", {}),
                "output": step.get("result"),
                "timestamp": step.get("timestamp", _utc_now()),
            }
        )
    await audit_repo.insert_many(rows)
    return calc_id
