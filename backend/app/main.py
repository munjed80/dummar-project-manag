import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from app.api import auth, complaints, tasks, contracts, locations, dashboard, users, uploads, reports, notifications, gis
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Rate limiter (shared instance used by endpoint modules)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(
    title="Dummar Project Management API",
    description="Production-grade API for Damascus Dummar Project Management Platform",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS – origins read from CORS_ORIGINS env var (comma-separated)
# ---------------------------------------------------------------------------
cors_origins = settings.get_cors_origins()
logger.info("CORS allowed origins: %s", cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ---------------------------------------------------------------------------
# Startup: warn about insecure default passwords
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup_security_checks():
    try:
        from app.core.database import SessionLocal
        from app.scripts.seed_data import check_default_passwords
        db = SessionLocal()
        try:
            check_default_passwords(db)
        finally:
            db.close()
    except Exception:
        # Don't block startup if DB is not ready yet (e.g. during CI)
        logger.debug("Skipped startup password check (DB may not be available)")
