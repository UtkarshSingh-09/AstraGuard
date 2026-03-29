from fastapi import APIRouter, HTTPException

from app.core.errors import error_response
from app.repositories.audit_repo import AuditRepository

router = APIRouter(prefix="/api", tags=["audit"])
audit_repo = AuditRepository()


def _serialize_for_json(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k == "_id":
                out[k] = str(v)
            else:
                out[k] = _serialize_for_json(v)
        return out
    if isinstance(value, list):
        return [_serialize_for_json(v) for v in value]
    return value


@router.get("/audit/{calculation_id}")
async def get_audit(calculation_id: str):
    try:
        rows = await audit_repo.fetch_by_calculation_id(calculation_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=error_response("db_unavailable", "Database temporarily unavailable", {"reason": str(exc)}),
        ) from exc
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=error_response("audit_not_found", "No audit records found for calculation_id"),
        )
    return {
        "status": "success",
        "calculation_id": calculation_id,
        "steps": _serialize_for_json(rows),
    }
