from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db_manager


class SessionsRepository:
    collection_name = "sessions"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def append_conversation(self, session_id: str, user_id: str | None, role: str, content: str) -> None:
        if not db_manager.is_mongo_ready:
            return
        await db_manager.mongo_db[self.collection_name].update_one(
            {"_id": session_id},
            {
                "$push": {"conversation_history": {"role": role, "content": content, "timestamp": self._utc_now()}},
                "$set": {"updated_at": self._utc_now(), "user_id": user_id},
                "$setOnInsert": {"created_at": self._utc_now()},
            },
            upsert=True,
        )

    async def set_extracted_data(self, session_id: str, extracted: dict[str, Any], completion_percentage: int) -> None:
        if not db_manager.is_mongo_ready:
            return
        await db_manager.mongo_db[self.collection_name].update_one(
            {"_id": session_id},
            {
                "$set": {
                    "extracted_so_far": extracted,
                    "completion_percentage": completion_percentage,
                    "updated_at": self._utc_now(),
                }
            },
            upsert=True,
        )

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        if not db_manager.is_mongo_ready:
            return None
        return await db_manager.mongo_db[self.collection_name].find_one({"_id": session_id})
