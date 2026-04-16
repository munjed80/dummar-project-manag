import json
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.models.contract import ContractType, ContractStatus


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


class ContractBase(BaseModel):
    contract_number: str
    title: str
    contractor_name: str
    contractor_contact: Optional[str] = None
    contract_type: ContractType
    contract_value: Decimal
    start_date: date
    end_date: date
    execution_duration_days: Optional[int] = None
    scope_description: str
    related_areas: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    contractor_contact: Optional[str] = None
    end_date: Optional[date] = None
    status: Optional[ContractStatus] = None
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None


class ContractResponse(ContractBase):
    id: int
    status: ContractStatus
    pdf_file: Optional[str]
    attachments: Optional[List[str]] = None
    notes: Optional[str]
    qr_code: Optional[str]
    created_by_id: int
    reviewed_by_id: Optional[int]
    approved_by_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    approved_at: Optional[datetime]

    @field_validator("attachments", mode="before")
    @classmethod
    def parse_attachments(cls, v: object) -> Optional[List[str]]:
        return _parse_file_list(v)

    class Config:
        from_attributes = True


class ContractApprovalRequest(BaseModel):
    action: str
    comments: Optional[str] = None


class ContractApprovalResponse(BaseModel):
    id: int
    contract_id: int
    user_id: int
    action: str
    comments: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
