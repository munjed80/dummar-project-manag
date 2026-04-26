from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.investment_property import PropertyType, PropertyStatus
from app.schemas.file_utils import parse_file_list


class InvestmentPropertyBase(BaseModel):
    property_type: PropertyType
    address: str
    area: Optional[float] = None
    status: PropertyStatus = PropertyStatus.AVAILABLE
    description: Optional[str] = None
    owner_name: Optional[str] = None
    owner_info: Optional[str] = None
    property_images: Optional[List[str]] = None
    property_documents: Optional[List[str]] = None
    owner_id_image: Optional[str] = None
    additional_attachments: Optional[List[str]] = None
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
    property_images: Optional[List[str]] = None
    property_documents: Optional[List[str]] = None
    owner_id_image: Optional[str] = None
    additional_attachments: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class InvestmentPropertyResponse(InvestmentPropertyBase):
    id: int
    is_active: bool
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    @classmethod
    def _parse_files(cls, v: object) -> Optional[List[str]]:
        return parse_file_list(v)

    _validate_property_images = field_validator("property_images", mode="before")(_parse_files)
    _validate_property_documents = field_validator("property_documents", mode="before")(_parse_files)
    _validate_additional_attachments = field_validator("additional_attachments", mode="before")(_parse_files)

    class Config:
        from_attributes = True


class PaginatedInvestmentProperties(BaseModel):
    total_count: int
    items: list[InvestmentPropertyResponse]
