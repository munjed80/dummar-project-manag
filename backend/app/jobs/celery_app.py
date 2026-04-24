"""Celery application factory.

The Celery app is constructed once at import time and shared across the
backend. When the broker URL is empty (tests / local dev without Redis)
the app is configured in eager mode so `task.delay()` and `task.apply()`
both run inline.
"""

from __future__ import annotations

import logging

from celery import Celery
from celery.signals import setup_logging

from app.core.config import settings

logger = logging.getLogger("dummar.jobs")


def _build_celery_app() -> Celery:
    """Build and configure the Celery application."""
    broker = settings.CELERY_BROKER_URL or "memory://"
    backend = settings.CELERY_RESULT_BACKEND or "cache+memory://"

    app = Celery(
        "dummar",
        broker=broker,
        backend=backend,
        include=["app.jobs.tasks"],
    )

    # Determine eager mode: explicit flag OR no real broker configured.
    eager = bool(settings.CELERY_TASK_ALWAYS_EAGER) or not settings.CELERY_BROKER_URL

    app.conf.update(
        task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        # Reliability
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # Retry policy defaults — individual tasks can override.
        task_default_retry_delay=10,
        task_publish_retry=True,
        task_publish_retry_policy={
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 1,
            "interval_max": 5,
        },
        # Eager mode: run tasks inline; surface exceptions to the caller so
        # tests/sync callers see the same error they would have seen before.
        task_always_eager=eager,
        task_eager_propagates=eager,
        # Result expiration (1 day) so the Redis backend doesn't grow forever.
        result_expires=86_400,
        broker_connection_retry_on_startup=True,
    )

    if eager:
        logger.info("Celery configured in EAGER mode (tasks run inline)")
    else:
        logger.info(
            "Celery configured with broker=%s backend=%s queue=%s",
            broker,
            backend,
            settings.CELERY_TASK_DEFAULT_QUEUE,
        )

    return app


celery_app = _build_celery_app()


# Make sure the worker process inherits the application's logging
# configuration (level + format) instead of Celery's default handlers.
@setup_logging.connect
def _configure_celery_logging(**_kwargs):  # pragma: no cover - signal handler
    level = settings.LOG_LEVEL.upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
