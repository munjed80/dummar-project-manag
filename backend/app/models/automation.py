"""Automation engine — configurable trigger/condition/action rules.

The :class:`Automation` row encodes a single rule:

* ``trigger`` — enum identifying the domain event that fires the rule
  (e.g. ``complaint_created``, ``complaint_status_changed``,
  ``task_created``, ``task_status_changed``).
* ``conditions`` — JSON list of simple {field, operator, value} predicates
  evaluated against the event context. All conditions must match for the
  actions to run (logical AND). An empty list matches everything.
* ``actions`` — JSON list of {type, params} entries executed in order.
  Supported action types: ``notification``, ``create_task``.
* ``enabled`` — soft-toggle so operators can pause a rule without
  deleting it.

Conditions and actions are kept in JSON columns so the schema does not
need to grow every time a new operator or action is added.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
import enum


class AutomationTrigger(str, enum.Enum):
    """Domain events that an automation can listen for."""

    COMPLAINT_CREATED = "complaint_created"
    COMPLAINT_STATUS_CHANGED = "complaint_status_changed"
    TASK_CREATED = "task_created"
    TASK_STATUS_CHANGED = "task_status_changed"


class Automation(Base):
    __tablename__ = "automations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger = Column(SQLEnum(AutomationTrigger), nullable=False, index=True)

    # JSON-encoded list of {field, operator, value} predicates.
    # Stored as Text to keep the migration portable across SQLite/PG.
    conditions = Column(Text, nullable=True)
    # JSON-encoded list of {type, params} action descriptors.
    actions = Column(Text, nullable=False)

    enabled = Column(Boolean, nullable=False, default=True, server_default="1")

    # Operational telemetry
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    created_by = relationship("User", foreign_keys=[created_by_id])
