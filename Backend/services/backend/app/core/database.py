from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.core.config import settings

try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
except Exception:  # pragma: no cover
    AsyncIOMotorClient = None  # type: ignore[assignment]
    AsyncIOMotorDatabase = Any  # type: ignore[assignment]

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None


class DatabaseManager:
    def __init__(self) -> None:
        self.mongo_client: AsyncIOMotorClient | None = None
        self.mongo_db: AsyncIOMotorDatabase | None = None
        self.redis_client = None
        self.mongo_last_error: str | None = None
        self.redis_last_error: str | None = None
        self._mongo_ready: bool = False
        self._redis_ready: bool = False

    async def connect(self) -> None:
        if settings.mongodb_uri and AsyncIOMotorClient is not None:
            try:
                self.mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
                self.mongo_db = self.mongo_client[settings.mongodb_db_name]
                await self.mongo_client.admin.command("ping")
                self._mongo_ready = True
                self.mongo_last_error = None
            except Exception as exc:
                self._mongo_ready = False
                self.mongo_last_error = str(exc)
                self.mongo_client = None
                self.mongo_db = None

        if settings.redis_url and aioredis is not None:
            try:
                redis_kwargs: dict[str, Any] = {"decode_responses": True}
                parsed = urlparse(settings.redis_url)
                if parsed.scheme == "rediss":
                    # Hackathon-friendly TLS setting for managed Redis endpoints.
                    # In production, prefer strict cert validation.
                    redis_kwargs["ssl_cert_reqs"] = None
                self.redis_client = aioredis.from_url(settings.redis_url, **redis_kwargs)
                await self.redis_client.ping()
                self._redis_ready = True
                self.redis_last_error = None
            except Exception as exc:
                self._redis_ready = False
                self.redis_last_error = str(exc)
                self.redis_client = None

    async def close(self) -> None:
        if self.mongo_client is not None:
            self.mongo_client.close()
            self.mongo_client = None
            self.mongo_db = None
            self._mongo_ready = False
        if self.redis_client is not None:
            await self.redis_client.close()
            self.redis_client = None
            self._redis_ready = False

    @property
    def is_mongo_ready(self) -> bool:
        return self._mongo_ready and self.mongo_db is not None

    @property
    def is_redis_ready(self) -> bool:
        return self._redis_ready and self.redis_client is not None


db_manager = DatabaseManager()
