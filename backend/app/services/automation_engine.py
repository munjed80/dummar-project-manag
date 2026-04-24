"""Automation engine — evaluates and runs configured automations.

Public API
----------

* :func:`fire_event(db, trigger, context)` — call this from anywhere a
  domain event happens (complaint created, task status changed, …). It
  loads every enabled automation listening for ``trigger``, evaluates
  conditions, and executes matching actions.
* :func:`run_automation(db, automation, context)` — execute a single
  automation against a context (used by the manual ``/automations/{id}/test``
  endpoint and by ``fire_event``).

Design notes
------------

* Automations are persisted with ``conditions`` and ``actions`` stored as
  JSON in TEXT columns. The engine de-serialises them per invocation;
  storage stays portable across SQLite and PostgreSQL.
* Each automation runs inside its own try/except so one bad rule never
  blocks the others. Errors are logged and recorded on the row in
  ``last_error`` for operator visibility.
* Fan-out is **synchronous** by design. The handful of supported actions
  are cheap (insert a notification row, enqueue an email job, create a
  task row); offloading them to Celery would buy little and would make
  semantics harder to test. Email sending already uses the background-job
  system internally via :func:`app.services.email_service.send_email`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.automation import Automation, AutomationTrigger

logger = logging.getLogger("dummar.automations")


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


def _get_field(context: Dict[str, Any], path: str) -> Any:
    """Read a possibly dotted path from the context.

    Supports nested dicts (``complaint.status``). Returns ``None`` if the
    path doesn't resolve, mirroring how downstream operators treat missing
    values (``eq`` to ``None`` is meaningful, etc.).
    """
    cur: Any = context
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluate a single {field, operator, value} predicate."""
    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")
    if not field or not operator:
        return False

    actual = _get_field(context, field)

    try:
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "in":
            return isinstance(expected, (list, tuple, set)) and actual in expected
        if operator == "not_in":
            return isinstance(expected, (list, tuple, set)) and actual not in expected
        if operator == "contains":
            if actual is None:
                return False
            return str(expected) in str(actual)
        if operator == "gt":
            return actual is not None and expected is not None and actual > expected
        if operator == "lt":
            return actual is not None and expected is not None and actual < expected
    except Exception:
        logger.exception(
            "Condition evaluation error for field=%s operator=%s", field, operator
        )
        return False

    return False


def _evaluate_conditions(
    conditions: List[Dict[str, Any]], context: Dict[str, Any]
) -> bool:
    """All conditions must match (logical AND). Empty list ⇒ match."""
    return all(_evaluate_condition(c, context) for c in conditions)


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


def _resolve_template(value: Any, context: Dict[str, Any]) -> Any:
    """Substitute ``{field.path}`` placeholders inside a string from the
    context. Non-string values pass through unchanged so action params
    remain typed (e.g. integer ``user_id``).
    """
    if not isinstance(value, str):
        return value
    if "{" not in value:
        return value

    out = value
    # Very small {a.b.c} substitution — intentionally not a full templating
    # engine. Avoids pulling in jinja for this single use case.
    import re

    def _sub(match: "re.Match[str]") -> str:
        path = match.group(1).strip()
        resolved = _get_field(context, path)
        return "" if resolved is None else str(resolved)

    out = re.sub(r"\{([a-zA-Z0-9_.]+)\}", _sub, out)
    return out


def _action_notification(
    db: Session, params: Dict[str, Any], context: Dict[str, Any]
) -> None:
    """Create an in-app Notification row.

    Required params: ``user_id`` (int).
    Optional params: ``title``, ``message`` (templated), ``notification_type``,
    ``entity_type``, ``entity_id`` (templated).
    """
    from app.models.notification import NotificationType
    from app.services.notification_service import create_notification

    user_id = params.get("user_id")
    if user_id is None:
        # Allow templating user_id from the context (e.g. assigned_to_id)
        user_id = _resolve_template(params.get("user_id_template", ""), context)
        if not user_id:
            raise ValueError("notification action requires 'user_id'")
        user_id = int(user_id)

    title = _resolve_template(params.get("title", "Automation"), context)
    message = _resolve_template(params.get("message", ""), context)

    type_str = params.get("notification_type", "general")
    try:
        notif_type = NotificationType(type_str)
    except ValueError:
        notif_type = NotificationType.GENERAL

    entity_type = params.get("entity_type")
    entity_id_raw = params.get("entity_id")
    entity_id: Optional[int] = None
    if entity_id_raw is not None:
        resolved = _resolve_template(entity_id_raw, context)
        try:
            entity_id = int(resolved) if resolved not in (None, "") else None
        except (TypeError, ValueError):
            entity_id = None

    create_notification(
        db=db,
        user_id=int(user_id),
        notification_type=notif_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def _action_email(
    db: Session, params: Dict[str, Any], context: Dict[str, Any]
) -> None:
    """Send an email via the background-job-backed email service.

    Required params: ``to_email``. Optional: ``subject``, ``body_html``
    (both templated against the context).
    """
    from app.services.email_service import send_email

    to_email = _resolve_template(params.get("to_email", ""), context)
    if not to_email:
        raise ValueError("email action requires 'to_email'")

    subject = _resolve_template(
        params.get("subject", "Dummar automation notification"), context
    )
    body_html = _resolve_template(
        params.get("body_html", "<p>Automation triggered.</p>"), context
    )

    send_email(to_email=to_email, subject=subject, body_html=body_html)


def _action_create_task(
    db: Session, params: Dict[str, Any], context: Dict[str, Any]
) -> None:
    """Create a Task row.

    Required params: ``title``. Optional: ``description``, ``priority``,
    ``assigned_to_id``, ``team_id``, ``project_id``, ``complaint_id``,
    ``location_id``, ``area_id``. All values are templated against context
    so an automation triggered by ``complaint_created`` can copy
    ``{complaint.id}`` into ``complaint_id``.
    """
    from app.models.task import Task, TaskActivity, TaskSourceType

    title = _resolve_template(params.get("title", ""), context)
    if not title:
        raise ValueError("create_task action requires 'title'")

    def _opt_int(key: str) -> Optional[int]:
        raw = params.get(key)
        if raw is None:
            return None
        resolved = _resolve_template(raw, context)
        try:
            return int(resolved) if resolved not in (None, "") else None
        except (TypeError, ValueError):
            return None

    description = _resolve_template(params.get("description", ""), context) or ""
    priority = params.get("priority")  # left as string, schema validated downstream
    if isinstance(priority, str):
        priority = _resolve_template(priority, context)

    complaint_id = _opt_int("complaint_id")

    task = Task(
        title=title,
        description=description,
        source_type=(
            TaskSourceType.COMPLAINT if complaint_id else TaskSourceType.INTERNAL
        ),
        complaint_id=complaint_id,
        area_id=_opt_int("area_id"),
        location_id=_opt_int("location_id"),
        project_id=_opt_int("project_id"),
        team_id=_opt_int("team_id"),
        assigned_to_id=_opt_int("assigned_to_id"),
        priority=priority or "medium",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    activity = TaskActivity(
        task_id=task.id,
        action="created_by_automation",
        description=f"Task created by automation rule (context trigger=automation)",
    )
    db.add(activity)
    db.commit()


_ACTION_HANDLERS: Dict[
    str, Callable[[Session, Dict[str, Any], Dict[str, Any]], None]
] = {
    "notification": _action_notification,
    "email": _action_email,
    "create_task": _action_create_task,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_automation(
    db: Session, automation: Automation, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Run a single automation against ``context``.

    Returns a small report dict ``{matched, actions_executed, errors}``.
    Persists ``run_count``, ``last_run_at`` and ``last_error`` for
    operator visibility. Never raises — all failures are captured.
    """
    report: Dict[str, Any] = {
        "matched": False,
        "actions_executed": 0,
        "errors": [],
    }

    try:
        conditions = json.loads(automation.conditions or "[]")
        actions = json.loads(automation.actions or "[]")
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in automation {automation.id}: {exc}"
        logger.error(msg)
        report["errors"].append(msg)
        _record_run(db, automation, error=msg)
        return report

    if not _evaluate_conditions(conditions, context):
        return report
    report["matched"] = True

    for entry in actions:
        atype = entry.get("type")
        params = entry.get("params") or {}
        handler = _ACTION_HANDLERS.get(atype)
        if handler is None:
            msg = f"Automation {automation.id}: unknown action type '{atype}'"
            logger.warning(msg)
            report["errors"].append(msg)
            continue
        try:
            handler(db, params, context)
            report["actions_executed"] += 1
            logger.info(
                "Automation %s ran action=%s (trigger=%s)",
                automation.id,
                atype,
                automation.trigger.value,
            )
        except Exception as exc:
            msg = f"Automation {automation.id} action '{atype}' failed: {exc}"
            logger.exception(msg)
            report["errors"].append(msg)

    _record_run(
        db,
        automation,
        error="; ".join(report["errors"]) if report["errors"] else None,
    )
    return report


def fire_event(
    db: Session, trigger: AutomationTrigger, context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Fan out an event to every enabled automation for *trigger*.

    Always returns a list of per-automation reports (possibly empty).
    Catches and logs any unexpected error from the engine itself so a
    bug in the automation layer never breaks the upstream API request.
    """
    try:
        rules = (
            db.query(Automation)
            .filter(
                Automation.trigger == trigger,
                Automation.enabled.is_(True),
            )
            .all()
        )
    except Exception:
        logger.exception(
            "Failed to load automations for trigger=%s", trigger.value
        )
        return []

    if not rules:
        return []

    logger.debug(
        "fire_event trigger=%s context_keys=%s rules=%d",
        trigger.value,
        sorted(context.keys()),
        len(rules),
    )

    reports: List[Dict[str, Any]] = []
    for rule in rules:
        try:
            reports.append(run_automation(db, rule, context))
        except Exception:
            logger.exception(
                "Automation %s crashed unexpectedly (trigger=%s)",
                rule.id,
                trigger.value,
            )
    return reports


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _record_run(
    db: Session, automation: Automation, error: Optional[str] = None
) -> None:
    """Update the audit columns on the automation row."""
    try:
        automation.run_count = (automation.run_count or 0) + 1
        automation.last_run_at = datetime.utcnow()
        automation.last_error = error
        db.commit()
    except Exception:
        logger.exception(
            "Failed to record automation run id=%s", automation.id
        )
        try:
            db.rollback()
        except Exception:
            pass
