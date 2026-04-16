from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

from app.schemas.complaint import ComplaintResponse
from app.schemas.task import TaskResponse
from app.schemas.contract import ContractResponse


class StatusBreakdown(BaseModel):
    status: str
    count: int


class TypeBreakdown(BaseModel):
    type: str
    count: int


class AreaBreakdown(BaseModel):
    area_id: Optional[int] = None
    area_name: Optional[str] = None
    count: int


class ComplaintSummary(BaseModel):
    total: int
    by_status: List[StatusBreakdown]
    by_type: List[TypeBreakdown]
    by_area: List[AreaBreakdown]


class TaskSummary(BaseModel):
    total: int
    by_status: List[StatusBreakdown]
    by_area: List[AreaBreakdown]


class ContractSummary(BaseModel):
    total: int
    by_status: List[StatusBreakdown]
    by_type: List[TypeBreakdown]


class ReportSummary(BaseModel):
    complaints: ComplaintSummary
    tasks: TaskSummary
    contracts: ContractSummary


class PaginatedComplaints(BaseModel):
    total_count: int
    items: List[ComplaintResponse]


class PaginatedTasks(BaseModel):
    total_count: int
    items: List[TaskResponse]


class PaginatedContracts(BaseModel):
    total_count: int
    items: List[ContractResponse]
