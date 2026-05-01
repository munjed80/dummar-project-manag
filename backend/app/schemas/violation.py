"""Pydantic schemas for the Violations module."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.violation import (
    ViolationSeverity,
    ViolationStatus,
    ViolationType,
)


class ViolationBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    violation_type: ViolationType
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    municipality_id: Optional[int] = None
    district_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    related_complaint_id: Optional[int] = None
    related_task_id: Optional[int] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    legal_reference: Optional[str] = Field(default=None, max_length=255)
    fine_amount: Optional[Decimal] = None
    deadline_date: Optional[datetime] = None


class ViolationCreate(ViolationBase):
    """Payload for creating a violation. ``status`` defaults to NEW."""

    status: ViolationStatus = ViolationStatus.NEW


class ViolationUpdate(BaseModel):
    """All fields optional — partial update via PATCH."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1)
    violation_type: Optional[ViolationType] = None
    severity: Optional[ViolationSeverity] = None
    status: Optional[ViolationStatus] = None
    municipality_id: Optional[int] = None
    district_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    related_complaint_id: Optional[int] = None
    related_task_id: Optional[int] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    legal_reference: Optional[str] = Field(default=None, max_length=255)
    fine_amount: Optional[Decimal] = None
    deadline_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class ViolationStatusUpdate(BaseModel):
    """Dedicated payload for the status-only PATCH endpoint."""

    status: ViolationStatus
    note: Optional[str] = None


class ViolationRead(ViolationBase):
    id: int
    violation_number: str
    status: ViolationStatus
    org_unit_id: Optional[int] = None
    reported_by_user_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ViolationListResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    items: List[ViolationRead]
