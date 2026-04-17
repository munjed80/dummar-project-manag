"""
Request logging middleware — structured request/response logging for observability.

Logs:
- method, path, status_code, duration_ms for every request
- Skips noisy health-check paths to keep logs clean
- Uses structured key=value format for easy parsing by log aggregators
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("dummar.requests")

# Paths to exclude from request logging (health checks are too noisy)
_SKIP_PATHS = frozenset({"/health", "/health/detailed", "/health/ready", "/docs", "/redoc", "/openapi.json"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        client_ip = request.client.host if request.client else "-"

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            logger.error(
                'method=%s path="%s" status=500 duration_ms=%.1f client=%s error=unhandled_exception',
                request.method, path, duration_ms, client_ip,
            )
            raise

        duration_ms = round((time.monotonic() - start) * 1000, 1)
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO

        logger.log(
            log_level,
            'method=%s path="%s" status=%d duration_ms=%.1f client=%s',
            request.method, path, response.status_code, duration_ms, client_ip,
        )

        return response
