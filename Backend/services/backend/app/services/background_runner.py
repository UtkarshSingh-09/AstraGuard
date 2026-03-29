from __future__ import annotations

import asyncio
from typing import Awaitable


class BackgroundRunner:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def spawn(self, coro: Awaitable) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))


background_runner = BackgroundRunner()
