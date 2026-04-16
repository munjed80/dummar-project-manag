import json
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.complaint import ComplaintType, ComplaintStatus, ComplaintPriority


def _parse_file_list(v: object) -> Optional[List[str]]:
    """Parse a DB text value (JSON array or comma-separated) into a list."""
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
        return [x.strip() for x in v.split(",") if x.strip()]
    return None


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
    images: Optional[List[str]] = None


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[ComplaintPriority] = None
    assigned_to_id: Optional[int] = None
    notes: Optional[str] = None
    images: Optional[List[str]] = None


class ComplaintResponse(ComplaintBase):
    id: int
    tracking_number: str
    status: ComplaintStatus
    priority: Optional[ComplaintPriority]
    assigned_to_id: Optional[int]
    images: Optional[List[str]] = None
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]

    @field_validator("images", mode="before")
    @classmethod
    def parse_images(cls, v: object) -> Optional[List[str]]:
        return _parse_file_list(v)

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
