from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.models.task import TaskStatus, TaskSourceType, TaskPriority


class TaskBase(BaseModel):
    title: str
    description: str
    source_type: TaskSourceType = TaskSourceType.INTERNAL
    complaint_id: Optional[int] = None
    contract_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    area_id: Optional[int] = None
    location_text: Optional[str] = None
    due_date: Optional[date] = None
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    notes: Optional[str] = None


class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    before_photos: Optional[str]
    after_photos: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TaskActivityResponse(BaseModel):
    id: int
    action: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
