from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.models.contract import ContractType, ContractStatus


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
    attachments: Optional[str] = None


class ContractResponse(ContractBase):
    id: int
    status: ContractStatus
    pdf_file: Optional[str]
    attachments: Optional[str]
    notes: Optional[str]
    qr_code: Optional[str]
    created_by_id: int
    reviewed_by_id: Optional[int]
    approved_by_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    approved_at: Optional[datetime]
    
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
