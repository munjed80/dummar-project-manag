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
    
    
class RecentActivity(BaseModel):
    recent_complaints: List[Dict[str, Any]]
    recent_tasks: List[Dict[str, Any]]
    recent_contracts: List[Dict[str, Any]]
