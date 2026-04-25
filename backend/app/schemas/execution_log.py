"""Pydantic schemas for the central execution log."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ExecutionLogResponse(BaseModel):
    id: int
    action_type: str
    action_name: str
    status: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    user_id: Optional[int] = None
    payload: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedExecutionLogs(BaseModel):
    total_count: int
    items: List[ExecutionLogResponse]
