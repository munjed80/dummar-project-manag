from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    title: str
    code: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location_id: Optional[int] = None
    contract_id: Optional[int] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location_id: Optional[int] = None
    contract_id: Optional[int] = None


class ProjectResponse(ProjectBase):
    id: int
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    task_count: int = 0
    complaint_count: int = 0
    team_count: int = 0
    location_name: Optional[str] = None
    contract_number: Optional[str] = None

    class Config:
        from_attributes = True
