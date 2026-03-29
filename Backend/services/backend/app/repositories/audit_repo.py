from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db_manager


class AuditRepository:
    collection_name = "audit_logs"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not db_manager.is_mongo_ready or not rows:
            return
        await db_manager.mongo_db[self.collection_name].insert_many(rows)

    async def fetch_by_calculation_id(self, calculation_id: str) -> list[dict[str, Any]]:
        if not db_manager.is_mongo_ready:
            return []
        cursor = db_manager.mongo_db[self.collection_name].find({"calculation_id": calculation_id}).sort("timestamp", 1)
        return await cursor.to_list(length=500)
