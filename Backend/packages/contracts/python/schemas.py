from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorEnvelope(BaseModel):
    status: str
    error: dict[str, Any]
    timestamp: str


class CalculationEnvelope(BaseModel):
    status: str
    user_id: str
    calculation_id: str | None = None
    sebi_disclaimer: str
    audit_trail: list[dict[str, Any]] = []


class JobEnvelope(BaseModel):
    status: str
    job_id: str
    message: str
