"""Background job system (Celery + Redis).

This package wires Celery into the Dummar backend. Heavy or IO-bound work
such as PDF generation, contract document OCR/intelligence and notification
fan-out is enqueued as Celery tasks so that the HTTP request thread returns
quickly.

The system degrades gracefully:

* If ``CELERY_BROKER_URL`` is empty (the default, e.g. in tests / local
  dev without a Redis container) **or** ``CELERY_TASK_ALWAYS_EAGER`` is
  ``True``, tasks are executed synchronously in-process via ``apply()``.
  This keeps the public service functions usable from any context — tests
  do not need a broker, and a developer can run the API standalone.
* In production (Redis + worker container running), ``dispatch()`` enqueues
  the task and returns an :class:`AsyncResult` whose ``id`` can be polled
  via the ``GET /jobs/{task_id}`` endpoint.

See :mod:`app.jobs.celery_app`, :mod:`app.jobs.dispatch`, and
:mod:`app.jobs.tasks` for the concrete pieces.
"""

from app.jobs.celery_app import celery_app
from app.jobs.dispatch import dispatch, is_eager_mode

__all__ = ["celery_app", "dispatch", "is_eager_mode"]
