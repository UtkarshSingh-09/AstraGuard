from __future__ import annotations

import time
from typing import Any


class EphemeralSecretStore:
    """
    In-memory short-lived secret holder for credentials/challenges.
    Never persist secrets to DB.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[dict[str, Any], float]] = {}

    def put(self, key: str, payload: dict[str, Any], ttl_seconds: int = 900) -> None:
        self._store[key] = (payload, time.time() + ttl_seconds)

    def get(self, key: str) -> dict[str, Any] | None:
        item = self._store.get(key)
        if not item:
            return None
        payload, expiry = item
        if expiry < time.time():
            self._store.pop(key, None)
            return None
        return payload

    def merge(self, key: str, patch: dict[str, Any], ttl_seconds: int = 900) -> None:
        current = self.get(key) or {}
        current.update(patch)
        self.put(key, current, ttl_seconds=ttl_seconds)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


secret_store = EphemeralSecretStore()
