from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WsEvent(BaseModel):
    type: str
    data: dict[str, Any]


class MarketEvent(BaseModel):
    type: str = "market_event"
    severity: str
    data: dict[str, Any]


class ArthScoreUpdateEvent(BaseModel):
    type: str = "arth_score_update"
    data: dict[str, Any]
