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
    # Email settings (optional — notifications work in-app without email)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@dummar.gov.sy"
    SMTP_ENABLED: bool = False

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
