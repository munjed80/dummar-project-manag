"""Helpers for dispatching Celery tasks from request handlers / services.

The :func:`dispatch` helper is the single entry-point used by the rest of
the codebase. It hides the difference between eager mode (sync, tests /
local-dev) and queued mode (Redis broker + worker container) so callers
do not have to branch on configuration.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import Task
from celery.result import AsyncResult, EagerResult

from app.core.config import settings

logger = logging.getLogger("dummar.jobs.dispatch")


def is_eager_mode() -> bool:
    """Return True when Celery tasks run inline rather than via a broker."""
    return bool(settings.CELERY_TASK_ALWAYS_EAGER) or not settings.CELERY_BROKER_URL


def dispatch(task: Task, *args: Any, **kwargs: Any) -> AsyncResult | EagerResult:
    """Enqueue *task* with ``args`` / ``kwargs`` and return the result handle.

    * In eager mode (no broker, or ``CELERY_TASK_ALWAYS_EAGER=True``) the task
      runs synchronously and an :class:`EagerResult` is returned. Any exception
      raised by the task body will propagate to the caller.
    * Otherwise the task is enqueued via ``apply_async`` and an
      :class:`AsyncResult` is returned immediately. The caller can poll the
      ``id`` via the ``GET /jobs/{task_id}`` endpoint.

    The helper logs failures defensively: if enqueuing itself fails (e.g. the
    broker is unreachable for a moment) the error is logged and re-raised so
    the API endpoint can return a 5xx — we never silently drop work.
    """
    if is_eager_mode():
        logger.debug("Running task %s eagerly", task.name)
        # apply() respects task_eager_propagates so test/dev callers see real
        # exceptions instead of an EagerResult holding the failure.
        return task.apply(args=args, kwargs=kwargs)

    try:
        result = task.apply_async(args=args, kwargs=kwargs)
        logger.info("Enqueued task %s id=%s", task.name, result.id)
        return result
    except Exception:
        logger.exception("Failed to enqueue task %s", task.name)
        raise
