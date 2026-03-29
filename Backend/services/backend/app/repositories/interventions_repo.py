from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db_manager


class InterventionsRepository:
    collection_name = "interventions"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def create(self, payload: dict[str, Any]) -> None:
        if not db_manager.is_mongo_ready:
            return
        await db_manager.mongo_db[self.collection_name].insert_one(
            {
                **payload,
                "timestamp": self._utc_now(),
            }
        )
