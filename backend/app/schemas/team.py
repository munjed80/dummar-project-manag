from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.team import TeamType


class TeamBase(BaseModel):
    name: str
    team_type: TeamType = TeamType.INTERNAL_TEAM
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True
    location_id: Optional[int] = None
    project_id: Optional[int] = None
    notes: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    team_type: Optional[TeamType] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None
    location_id: Optional[int] = None
    project_id: Optional[int] = None
    notes: Optional[str] = None


class TeamResponse(TeamBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    task_count: int = 0
    location_name: Optional[str] = None
    project_title: Optional[str] = None

    class Config:
        from_attributes = True
