"""
Health check endpoints — detailed system health monitoring.

Endpoints:
  GET /health/detailed  — checks DB connectivity, SMTP reachability
  GET /health/smtp      — tests SMTP connection only (admin)
  POST /health/smtp/test-send — sends a real test email (admin, requires SMTP enabled)
"""
import logging
import smtplib
import ssl
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_internal_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class ComponentHealth(BaseModel):
    status: str  # "ok" | "error" | "disabled"
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class DetailedHealth(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    database: ComponentHealth
    smtp: ComponentHealth
    version: str = "1.0.0"


class SmtpTestResult(BaseModel):
    status: str  # "ok" | "error" | "disabled"
    host: Optional[str] = None
    port: Optional[int] = None
    latency_ms: Optional[float] = None
    message: Optional[str] = None


def _check_db(db: Session) -> ComponentHealth:
    """Test database connectivity with a simple query."""
    try:
        start = time.monotonic()
        db.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error("Health check: DB connection failed: %s", e)
        return ComponentHealth(status="error", message=str(e)[:200])


def _check_smtp() -> ComponentHealth:
    """Test SMTP server reachability (connection only, no email sent)."""
    if not settings.SMTP_ENABLED:
        return ComponentHealth(status="disabled", message="SMTP_ENABLED=false")

    if not settings.SMTP_HOST:
        return ComponentHealth(status="error", message="SMTP_HOST not configured")

    try:
        start = time.monotonic()
        port = settings.SMTP_PORT
        timeout = 10

        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, port, timeout=timeout, context=context) as server:
                server.ehlo()
        else:
            with smtplib.SMTP(settings.SMTP_HOST, port, timeout=timeout) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()

        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error("Health check: SMTP connection failed: %s", e)
        return ComponentHealth(status="error", message=str(e)[:200])


@router.get("/detailed", response_model=DetailedHealth)
def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check — tests DB and SMTP connectivity.
    Public endpoint (no auth) for monitoring tools / load balancers.
    """
    db_health = _check_db(db)
    smtp_health = _check_smtp()

    # Overall status
    if db_health.status == "error":
        overall = "unhealthy"
    elif smtp_health.status == "error":
        overall = "degraded"
    else:
        overall = "healthy"

    return DetailedHealth(
        status=overall,
        database=db_health,
        smtp=smtp_health,
    )


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe — returns 200 only when the database is reachable.
    Used by container orchestrators to determine if traffic can be routed.
    """
    db_health = _check_db(db)
    if db_health.status != "ok":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": db_health.model_dump()},
        )
    return {"status": "ready", "database": db_health.model_dump()}


@router.get("/smtp", response_model=SmtpTestResult)
def smtp_health_check(
    current_user: User = Depends(get_current_internal_user),
):
    """
    Test SMTP connectivity. Requires internal staff authentication.
    Does NOT send any email — only tests the connection.
    """
    if not settings.SMTP_ENABLED:
        return SmtpTestResult(
            status="disabled",
            message="SMTP is disabled. Set SMTP_ENABLED=true to enable.",
        )

    if not settings.SMTP_HOST:
        return SmtpTestResult(
            status="error",
            message="SMTP_HOST is not configured.",
        )

    try:
        start = time.monotonic()
        port = settings.SMTP_PORT
        timeout = 10

        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, port, timeout=timeout, context=context) as server:
                server.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, port, timeout=timeout) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        latency = (time.monotonic() - start) * 1000
        return SmtpTestResult(
            status="ok",
            host=settings.SMTP_HOST,
            port=port,
            latency_ms=round(latency, 2),
            message="SMTP connection and authentication successful.",
        )
    except Exception as e:
        return SmtpTestResult(
            status="error",
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            message=str(e)[:300],
        )


class SmtpTestSendRequest(BaseModel):
    to_email: EmailStr


class SmtpTestSendResult(BaseModel):
    status: str  # "sent" | "error" | "disabled"
    to_email: str
    message: str


@router.post("/smtp/test-send", response_model=SmtpTestSendResult)
def smtp_test_send(
    request_body: SmtpTestSendRequest,
    current_user: User = Depends(get_current_internal_user),
):
    """
    Send a real test email to verify SMTP configuration end-to-end.
    Requires internal staff authentication and SMTP to be enabled.
    This is an operational verification tool, not for regular use.
    """
    from app.services.email_service import send_email, _render_html

    if not settings.SMTP_ENABLED:
        return SmtpTestSendResult(
            status="disabled",
            to_email=request_body.to_email,
            message="SMTP is disabled. Set SMTP_ENABLED=true to enable.",
        )

    content = (
        "<p>هذا بريد اختباري من منصة إدارة مشروع دمّر.</p>"
        "<p>إذا تلقيت هذا البريد، فإن إعدادات SMTP تعمل بشكل صحيح.</p>"
        "<p>This is a test email from Dummar Project Management Platform. "
        "If you received this email, SMTP configuration is working correctly.</p>"
    )
    html_body = _render_html("اختبار البريد الإلكتروني — Email Test", content)

    success = send_email(
        to_email=request_body.to_email,
        subject="Dummar Platform — SMTP Test / اختبار البريد",
        body_html=html_body,
    )

    if success:
        logger.info("SMTP test email sent successfully to %s by user %s", request_body.to_email, current_user.username)
        return SmtpTestSendResult(
            status="sent",
            to_email=request_body.to_email,
            message="Test email sent successfully. Check inbox (and spam folder).",
        )
    else:
        return SmtpTestSendResult(
            status="error",
            to_email=request_body.to_email,
            message="Failed to send test email. Check application logs for details.",
        )
