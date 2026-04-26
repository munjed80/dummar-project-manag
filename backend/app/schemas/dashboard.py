from pydantic import BaseModel
from typing import Dict, List, Any


class DashboardStats(BaseModel):
    total_complaints: int
    complaints_by_status: Dict[str, int]
    total_tasks: int
    tasks_by_status: Dict[str, int]
    total_contracts: int
    active_contracts: int
    contracts_nearing_expiry: int
    # Investment-contract expiry buckets (cumulative — within_60 includes
    # within_30; within_90 includes within_60).
    total_investment_contracts: int = 0
    investment_contracts_expired: int = 0
    investment_contracts_within_30: int = 0
    investment_contracts_within_60: int = 0
    investment_contracts_within_90: int = 0
    
    
class RecentActivity(BaseModel):
    recent_complaints: List[Dict[str, Any]]
    recent_tasks: List[Dict[str, Any]]
    recent_contracts: List[Dict[str, Any]]
