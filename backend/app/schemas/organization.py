from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.organization import OrgLevel


class OrganizationUnitBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    level: OrgLevel
    parent_id: Optional[int] = None
    is_active: bool = True


class OrganizationUnitCreate(OrganizationUnitBase):
    pass


class OrganizationUnitUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    parent_id: Optional[int] = None


class OrganizationUnitResponse(OrganizationUnitBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrganizationUnitTreeNode(OrganizationUnitResponse):
    children: List["OrganizationUnitTreeNode"] = []


OrganizationUnitTreeNode.model_rebuild()


class PermissionItem(BaseModel):
    resource: str
    action: str


class MePermissionsResponse(BaseModel):
    user_id: int
    role: str
    org_unit_id: Optional[int] = None
    governorate_id: Optional[int] = None
    municipality_id: Optional[int] = None
    district_id: Optional[int] = None
    scope_unit_ids: Optional[List[int]] = None  # None ⇒ global
    permissions: List[PermissionItem]
