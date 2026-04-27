from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = "/app/uploads"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    LOG_LEVEL: str = "info"
    # Deployment environment: "production" | "development".
    # In production, /docs, /redoc, and /openapi.json are disabled by default
    # (override with ENABLE_API_DOCS=true).
    ENVIRONMENT: str = "production"
    ENABLE_API_DOCS: bool = False
    # SQLAlchemy connection pool tuning (important for gunicorn multi-worker
    # deployments to prevent pool starvation and stale-connection crashes).
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # ── Background jobs (Celery + Redis) ──
    # When CELERY_BROKER_URL is empty OR CELERY_TASK_ALWAYS_EAGER is True the
    # job system runs tasks inline in the calling process. This keeps tests and
    # local-dev runnable without spinning up Redis + a worker container.
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_DEFAULT_QUEUE: str = "dummar"

    def get_cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins from env var."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def docs_enabled(self) -> bool:
        """API docs (/docs, /redoc, /openapi.json) are enabled only in non-production
        environments OR when ENABLE_API_DOCS is explicitly set to true."""
        if self.ENABLE_API_DOCS:
            return True
        return not self.is_production()

    class Config:
        env_file = ".env"


settings = Settings()
