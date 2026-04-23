from pydantic import BaseModel
from typing import Optional, List


class SettingItem(BaseModel):
    key: str
    value: Optional[str] = None
    value_type: str = 'string'
    category: str = 'general'
    description: Optional[str] = None


class SettingsBulkUpdate(BaseModel):
    items: List[SettingItem]
