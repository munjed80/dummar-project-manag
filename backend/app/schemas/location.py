from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------------------------------------------------------------------------
# Unified Location schemas
# ---------------------------------------------------------------------------

class LocationCreate(BaseModel):
    name: str
    code: str
    location_type: str
    parent_id: Optional[int] = None
    status: str = "active"
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_path: Optional[str] = None
    metadata_json: Optional[str] = None


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_path: Optional[str] = None
    metadata_json: Optional[str] = None
    is_active: Optional[int] = None


class LocationResponse(BaseModel):
    id: int
    name: str
    code: str
    location_type: str
    parent_id: Optional[int] = None
    status: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_path: Optional[str] = None
    metadata_json: Optional[str] = None
    is_active: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LocationTreeNode(BaseModel):
    id: int
    name: str
    code: str
    location_type: str
    parent_id: Optional[int] = None
    status: str
    is_active: int
    children: List["LocationTreeNode"] = []
    complaint_count: int = 0
    task_count: int = 0
    contract_count: int = 0

    class Config:
        from_attributes = True


class LocationDetail(BaseModel):
    location: LocationResponse
    parent: Optional[LocationResponse] = None
    children: List[LocationResponse] = []
    breadcrumb: List[LocationResponse] = []
    complaint_count: int = 0
    open_complaint_count: int = 0
    task_count: int = 0
    open_task_count: int = 0
    contract_count: int = 0
    active_contract_count: int = 0
    delayed_task_count: int = 0


class LocationStats(BaseModel):
    location_id: int
    location_name: str
    location_type: str
    complaint_count: int = 0
    open_complaint_count: int = 0
    task_count: int = 0
    open_task_count: int = 0
    contract_count: int = 0
    active_contract_count: int = 0
    delayed_task_count: int = 0
    is_hotspot: bool = False


class LocationReportSummary(BaseModel):
    total_locations: int
    by_type: dict
    hotspots: List[LocationStats] = []
    most_complaints: List[LocationStats] = []
    most_delayed: List[LocationStats] = []
    contract_coverage: List[LocationStats] = []


# ---------------------------------------------------------------------------
# Legacy schemas (kept for backward compatibility)
# ---------------------------------------------------------------------------

class AreaBase(BaseModel):
    name: str
    name_ar: str
    code: str
    description: Optional[str] = None


class AreaCreate(AreaBase):
    pass


class AreaUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    description: Optional[str] = None


class AreaResponse(AreaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BuildingBase(BaseModel):
    area_id: int
    name: str
    name_ar: str
    building_number: Optional[str] = None
    floors: Optional[int] = None


class BuildingCreate(BuildingBase):
    pass


class BuildingResponse(BuildingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StreetBase(BaseModel):
    name: str
    name_ar: str
    code: Optional[str] = None


class StreetCreate(StreetBase):
    pass


class StreetResponse(StreetBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
