from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    org_unit_id: Optional[int] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[int] = None
    org_unit_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    is_active: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    username: str
    password: str
