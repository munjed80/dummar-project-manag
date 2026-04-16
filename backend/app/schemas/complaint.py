from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.complaint import ComplaintType, ComplaintStatus, ComplaintPriority


class ComplaintBase(BaseModel):
    full_name: str
    phone: str
    complaint_type: ComplaintType
    description: str
    location_text: Optional[str] = None
    area_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ComplaintCreate(ComplaintBase):
    images: Optional[str] = None


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[ComplaintPriority] = None
    assigned_to_id: Optional[int] = None
    notes: Optional[str] = None
    images: Optional[str] = None


class ComplaintResponse(ComplaintBase):
    id: int
    tracking_number: str
    status: ComplaintStatus
    priority: Optional[ComplaintPriority]
    assigned_to_id: Optional[int]
    images: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ComplaintTrackRequest(BaseModel):
    tracking_number: str
    phone: str


class ComplaintActivityResponse(BaseModel):
    id: int
    action: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
