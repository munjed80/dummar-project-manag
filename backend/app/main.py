import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import auth, complaints, tasks, contracts, locations, dashboard, users, uploads, reports, notifications, gis, health, audit_logs
from app.core.config import settings
from app.middleware.request_logging import RequestLoggingMiddleware

# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------
_log_level = os.environ.get("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("dummar")


# ---------------------------------------------------------------------------
# Application metrics (lightweight in-memory counters)
# ---------------------------------------------------------------------------
class _Metrics:
    """Simple in-memory request metrics — no external dependency required."""
    def __init__(self):
        self.start_time = time.monotonic()
        self.total_requests = 0
        self.error_requests = 0  # 5xx

    @property
    def uptime_seconds(self) -> float:
        return round(time.monotonic() - self.start_time, 1)

metrics = _Metrics()


# ---------------------------------------------------------------------------
# Lifespan — replaces deprecated on_event("startup")
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Dummar API starting — version 1.0.0")
    try:
        from app.core.database import SessionLocal
        from app.scripts.seed_data import check_default_passwords
        db = SessionLocal()
        try:
            check_default_passwords(db)
        finally:
            db.close()
    except Exception:
        logger.debug("Skipped startup password check (DB may not be available)")

    yield

    # Shutdown
    logger.info("Dummar API shutting down")


# ---------------------------------------------------------------------------
# Rate limiter (shared instance used by endpoint modules)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(
    title="Dummar Project Management API",
    description="Production-grade API for Damascus Dummar Project Management Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Request logging (added before CORS so it wraps actual responses)
app.add_middleware(RequestLoggingMiddleware)

# CORS – origins read from CORS_ORIGINS env var (comma-separated)
cors_origins = settings.get_cors_origins()
logger.info("CORS allowed origins: %s", cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(tasks.router)
app.include_router(contracts.router)
app.include_router(locations.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(uploads.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(gis.router)
app.include_router(health.router)
app.include_router(audit_logs.router)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {
        "message": "Dummar Project Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
def get_metrics():
    """
    Lightweight operational metrics endpoint.
    Exposes uptime and basic request counters for monitoring.
    """
    return {
        "uptime_seconds": metrics.uptime_seconds,
        "total_requests": metrics.total_requests,
        "error_requests": metrics.error_requests,
        "version": "1.0.0",
    }
