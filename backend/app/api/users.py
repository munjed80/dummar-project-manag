from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import (
    AdminPasswordReset,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from app.api.deps import get_current_user, get_current_active_director
from app.services.audit import write_audit_log


class PaginatedUsers(BaseModel):
    total_count: int
    items: List[UserResponse]

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    if user.email:
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role,
        phone=user.phone,
        org_unit_id=user.org_unit_id,
        is_active=1,
        must_change_password=bool(user.must_change_password),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    write_audit_log(
        db, action="user_create", entity_type="user",
        entity_id=db_user.id, user_id=current_user.id,
        description=(
            f"User {db_user.username} (role={db_user.role.value}) created"
            f"{' [must_change_password]' if db_user.must_change_password else ''}"
        ),
        request=request,
    )

    return db_user


@router.get("/", response_model=PaginatedUsers)
def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role_filter: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db),
):
    query = db.query(User)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    if role_filter:
        query = query.filter(User.role == role_filter)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total_count = query.count()
    users = query.offset(skip).limit(limit).all()
    return {"total_count": total_count, "items": users}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)

    # Defensive: a director must not be able to lock themselves out by
    # demoting their own role or marking themselves inactive in one call.
    if user.id == current_user.id:
        if "is_active" in update_data and not update_data["is_active"]:
            raise HTTPException(
                status_code=400,
                detail="You cannot deactivate your own account",
            )
        if "role" in update_data and update_data["role"] != user.role:
            raise HTTPException(
                status_code=400,
                detail="You cannot change your own role",
            )

    # Track what changed for audit (do not log password values).
    changes = []
    for field, value in update_data.items():
        if field == "password":
            changes.append("password reset")
        elif field == "role":
            old = user.role.value if user.role is not None else None
            new = value.value if hasattr(value, "value") else value
            if old != new:
                changes.append(f"role: {old} -> {new}")
        else:
            current = getattr(user, field, None)
            if current != value:
                changes.append(f"{field}: {current} -> {value}")

    # Apply non-password fields directly.
    new_password = update_data.pop("password", None)
    for field, value in update_data.items():
        setattr(user, field, value)

    if new_password is not None:
        user.hashed_password = get_password_hash(new_password)
        # Force the user to rotate the admin-supplied password unless the
        # admin explicitly cleared the flag in the same request.
        if "must_change_password" not in update_data:
            user.must_change_password = True

    db.commit()
    db.refresh(user)

    desc = f"User {user.username} updated"
    if changes:
        desc += f" [{', '.join(changes[:5])}]"

    write_audit_log(
        db, action="user_update", entity_type="user",
        entity_id=user.id, user_id=current_user.id,
        description=desc,
        request=request,
    )

    return user


@router.post("/{user_id}/reset-password", response_model=UserResponse)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    request: Request,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db),
):
    """Admin-only password reset.

    Sets a new password for the target user and (by default) flags the
    account so the user must change it on next login. The new password is
    never stored or logged in plaintext.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(payload.new_password)
    user.must_change_password = bool(payload.require_change_on_next_login)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db, action="user_password_reset", entity_type="user",
        entity_id=user.id, user_id=current_user.id,
        description=(
            f"Password reset for {user.username}"
            f"{' [must_change_password]' if user.must_change_password else ''}"
        ),
        request=request,
    )
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account",
        )

    user.is_active = 0
    db.commit()

    write_audit_log(
        db, action="user_deactivate", entity_type="user",
        entity_id=user.id, user_id=current_user.id,
        description=f"User {user.username} (role={user.role.value}) deactivated",
        request=request,
    )

    return {"message": "User deactivated successfully"}

