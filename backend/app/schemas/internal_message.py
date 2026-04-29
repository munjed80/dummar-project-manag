from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.internal_message import MessageThreadType


class MessageSendRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def validate_body_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message body cannot be blank")
        return normalized


class ThreadCreateRequest(BaseModel):
    participant_user_ids: List[int] = Field(min_length=1)
    title: Optional[str] = Field(default=None, max_length=200)


class MessageResponse(BaseModel):
    id: int
    thread_id: int
    sender_user_id: int
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class ThreadParticipantResponse(BaseModel):
    user_id: int
    joined_at: datetime
    last_read_at: Optional[datetime] = None


class ThreadSummaryResponse(BaseModel):
    id: int
    title: Optional[str]
    thread_type: MessageThreadType
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0
    participants: List[ThreadParticipantResponse] = Field(default_factory=list)


class ThreadDetailResponse(BaseModel):
    thread: ThreadSummaryResponse
    messages: List[MessageResponse]


class PaginatedThreadListResponse(BaseModel):
    total_count: int
    items: List[ThreadSummaryResponse]
