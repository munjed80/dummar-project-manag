from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from typing import Optional
from fastapi import Request


def write_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Optional[Request] = None,
):
    # Auto-extract IP and user_agent from Request if provided
    if request is not None:
        if ip_address is None:
            ip_address = request.client.host if request.client else None
        if user_agent is None:
            user_agent = request.headers.get("user-agent", "")[:500]

    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    return log
