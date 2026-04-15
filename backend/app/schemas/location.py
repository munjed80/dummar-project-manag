from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
