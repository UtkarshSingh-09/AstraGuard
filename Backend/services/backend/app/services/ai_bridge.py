from __future__ import annotations

from typing import Any, Protocol


class NarrationProvider(Protocol):
    async def fire_narration(self, result: dict[str, Any]) -> str: ...
    async def tax_explanation(self, result: dict[str, Any]) -> str: ...
    async def portfolio_rebalance_narration(self, result: dict[str, Any]) -> str: ...
    async def behavioral_message(self, payload: dict[str, Any]) -> str: ...


class NullNarrationProvider:
    async def fire_narration(self, result: dict[str, Any]) -> str:
        return "Narration unavailable"

    async def tax_explanation(self, result: dict[str, Any]) -> str:
        return "Narration unavailable"

    async def portfolio_rebalance_narration(self, result: dict[str, Any]) -> str:
        return "Narration unavailable"

    async def behavioral_message(self, payload: dict[str, Any]) -> str:
        return "Narration unavailable"
