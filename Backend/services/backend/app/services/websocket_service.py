from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.models.contracts import JobState

class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        if user_id in self._connections and websocket in self._connections[user_id]:
            self._connections[user_id].remove(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> None:
        for ws in list(self._connections.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, payload)

    async def publish_job_update(self, job: JobState) -> None:
        await self.send_to_user(
            job.user_id,
            {
                "type": "job_update",
                "data": {
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "job_status": job.status,
                    "message": job.message,
                    "result": job.result,
                    "error": job.error,
                },
            },
        )


ws_manager = WebSocketManager()
