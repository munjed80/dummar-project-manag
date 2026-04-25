"""Tests for the central execution-log system.

Covers:
* The recorder service (success / failure / skipped, payload sanitisation,
  context manager re-raise behaviour, fresh-session fallback).
* Instrumentation of the four critical pathways (notifications, automation
  engine, email service, background jobs).
* The /execution-logs API (filters, pagination, role gate).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.automation import Automation, AutomationTrigger
from app.models.execution_log import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_EMAIL,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_TASK,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_SKIPPED,
    EXECUTION_STATUS_SUCCESS,
    ExecutionLog,
)
from app.models.notification import NotificationType
from app.services import execution_log as exec_log_service
from app.services.execution_log import (
    record_execution,
    track_execution,
)
from tests.conftest import _auth_headers


# ---------------------------------------------------------------------------
# Recorder service unit tests
# ---------------------------------------------------------------------------


def test_record_execution_success_inserts_row(db):
    log = record_execution(
        action_type=ACTION_TYPE_NOTIFICATION,
        action_name="unit.success",
        status=EXECUTION_STATUS_SUCCESS,
        entity_type="complaint",
        entity_id=42,
        payload={"a": 1},
        db=db,
    )
    assert log is not None
    assert log.id is not None
    fetched = db.query(ExecutionLog).filter_by(id=log.id).one()
    assert fetched.action_name == "unit.success"
    assert fetched.entity_id == 42
    assert "a" in (fetched.payload or "")


def test_record_execution_with_no_db_uses_factory(db):
    """When db is omitted the recorder uses the test session factory."""
    before = db.query(ExecutionLog).count()
    log = record_execution(
        action_type=ACTION_TYPE_TASK,
        action_name="unit.factory",
        status=EXECUTION_STATUS_SUCCESS,
    )
    assert log is not None
    after = db.query(ExecutionLog).count()
    assert after == before + 1


def test_track_execution_success(db):
    with track_execution(
        ACTION_TYPE_NOTIFICATION, "unit.ctx.ok", entity_type="task", entity_id=7, db=db
    ) as ctx:
        ctx.payload = {"k": "v"}
    row = (
        db.query(ExecutionLog)
        .filter_by(action_name="unit.ctx.ok")
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_SUCCESS
    assert row.duration_ms is not None and row.duration_ms >= 0
    assert row.finished_at is not None


def test_track_execution_failure_records_and_reraises(db):
    with pytest.raises(ValueError):
        with track_execution(ACTION_TYPE_NOTIFICATION, "unit.ctx.fail", db=db):
            raise ValueError("boom")
    row = (
        db.query(ExecutionLog)
        .filter_by(action_name="unit.ctx.fail")
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_FAILED
    assert "boom" in (row.error or "")
    assert "ValueError" in (row.error or "")


def test_track_execution_failure_no_reraise(db):
    with track_execution(
        ACTION_TYPE_TASK, "unit.ctx.fail2", db=db, reraise=False
    ):
        raise RuntimeError("captured")
    row = (
        db.query(ExecutionLog)
        .filter_by(action_name="unit.ctx.fail2")
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row.status == EXECUTION_STATUS_FAILED
    assert "captured" in row.error


def test_track_execution_skip(db):
    with track_execution(ACTION_TYPE_EMAIL, "unit.ctx.skip", db=db) as ctx:
        ctx.skip("disabled")
    row = (
        db.query(ExecutionLog)
        .filter_by(action_name="unit.ctx.skip")
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row.status == EXECUTION_STATUS_SKIPPED
    assert "disabled" in (row.payload or "")


def test_payload_redacts_secrets(db):
    log = record_execution(
        action_type=ACTION_TYPE_TASK,
        action_name="unit.redact",
        status=EXECUTION_STATUS_SUCCESS,
        payload={"password": "shh", "token": "abc", "user": "alice"},
        db=db,
    )
    assert log is not None
    assert "shh" not in (log.payload or "")
    assert "abc" not in (log.payload or "")
    assert "alice" in (log.payload or "")
    assert "REDACTED" in (log.payload or "")


def test_payload_truncated_when_huge(db):
    huge = {"big": "x" * 20000}
    log = record_execution(
        action_type=ACTION_TYPE_TASK,
        action_name="unit.truncate",
        status=EXECUTION_STATUS_SUCCESS,
        payload=huge,
        db=db,
    )
    assert log is not None
    assert log.payload is not None
    assert len(log.payload) <= 8500
    assert "truncated" in log.payload


def test_recorder_never_raises_on_db_failure(monkeypatch, db):
    """If the underlying session blows up, the recorder swallows the error."""

    class _BadFactory:
        def __call__(self):
            raise RuntimeError("db down")

    original = exec_log_service._session_factory
    monkeypatch.setattr(exec_log_service, "_session_factory", _BadFactory())
    try:
        # Should not raise even though no db is supplied and the factory blows.
        result = record_execution(
            action_type=ACTION_TYPE_TASK,
            action_name="unit.never_raise",
            status=EXECUTION_STATUS_FAILED,
        )
        assert result is None
    finally:
        exec_log_service._session_factory = original


# ---------------------------------------------------------------------------
# Notification instrumentation
# ---------------------------------------------------------------------------


def test_create_notification_writes_execution_log(db, citizen_user):
    from app.services.notification_service import create_notification

    create_notification(
        db=db,
        user_id=citizen_user.id,
        notification_type=NotificationType.GENERAL,
        title="hi",
        message="there",
        entity_type="complaint",
        entity_id=99,
    )
    row = (
        db.query(ExecutionLog)
        .filter_by(action_type=ACTION_TYPE_NOTIFICATION, action_name="create_notification")
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_SUCCESS
    assert row.user_id == citizen_user.id
    assert row.entity_type == "complaint"
    assert row.entity_id == 99


# ---------------------------------------------------------------------------
# Automation engine instrumentation
# ---------------------------------------------------------------------------


def _make_automation(db, name: str, actions_json: str, conditions_json: str = "[]"):
    auto = Automation(
        name=name,
        trigger=AutomationTrigger.COMPLAINT_CREATED,
        conditions=conditions_json,
        actions=actions_json,
        enabled=True,
    )
    db.add(auto)
    db.commit()
    db.refresh(auto)
    return auto


def test_automation_action_success_logged(db, director_user):
    import json as _json

    automation = _make_automation(
        db,
        "log-success",
        _json.dumps(
            [
                {
                    "type": "notification",
                    "params": {
                        "user_id": director_user.id,
                        "title": "hello",
                        "message": "world",
                    },
                }
            ]
        ),
    )
    from app.services.automation_engine import run_automation

    report = run_automation(db, automation, {"complaint": {"id": 1}})
    assert report["actions_executed"] == 1

    row = (
        db.query(ExecutionLog)
        .filter_by(
            action_type=ACTION_TYPE_AUTOMATION,
            action_name="automation.action.notification",
        )
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_SUCCESS
    assert row.entity_type == "automation"
    assert row.entity_id == automation.id


def test_automation_unknown_action_logged_as_failed(db):
    import json as _json

    automation = _make_automation(
        db, "log-unknown", _json.dumps([{"type": "does_not_exist", "params": {}}])
    )
    from app.services.automation_engine import run_automation

    run_automation(db, automation, {})

    row = (
        db.query(ExecutionLog)
        .filter_by(
            action_type=ACTION_TYPE_AUTOMATION,
            action_name="automation.action.does_not_exist",
        )
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_FAILED
    assert "unknown action type" in (row.error or "")


def test_automation_action_failure_logged(db):
    import json as _json

    # email action without to_email raises ValueError inside the handler.
    automation = _make_automation(
        db, "log-fail", _json.dumps([{"type": "email", "params": {}}])
    )
    from app.services.automation_engine import run_automation

    run_automation(db, automation, {})

    row = (
        db.query(ExecutionLog)
        .filter_by(
            action_type=ACTION_TYPE_AUTOMATION,
            action_name="automation.action.email",
        )
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_FAILED
    assert "to_email" in (row.error or "")


# ---------------------------------------------------------------------------
# Email service instrumentation
# ---------------------------------------------------------------------------


def test_email_send_skipped_when_smtp_disabled(db, monkeypatch):
    from app.core.config import settings
    from app.services.email_service import _send_email_sync

    monkeypatch.setattr(settings, "SMTP_ENABLED", False, raising=False)

    sent = _send_email_sync("a@b.c", "subj-disabled", "<p/>")
    assert sent is False

    row = (
        db.query(ExecutionLog)
        .filter_by(action_type=ACTION_TYPE_EMAIL, action_name="email.send")
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_SKIPPED
    assert "smtp_disabled" in (row.payload or "")


# ---------------------------------------------------------------------------
# Background job instrumentation
# ---------------------------------------------------------------------------


def test_pdf_task_skipped_when_contract_missing(db):
    from app.jobs.tasks import generate_contract_pdf_task

    # contract_id 999_999 doesn't exist.
    result = generate_contract_pdf_task.apply(args=(999999,)).get()
    assert result is None

    row = (
        db.query(ExecutionLog)
        .filter_by(
            action_type=ACTION_TYPE_TASK,
            action_name="dummar.contracts.generate_pdf",
        )
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_SKIPPED
    assert row.entity_id == 999999


def test_intelligence_task_skipped_when_doc_missing(db, director_user):
    from app.jobs.tasks import process_contract_document_task

    result = process_contract_document_task.apply(
        args=(123456, "/tmp/no.pdf", director_user.id)
    ).get()
    assert result is False

    row = (
        db.query(ExecutionLog)
        .filter_by(
            action_type=ACTION_TYPE_TASK,
            action_name="dummar.contract_intelligence.process_document",
        )
        .order_by(ExecutionLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.status == EXECUTION_STATUS_SKIPPED
    assert row.user_id == director_user.id


# ---------------------------------------------------------------------------
# API: /execution-logs
# ---------------------------------------------------------------------------


def _seed_logs(db):
    """Insert a small variety of rows so list/filter assertions are meaningful."""
    rows = [
        (ACTION_TYPE_EMAIL, "email.send", EXECUTION_STATUS_SUCCESS),
        (ACTION_TYPE_EMAIL, "email.send", EXECUTION_STATUS_FAILED),
        (ACTION_TYPE_NOTIFICATION, "create_notification", EXECUTION_STATUS_SUCCESS),
        (ACTION_TYPE_AUTOMATION, "automation.action.email", EXECUTION_STATUS_FAILED),
        (ACTION_TYPE_TASK, "dummar.email.send", EXECUTION_STATUS_SUCCESS),
    ]
    for atype, aname, status in rows:
        record_execution(
            action_type=atype, action_name=aname, status=status, db=db
        )


def test_list_requires_director(client, field_token, db):
    _seed_logs(db)
    resp = client.get("/execution-logs/", headers=_auth_headers(field_token))
    assert resp.status_code == 403


def test_list_returns_logs_for_director(client, director_token, db):
    _seed_logs(db)
    resp = client.get("/execution-logs/", headers=_auth_headers(director_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] >= 5
    assert len(body["items"]) >= 5
    # newest first
    timestamps = [item["created_at"] for item in body["items"] if item["created_at"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_filters_by_action_type(client, director_token, db):
    _seed_logs(db)
    resp = client.get(
        "/execution-logs/",
        params={"action_type": ACTION_TYPE_EMAIL},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] >= 2
    assert all(item["action_type"] == ACTION_TYPE_EMAIL for item in body["items"])


def test_list_filters_by_status(client, director_token, db):
    _seed_logs(db)
    resp = client.get(
        "/execution-logs/",
        params={"status": EXECUTION_STATUS_FAILED},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] >= 2
    assert all(item["status"] == EXECUTION_STATUS_FAILED for item in body["items"])


def test_list_pagination(client, director_token, db):
    _seed_logs(db)
    resp = client.get(
        "/execution-logs/",
        params={"limit": 2, "skip": 0},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total_count"] >= 5


def test_list_respects_since_filter(client, director_token, db):
    # A row from the distant past shouldn't appear when since=now.
    old = datetime(2000, 1, 1, tzinfo=timezone.utc)
    record_execution(
        action_type=ACTION_TYPE_TASK,
        action_name="ancient",
        status=EXECUTION_STATUS_SUCCESS,
        started_at=old,
        finished_at=old,
        db=db,
    )
    # Force the row's created_at to the same old date.
    db.query(ExecutionLog).filter_by(action_name="ancient").update(
        {ExecutionLog.created_at: old}
    )
    db.commit()

    record_execution(
        action_type=ACTION_TYPE_TASK,
        action_name="recent",
        status=EXECUTION_STATUS_SUCCESS,
        db=db,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    resp = client.get(
        "/execution-logs/",
        params={"since": cutoff.isoformat()},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    names = [item["action_name"] for item in resp.json()["items"]]
    assert "recent" in names
    assert "ancient" not in names


def test_summary_endpoint(client, director_token, db):
    _seed_logs(db)
    resp = client.get("/execution-logs/summary", headers=_auth_headers(director_token))
    assert resp.status_code == 200
    body = resp.json()
    assert "by_action_type" in body
    by = body["by_action_type"]
    assert ACTION_TYPE_EMAIL in by
    assert by[ACTION_TYPE_EMAIL].get(EXECUTION_STATUS_SUCCESS, 0) >= 1
    assert by[ACTION_TYPE_EMAIL].get(EXECUTION_STATUS_FAILED, 0) >= 1


def test_summary_requires_director(client, field_token, db):
    _seed_logs(db)
    resp = client.get(
        "/execution-logs/summary", headers=_auth_headers(field_token)
    )
    assert resp.status_code == 403
