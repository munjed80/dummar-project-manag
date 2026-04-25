"""Centralized execution log — records the outcome of every critical action.

Every notification, automation action, background task and email goes through
:func:`app.services.execution_log.record_execution` (or the
``track_execution`` context manager) which inserts a row here. Operators query
``GET /execution-logs`` to debug failures without trawling worker logs.

Status semantics:
  * ``success`` — the action ran to completion without raising.
  * ``failed``  — the action raised an exception. ``error`` holds the message
    and (truncated) traceback.
  * ``skipped`` — preconditions weren't met (e.g. SMTP disabled, duplicate
    email guard, missing entity). Recorded so operators can tell "no-op" from
    "never tried".
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


# Status values are kept as plain strings rather than a SQLAlchemy Enum so
# new outcomes (e.g. "retried") can be added without an ALTER TYPE migration.
EXECUTION_STATUS_SUCCESS = "success"
EXECUTION_STATUS_FAILED = "failed"
EXECUTION_STATUS_SKIPPED = "skipped"

# Coarse buckets so the API can offer a useful filter in the UI.
ACTION_TYPE_NOTIFICATION = "notification"
ACTION_TYPE_EMAIL = "email"
ACTION_TYPE_AUTOMATION = "automation"
ACTION_TYPE_TASK = "task"


class ExecutionLog(Base):
    """A single observation of a critical action's outcome."""

    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    # Coarse bucket: notification / email / automation / task.
    action_type = Column(String(50), nullable=False, index=True)
    # Specific operation, e.g. "dummar.email.send", "create_notification",
    # "automation.action.email", "automation.run".
    action_name = Column(String(200), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)

    # Optional link to the domain entity that triggered the action.
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)

    # User who triggered or owns the action (nullable for system-initiated work).
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Free-form JSON-serialised context (sanitised by the service layer — no
    # secrets, no credentials).
    payload = Column(Text, nullable=True)

    # Failure details — empty for success/skipped rows.
    error = Column(Text, nullable=True)

    # Timing — duration_ms is denormalised so dashboards don't have to
    # re-compute it from the timestamps.
    started_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
