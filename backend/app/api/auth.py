from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core import permissions as perms
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    PasswordChangeRequest,
    Token,
    UserResponse,
)
from app.schemas.organization import MePermissionsResponse, PermissionItem
from app.api.deps import get_current_user
from app.services.audit import write_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})

    write_audit_log(
        db, action="login", entity_type="user",
        entity_id=user.id, user_id=user.id,
        description=f"User {user.username} logged in",
        request=request,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_password": bool(getattr(user, "must_change_password", False)),
    }


@router.post("/change-password", response_model=UserResponse)
def change_my_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Self-service password change. Used both for routine rotation and for
    the first-login flow when ``must_change_password`` is set on the account.

    Verifies the current password, hashes the new one, and clears the
    ``must_change_password`` flag.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)

    write_audit_log(
        db, action="password_change", entity_type="user",
        entity_id=current_user.id, user_id=current_user.id,
        description=f"User {current_user.username} changed their password",
        request=request,
    )
    return current_user


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/permissions", response_model=MePermissionsResponse)
def get_current_user_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's effective permissions, org chain, and reachable
    org subtree IDs. Powers the frontend ``<Can>`` wrapper so the UI can hide
    actions the backend would refuse anyway.
    """
    chain = perms.derive_org_chain(db, current_user.org_unit_id)
    scope = perms.user_scope_unit_ids(db, current_user)
    return MePermissionsResponse(
        user_id=current_user.id,
        role=current_user.role.value,
        org_unit_id=current_user.org_unit_id,
        governorate_id=chain["governorate_id"],
        municipality_id=chain["municipality_id"],
        district_id=chain["district_id"],
        scope_unit_ids=None if scope is None else sorted(scope),
        permissions=[
            PermissionItem(**p) for p in perms.list_permissions(current_user.role)
        ],
    )

