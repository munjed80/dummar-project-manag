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
    password: str = Field(..., min_length=8)
    # When True (default for admin-created accounts) the user must rotate their
    # password on first login via /auth/change-password.
    must_change_password: bool = True


class UserUpdate(BaseModel):
    """Fields an admin (PROJECT_DIRECTOR) can change on an existing user.

    Email is intentionally optional throughout the system — we never require it.
    Setting ``password`` here will hash it and force a password change on next
    login (see ``app.api.users.update_user``).
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[int] = None
    org_unit_id: Optional[int] = None
    password: Optional[str] = Field(default=None, min_length=8)
    must_change_password: Optional[bool] = None


class AdminPasswordReset(BaseModel):
    """Admin-only password reset payload."""
    new_password: str = Field(..., min_length=8)
    require_change_on_next_login: bool = True


class PasswordChangeRequest(BaseModel):
    """Self-service password change (used for first-login rotation too)."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: int
    is_active: int
    must_change_password: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    must_change_password: bool = False


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    username: str
    password: str

