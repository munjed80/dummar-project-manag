"""Central execution-log recorder.

Public API:
  * :func:`record_execution` — insert a single ExecutionLog row in one call.
  * :func:`track_execution` — context manager wrapping a block of code; on
    exit it records ``success`` (no exception), ``failed`` (exception, which
    is re-raised by default), or ``skipped`` (caller called ``ctx.skip(...)``).

Design notes:
  * The recorder NEVER raises. A failure to write a log row must not break
    the upstream domain action (we'd rather lose telemetry than silently
    drop a notification or task).
  * Each insert uses a fresh, short-lived session obtained from
    ``app.core.database.SessionLocal`` so it works equally well from inside
    Celery workers (where the request-scoped session is unavailable) and
    from FastAPI handlers. A pre-existing session can be passed via the
    ``db`` argument when caller already has one — we'll use it directly.
  * Payload is JSON-serialised with ``default=str`` so non-serialisable
    objects (datetimes, Decimals) don't blow up the recorder.
"""

from __future__ import annotations

import json
import logging
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Mapping, Optional

from sqlalchemy.orm import Session

from app.models.execution_log import (
    ACTION_TYPE_AUTOMATION,  # noqa: F401 — re-exported convenience
    ACTION_TYPE_NOTIFICATION,  # noqa: F401
    ACTION_TYPE_TASK,  # noqa: F401
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_SKIPPED,
    EXECUTION_STATUS_SUCCESS,
    ExecutionLog,
)

logger = logging.getLogger("dummar.execution_log")

# Hard cap on payload / error fields. Anything longer is truncated so a stack
# trace dump or huge automation context can never blow up a single row.
_MAX_PAYLOAD_CHARS = 8000
_MAX_ERROR_CHARS = 4000

# Keys whose values must NEVER be persisted to the log (we redact them).
_REDACTED_KEYS = frozenset(
    {
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "smtp_password",
        "api_key",
    }
)


def _redact(payload: Any) -> Any:
    """Recursively redact sensitive keys from dict/list payloads."""
    if isinstance(payload, Mapping):
        return {
            k: ("***REDACTED***" if k.lower() in _REDACTED_KEYS else _redact(v))
            for k, v in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [_redact(item) for item in payload]
    return payload


def _serialise_payload(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    try:
        text = json.dumps(_redact(payload), default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        # Fallback to repr so we still capture *something* useful.
        text = repr(payload)
    if len(text) > _MAX_PAYLOAD_CHARS:
        text = text[:_MAX_PAYLOAD_CHARS] + "…(truncated)"
    return text


def _truncate_error(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    if len(text) > _MAX_ERROR_CHARS:
        return text[:_MAX_ERROR_CHARS] + "…(truncated)"
    return text


def _open_session(db: Optional[Session]) -> tuple[Session, bool]:
    """Return (session, owns_session). When owns_session is True the caller
    must close it — used so recording from a worker doesn't leak sessions."""
    if db is not None:
        return db, False
    factory = _session_factory or _default_session_factory
    return factory(), True


# Session factory used when no db is supplied — overridable by tests so the
# recorder writes into the same in-memory SQLite engine the API tests use.
def _default_session_factory() -> Session:
    from app.core.database import SessionLocal

    return SessionLocal()


_session_factory: Optional[Any] = None


def set_log_session_factory(factory: Any) -> None:
    """Override the SQLAlchemy session factory used when no ``db`` is passed.

    Tests call this from ``conftest.py`` so the recorder writes into the
    in-memory SQLite engine. Production never touches it.
    """
    global _session_factory
    _session_factory = factory


def record_execution(
    *,
    action_type: str,
    action_name: str,
    status: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    payload: Any = None,
    error: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    duration_ms: Optional[int] = None,
    db: Optional[Session] = None,
) -> Optional[ExecutionLog]:
    """Insert a single execution-log row. Never raises.

    Returns the persisted row on success, ``None`` if insertion failed.
    """
    try:
        session, owns_session = _open_session(db)
    except Exception:
        logger.exception(
            "Failed to obtain session for execution log action_type=%s action_name=%s",
            action_type,
            action_name,
        )
        return None
    try:
        log = ExecutionLog(
            action_type=action_type,
            action_name=action_name,
            status=status,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            payload=_serialise_payload(payload),
            error=_truncate_error(error),
            started_at=started_at or datetime.now(timezone.utc),
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        session.add(log)
        session.commit()
        if owns_session:
            session.refresh(log)
        return log
    except Exception:
        # Telemetry must never break the caller; log and move on.
        logger.exception(
            "Failed to record execution log action_type=%s action_name=%s",
            action_type,
            action_name,
        )
        try:
            session.rollback()
        except Exception:
            pass
        return None
    finally:
        if owns_session:
            try:
                session.close()
            except Exception:
                pass


class _TrackingContext:
    """Mutable handle yielded by :func:`track_execution`.

    Callers can call :meth:`skip` to mark the execution as skipped (e.g.
    SMTP disabled, dedup hit) instead of success.
    """

    __slots__ = ("entity_type", "entity_id", "user_id", "payload", "_status_override")

    def __init__(self) -> None:
        self.entity_type: Optional[str] = None
        self.entity_id: Optional[int] = None
        self.user_id: Optional[int] = None
        self.payload: Any = None
        self._status_override: Optional[str] = None

    def skip(self, reason: Optional[str] = None) -> None:
        """Mark this execution as ``skipped``. ``reason`` is appended to
        the log's payload for operator visibility."""
        self._status_override = EXECUTION_STATUS_SKIPPED
        if reason is not None:
            if isinstance(self.payload, dict):
                self.payload.setdefault("skip_reason", reason)
            else:
                self.payload = {"skip_reason": reason, "original": self.payload}


@contextmanager
def track_execution(
    action_type: str,
    action_name: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    payload: Any = None,
    db: Optional[Session] = None,
    reraise: bool = True,
) -> Iterator[_TrackingContext]:
    """Track a block of code and emit one ExecutionLog row on exit.

    Usage::

        with track_execution(ACTION_TYPE_TASK, "dummar.contracts.generate_pdf",
                             entity_type="contract", entity_id=contract.id) as ctx:
            ctx.payload = {"contract_number": contract.number}
            run_pdf_generation(...)
            if not_found:
                ctx.skip("contract_not_found")

    On normal completion: status=success (or skipped if ``ctx.skip()`` was
    called). On exception: status=failed, error=traceback; the exception
    is re-raised when ``reraise=True``.
    """
    started = datetime.now(timezone.utc)
    handle = _TrackingContext()
    handle.entity_type = entity_type
    handle.entity_id = entity_id
    handle.user_id = user_id
    handle.payload = payload

    error_text: Optional[str] = None
    raised: Optional[BaseException] = None
    try:
        yield handle
    except Exception as exc:
        raised = exc
        error_text = (
            f"{type(exc).__name__}: {exc}\n" + "".join(traceback.format_exc())
        )
    finally:
        finished = datetime.now(timezone.utc)
        if raised is not None:
            status = EXECUTION_STATUS_FAILED
        elif handle._status_override is not None:
            status = handle._status_override
        else:
            status = EXECUTION_STATUS_SUCCESS

        record_execution(
            action_type=action_type,
            action_name=action_name,
            status=status,
            entity_type=handle.entity_type,
            entity_id=handle.entity_id,
            user_id=handle.user_id,
            payload=handle.payload,
            error=error_text,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
            db=db,
        )

    if raised is not None and reraise:
        raise raised
