from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


BotIntent = Literal[
    "complaints_summary",
    "tasks_summary",
    "contracts_expiring",
    "context_analysis",
]


# Risk levels surfaced by the rule-based context analyser.
RiskLevel = Literal["low", "medium", "high"]


# Context types supported by /internal-bot/query when running a contextual
# analysis. Phase 3 ships only "complaint" — extend this tuple (and the
# matching backend branch) when wiring contracts/tasks.
SUPPORTED_CONTEXT_TYPES: tuple[str, ...] = ("complaint",)


class InternalBotQuery(BaseModel):
    intent: BotIntent | None = Field(None, description="Structured query intent")
    question: str | None = Field(None, description="Natural-language Arabic question")
    days: int = Field(7, ge=1, le=365, description="Lookback/forecast window in days")
    limit: int = Field(10, ge=1, le=100, description="Max result rows for list intents")
    location_id: int | None = Field(None, ge=1)
    project_id: int | None = Field(None, ge=1)
    # Optional contextual analysis pointer (Phase 3). When both fields are
    # provided the bot returns a rule-based decision-support summary linked
    # to the entity.
    context_type: str | None = Field(
        None, max_length=50, description="Entity type — currently only 'complaint'"
    )
    context_id: int | None = Field(None, ge=1)


class RelatedItem(BaseModel):
    type: str
    id: int
    label: str


class InternalBotResponse(BaseModel):
    intent: BotIntent
    summary: str
    data: list[dict[str, Any]]
    generated_on: date
    # Populated when intent == 'context_analysis'. Optional everywhere else
    # so existing summary/list intents stay unchanged.
    risk_level: Optional[RiskLevel] = None
    key_points: Optional[list[str]] = None
    recommended_actions: Optional[list[str]] = None
    related_items: Optional[list[RelatedItem]] = None
    context_type: Optional[str] = None
    context_id: Optional[int] = None

