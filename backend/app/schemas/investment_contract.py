"""Pydantic schemas for the InvestmentContract resource."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.investment_contract import InvestmentContractStatus, InvestmentType
from app.schemas.file_utils import parse_file_list


class InvestmentContractBase(BaseModel):
    contract_number: str = Field(..., max_length=80)
    property_id: int
    investor_name: str = Field(..., max_length=200)
    investor_contact: Optional[str] = None
    investment_type: InvestmentType = InvestmentType.LEASE
    start_date: date
    end_date: date
    contract_value: Decimal
    notes: Optional[str] = None

    # Typed attachments — each is the relative upload path returned by
    # /uploads/ (or NULL if not yet uploaded).
    contract_copy: Optional[str] = None
    terms_booklet: Optional[str] = None
    investor_id_copy: Optional[str] = None
    owner_id_copy: Optional[str] = None
    ownership_proof: Optional[str] = None
    handover_report: Optional[str] = None
    additional_attachments: Optional[List[str]] = None


class InvestmentContractCreate(InvestmentContractBase):
    pass


class InvestmentContractUpdate(BaseModel):
    contract_number: Optional[str] = Field(default=None, max_length=80)
    property_id: Optional[int] = None
    investor_name: Optional[str] = Field(default=None, max_length=200)
    investor_contact: Optional[str] = None
    investment_type: Optional[InvestmentType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    contract_value: Optional[Decimal] = None
    status: Optional[InvestmentContractStatus] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    contract_copy: Optional[str] = None
    terms_booklet: Optional[str] = None
    investor_id_copy: Optional[str] = None
    owner_id_copy: Optional[str] = None
    ownership_proof: Optional[str] = None
    handover_report: Optional[str] = None
    additional_attachments: Optional[List[str]] = None


class InvestmentContractResponse(BaseModel):
    id: int
    contract_number: str
    property_id: int
    investor_name: str
    investor_contact: Optional[str] = None
    investment_type: InvestmentType
    start_date: date
    end_date: date
    contract_value: Decimal
    status: InvestmentContractStatus
    notes: Optional[str] = None
    contract_copy: Optional[str] = None
    terms_booklet: Optional[str] = None
    investor_id_copy: Optional[str] = None
    owner_id_copy: Optional[str] = None
    ownership_proof: Optional[str] = None
    handover_report: Optional[str] = None
    additional_attachments: Optional[List[str]] = None
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Computed expiry fields (populated by the API layer).
    days_until_expiry: Optional[int] = None
    expiry_alert: Optional[str] = None  # one of: "expired", "30", "60", "90", None

    @field_validator("additional_attachments", mode="before")
    @classmethod
    def _parse_additional(cls, v: object) -> Optional[List[str]]:
        return parse_file_list(v)

    class Config:
        from_attributes = True


class PaginatedInvestmentContracts(BaseModel):
    total_count: int
    items: List[InvestmentContractResponse]
