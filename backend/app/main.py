import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import auth, complaints, tasks, contracts, locations, dashboard, users, uploads, reports, notifications, gis, health, audit_logs, contract_intelligence
from app.api.deps import get_current_internal_user
from app.core.config import settings
from app.middleware.request_logging import RequestLoggingMiddleware
from app.models.user import User

# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------
_log_level = settings.LOG_LEVEL.upper()
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
    logger.info("Dummar API starting — version 1.0.0 (env=%s, docs_enabled=%s)",
                settings.ENVIRONMENT, settings.docs_enabled())
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

# Disable Swagger UI / ReDoc / openapi schema by default in production.
# Enable explicitly with ENABLE_API_DOCS=true (e.g. when fronted by an auth proxy).
_docs_enabled = settings.docs_enabled()

app = FastAPI(
    title="Dummar Project Management API",
    description="Production-grade API for Damascus Dummar Project Management Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
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
app.include_router(contract_intelligence.router)

# Ensure the upload directory exists. NOTE: we intentionally do NOT mount it as
# unauthenticated StaticFiles. All file access goes through app.api.uploads
# which enforces category-based authorization (sensitive categories like
# "contracts" and "contract_intelligence" require an authenticated internal user).
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "Dummar Project Management API",
        "version": "1.0.0",
        "docs": "/docs" if _docs_enabled else "disabled (set ENABLE_API_DOCS=true to enable)",
    }


@app.get("/health")
def health_check():
    """Liveness probe — always returns 200 if the process is up.
    Public on purpose so orchestrators / load balancers can call it without auth."""
    return {"status": "healthy"}


@app.get("/metrics")
def get_metrics(current_user: User = Depends(get_current_internal_user)):
    """
    Lightweight operational metrics endpoint.
    Exposes uptime and basic request counters for monitoring.
    Restricted to authenticated internal staff to avoid leaking operational data.
    """
    return {
        "uptime_seconds": metrics.uptime_seconds,
        "total_requests": metrics.total_requests,
        "error_requests": metrics.error_requests,
        "version": "1.0.0",
    }
