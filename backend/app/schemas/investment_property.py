from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.investment_property import PropertyType, PropertyStatus


class InvestmentPropertyBase(BaseModel):
    property_type: PropertyType
    address: str
    area: Optional[float] = None
    status: PropertyStatus = PropertyStatus.AVAILABLE
    description: Optional[str] = None
    owner_name: Optional[str] = None
    owner_info: Optional[str] = None
    notes: Optional[str] = None


class InvestmentPropertyCreate(InvestmentPropertyBase):
    pass


class InvestmentPropertyUpdate(BaseModel):
    property_type: Optional[PropertyType] = None
    address: Optional[str] = None
    area: Optional[float] = None
    status: Optional[PropertyStatus] = None
    description: Optional[str] = None
    owner_name: Optional[str] = None
    owner_info: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class InvestmentPropertyResponse(InvestmentPropertyBase):
    id: int
    is_active: bool
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaginatedInvestmentProperties(BaseModel):
    total_count: int
    items: list[InvestmentPropertyResponse]
