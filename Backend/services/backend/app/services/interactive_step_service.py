from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class InteractiveStepService:
    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = defaultdict(asyncio.Event)
        self._payloads: dict[str, dict[str, Any]] = {}

    def submit(self, job_id: str, step_type: str, value: str) -> None:
        self._payloads[job_id] = {"step_type": step_type, "value": value}
        self._events[job_id].set()

    async def wait_for_step(self, job_id: str, timeout: int = 300) -> dict[str, Any] | None:
        event = self._events[job_id]
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        event.clear()
        return self._payloads.get(job_id)

    def clear(self, job_id: str) -> None:
        self._events.pop(job_id, None)
        self._payloads.pop(job_id, None)


interactive_steps = InteractiveStepService()
