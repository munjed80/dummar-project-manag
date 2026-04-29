from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


BotIntent = Literal[
    "complaints_summary",
    "tasks_summary",
    "contracts_expiring",
]


class InternalBotQuery(BaseModel):
    intent: BotIntent = Field(..., description="Query intent")
    days: int = Field(7, ge=1, le=365, description="Lookback/forecast window in days")
    limit: int = Field(10, ge=1, le=100, description="Max result rows for list intents")


class InternalBotResponse(BaseModel):
    intent: BotIntent
    summary: str
    data: list[dict[str, Any]]
    generated_on: date
