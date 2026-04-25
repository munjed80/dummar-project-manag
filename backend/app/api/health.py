"""
Health check endpoints — detailed system health monitoring.

Endpoints:
  GET /health/detailed  — checks DB connectivity (admin)
  GET /health/ready     — readiness probe (DB only, public)
  GET /health/ocr       — OCR engine status + Arabic verification (admin)
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

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
    version: str = "1.0.0"


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


@router.get("/detailed", response_model=DetailedHealth)
def detailed_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_internal_user),
):
    """
    Detailed health check — tests DB connectivity.
    Restricted to authenticated internal staff: this endpoint exposes operational
    detail (latency) that should not be available to anonymous callers in
    production. Use /health (liveness) and /health/ready (readiness) for
    unauthenticated probes.
    """
    db_health = _check_db(db)

    overall = "unhealthy" if db_health.status == "error" else "healthy"

    return DetailedHealth(
        status=overall,
        database=db_health,
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


# ---------------------------------------------------------------------------
# OCR verification endpoint
# ---------------------------------------------------------------------------


@router.get("/ocr")
def ocr_health_check(
    current_user: User = Depends(get_current_internal_user),
):
    """
    OCR engine status and verification.
    Returns OCR engine info, Tesseract availability, supported formats,
    and a basic Arabic text processing verification.
    Requires internal staff authentication.
    """
    from app.services.ocr_service import get_ocr_status, is_tesseract_available

    status = get_ocr_status()

    # Basic Arabic text verification — test that the OCR service
    # can handle Arabic content without crashing
    arabic_verification = {"status": "skipped", "message": "Tesseract not available"}
    if is_tesseract_available():
        try:
            import tempfile
            import os
            from app.services.ocr_service import process_ocr

            # Create a minimal text file with Arabic content for verification
            arabic_text = "عقد رقم 2024/001\nشركة دمّر للمقاولات\nالقيمة: 500,000 ل.س"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(arabic_text)
                temp_path = f.name

            try:
                result = process_ocr(temp_path, 'txt')
                if result.success and result.text.strip():
                    arabic_verification = {
                        "status": "ok",
                        "engine": result.engine,
                        "text_length": len(result.text),
                        "confidence": result.confidence,
                        "message": "Arabic text processing verified successfully",
                    }
                else:
                    arabic_verification = {
                        "status": "warning",
                        "message": "OCR processed but returned empty or failed result",
                        "warnings": result.warnings,
                    }
            finally:
                os.unlink(temp_path)
        except Exception as e:
            logger.exception("OCR Arabic verification check failed")
            arabic_verification = {
                "status": "error",
                "message": "Arabic verification failed. Check server logs for details.",
            }

    status["arabic_verification"] = arabic_verification
    return status
