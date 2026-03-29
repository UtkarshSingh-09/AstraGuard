from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db_manager


class UsersRepository:
    collection_name = "users"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        if not db_manager.is_mongo_ready:
            return None
        return await db_manager.mongo_db[self.collection_name].find_one({"_id": user_id})

    async def upsert_user(self, user_id: str, payload: dict[str, Any]) -> None:
        if not db_manager.is_mongo_ready:
            return
        await db_manager.mongo_db[self.collection_name].update_one(
            {"_id": user_id},
            {"$set": {**payload, "updated_at": self._utc_now()}, "$setOnInsert": {"created_at": self._utc_now()}},
            upsert=True,
        )

    async def update_financial_dna(self, user_id: str, financial_dna: dict[str, Any]) -> None:
        await self.upsert_user(user_id, {"financial_dna": financial_dna})

    async def update_behavioral_dna(self, user_id: str, behavioral_dna: dict[str, Any]) -> None:
        await self.upsert_user(user_id, {"behavioral_dna": behavioral_dna})

