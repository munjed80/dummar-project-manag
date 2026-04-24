"""Pydantic schemas for the automation engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.automation import AutomationTrigger


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


# Operators supported by the condition evaluator. Kept in sync with
# app.services.automation_engine._evaluate_condition.
SUPPORTED_OPERATORS = {"eq", "ne", "in", "not_in", "contains", "gt", "lt"}

# Action types supported by the action executor. Kept in sync with
# app.services.automation_engine._ACTION_HANDLERS.
SUPPORTED_ACTION_TYPES = {"notification", "email", "create_task"}


class AutomationCondition(BaseModel):
    """A single predicate evaluated against the trigger context."""

    field: str = Field(..., min_length=1, max_length=100)
    operator: str
    value: Any = None

    @field_validator("operator")
    @classmethod
    def _validate_operator(cls, v: str) -> str:
        if v not in SUPPORTED_OPERATORS:
            raise ValueError(
                f"Unsupported operator '{v}'. Supported: {sorted(SUPPORTED_OPERATORS)}"
            )
        return v


class AutomationAction(BaseModel):
    """A single action to execute when the rule fires."""

    type: str
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in SUPPORTED_ACTION_TYPES:
            raise ValueError(
                f"Unsupported action type '{v}'. Supported: {sorted(SUPPORTED_ACTION_TYPES)}"
            )
        return v


# ---------------------------------------------------------------------------
# CRUD schemas
# ---------------------------------------------------------------------------


class AutomationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    trigger: AutomationTrigger
    conditions: List[AutomationCondition] = Field(default_factory=list)
    actions: List[AutomationAction] = Field(..., min_length=1)
    enabled: bool = True


class AutomationCreate(AutomationBase):
    pass


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    trigger: Optional[AutomationTrigger] = None
    conditions: Optional[List[AutomationCondition]] = None
    actions: Optional[List[AutomationAction]] = Field(default=None, min_length=1)
    enabled: Optional[bool] = None


class AutomationResponse(AutomationBase):
    id: int
    last_run_at: Optional[datetime] = None
    run_count: int = 0
    last_error: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AutomationTestRequest(BaseModel):
    """Manually fire an automation against a synthetic event context."""

    context: Dict[str, Any] = Field(default_factory=dict)


class AutomationTestResult(BaseModel):
    matched: bool
    actions_executed: int
    errors: List[str] = Field(default_factory=list)
