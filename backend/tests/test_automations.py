"""Tests for the automation engine + CRUD endpoints.

Covers:

* `Automation` model + alembic-equivalent schema (via `Base.metadata.create_all`)
* `AutomationCreate` / `AutomationUpdate` schemas (operator + action validation)
* CRUD endpoints + RBAC (only PROJECT_DIRECTOR can mutate; internal staff can read)
* `_evaluate_condition` for every supported operator
* Action handlers: `notification`, `create_task` (incl. templating)
* `fire_event` integrates with real complaint/task endpoints
* Disabled automations are skipped
* A failing rule does not block the others
* `last_run_at` / `run_count` / `last_error` are persisted
"""

from __future__ import annotations

import json

import pytest

from app.models.automation import Automation, AutomationTrigger
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User, UserRole
from app.services.automation_engine import (
    _evaluate_condition,
    _resolve_template,
    fire_event,
    run_automation,
)

from tests.conftest import _auth_headers, _create_user, _login


# ---------------------------------------------------------------------------
# Condition evaluator unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator,value,actual,expected_result",
    [
        ("eq", "high", "high", True),
        ("eq", "high", "low", False),
        ("ne", "high", "low", True),
        ("ne", "high", "high", False),
        ("in", ["a", "b"], "a", True),
        ("in", ["a", "b"], "c", False),
        ("not_in", ["a", "b"], "c", True),
        ("not_in", ["a", "b"], "a", False),
        ("contains", "abc", "xxabcxx", True),
        ("contains", "abc", "xyz", False),
        ("gt", 5, 10, True),
        ("gt", 5, 3, False),
        ("lt", 5, 3, True),
        ("lt", 5, 10, False),
    ],
)
def test_evaluate_condition_operators(operator, value, actual, expected_result):
    ctx = {"obj": {"field": actual}}
    cond = {"field": "obj.field", "operator": operator, "value": value}
    assert _evaluate_condition(cond, ctx) is expected_result


def test_evaluate_condition_unknown_field_returns_false():
    assert (
        _evaluate_condition(
            {"field": "missing", "operator": "eq", "value": "x"}, {}
        )
        is False
    )


def test_evaluate_condition_eq_to_none_matches_missing():
    # Missing path resolves to None — eq None is meaningful.
    assert (
        _evaluate_condition(
            {"field": "missing", "operator": "eq", "value": None}, {}
        )
        is True
    )


def test_evaluate_condition_unknown_operator_is_false():
    assert (
        _evaluate_condition({"field": "x", "operator": "regex", "value": ".*"}, {"x": "1"})
        is False
    )


# ---------------------------------------------------------------------------
# Template resolver
# ---------------------------------------------------------------------------


def test_resolve_template_substitutes_dotted_paths():
    ctx = {"complaint": {"id": 7, "tracking_number": "CMP123"}}
    out = _resolve_template(
        "Complaint {complaint.tracking_number} (id={complaint.id})", ctx
    )
    assert out == "Complaint CMP123 (id=7)"


def test_resolve_template_passes_through_non_strings():
    assert _resolve_template(42, {}) == 42
    assert _resolve_template(None, {}) is None
    assert _resolve_template({"a": 1}, {}) == {"a": 1}


def test_resolve_template_missing_field_renders_empty():
    assert _resolve_template("[{a.b}]", {}) == "[]"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_automation_schema_rejects_unknown_operator(client, director_token):
    resp = client.post(
        "/automations/",
        headers=_auth_headers(director_token),
        json={
            "name": "bad",
            "trigger": "complaint_created",
            "conditions": [{"field": "complaint.id", "operator": "regex", "value": "."}],
            "actions": [{"type": "notification", "params": {"user_id": 1}}],
        },
    )
    assert resp.status_code == 422


def test_automation_schema_rejects_unknown_action_type(client, director_token):
    resp = client.post(
        "/automations/",
        headers=_auth_headers(director_token),
        json={
            "name": "bad",
            "trigger": "complaint_created",
            "actions": [{"type": "shell", "params": {"cmd": "rm -rf /"}}],
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# CRUD endpoints + RBAC
# ---------------------------------------------------------------------------


def _make_payload(**overrides):
    base = {
        "name": "Notify on new complaint",
        "description": "test",
        "trigger": "complaint_created",
        "conditions": [
            {
                "field": "complaint.complaint_type",
                "operator": "eq",
                "value": "infrastructure",
            }
        ],
        "actions": [
            {
                "type": "notification",
                "params": {
                    "user_id": 1,
                    "title": "New complaint",
                    "message": "Tracking {complaint.tracking_number}",
                },
            }
        ],
        "enabled": True,
    }
    base.update(overrides)
    return base


def test_create_list_get_update_delete_automation(client, director_user, director_token):
    create = client.post(
        "/automations/",
        headers=_auth_headers(director_token),
        json=_make_payload(),
    )
    assert create.status_code == 201, create.text
    auto_id = create.json()["id"]
    assert create.json()["created_by_id"] == director_user.id

    listed = client.get("/automations/", headers=_auth_headers(director_token))
    assert listed.status_code == 200
    assert any(a["id"] == auto_id for a in listed.json())

    got = client.get(f"/automations/{auto_id}", headers=_auth_headers(director_token))
    assert got.status_code == 200
    assert got.json()["name"] == "Notify on new complaint"
    assert got.json()["conditions"][0]["operator"] == "eq"

    upd = client.put(
        f"/automations/{auto_id}",
        headers=_auth_headers(director_token),
        json={"enabled": False, "name": "renamed"},
    )
    assert upd.status_code == 200
    assert upd.json()["enabled"] is False
    assert upd.json()["name"] == "renamed"

    deleted = client.delete(
        f"/automations/{auto_id}", headers=_auth_headers(director_token)
    )
    assert deleted.status_code == 204
    missing = client.get(
        f"/automations/{auto_id}", headers=_auth_headers(director_token)
    )
    assert missing.status_code == 404


def test_non_director_cannot_create_automation(client, field_token):
    resp = client.post(
        "/automations/",
        headers=_auth_headers(field_token),
        json=_make_payload(),
    )
    assert resp.status_code == 403


def test_internal_staff_can_list_automations(client, director_token, field_token):
    client.post(
        "/automations/",
        headers=_auth_headers(director_token),
        json=_make_payload(),
    )
    resp = client.get("/automations/", headers=_auth_headers(field_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_unauthenticated_cannot_access_automations(client):
    assert client.get("/automations/").status_code in (401, 403)


# ---------------------------------------------------------------------------
# Engine integration: fire_event from real complaint/task endpoints
# ---------------------------------------------------------------------------


def _create_automation_row(db, **overrides) -> Automation:
    payload = _make_payload(**overrides)
    row = Automation(
        name=payload["name"],
        description=payload.get("description"),
        trigger=AutomationTrigger(payload["trigger"]),
        conditions=json.dumps(payload["conditions"]),
        actions=json.dumps(payload["actions"]),
        enabled=payload["enabled"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_complaint_created_fires_notification_action(client, db, director_user):
    # Director (id from fixture) will receive the notification.
    _create_automation_row(
        db,
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "Auto: complaint",
                    "message": "Tracking {complaint.tracking_number}",
                    "entity_type": "complaint",
                    "entity_id": "{complaint.id}",
                },
            }
        ],
    )

    resp = client.post(
        "/complaints/",
        json={
            "full_name": "Tester",
            "phone": "0900000000",
            "complaint_type": "infrastructure",
            "description": "auto trigger",
        },
    )
    assert resp.status_code == 200, resp.text
    tracking = resp.json()["tracking_number"]
    complaint_id = resp.json()["id"]

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == director_user.id)
        .all()
    )
    assert any(
        n.title == "Auto: complaint" and tracking in n.message for n in notifs
    )
    matching = [n for n in notifs if n.title == "Auto: complaint"][0]
    assert matching.entity_type == "complaint"
    assert matching.entity_id == complaint_id


def test_complaint_created_skips_when_condition_does_not_match(
    client, db, director_user
):
    _create_automation_row(
        db,
        conditions=[
            {
                "field": "complaint.complaint_type",
                "operator": "eq",
                "value": "electricity",  # we'll submit infrastructure
            }
        ],
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "Should NOT appear",
                    "message": "no",
                },
            }
        ],
    )

    client.post(
        "/complaints/",
        json={
            "full_name": "Tester",
            "phone": "0900000000",
            "complaint_type": "infrastructure",
            "description": "no match",
        },
    )

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == director_user.id)
        .all()
    )
    assert not any(n.title == "Should NOT appear" for n in notifs)


def test_disabled_automation_is_skipped(client, db, director_user):
    _create_automation_row(
        db,
        enabled=False,
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "Disabled rule",
                    "message": "x",
                },
            }
        ],
    )

    client.post(
        "/complaints/",
        json={
            "full_name": "Tester",
            "phone": "0900000000",
            "complaint_type": "infrastructure",
            "description": "disabled test",
        },
    )

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == director_user.id)
        .all()
    )
    assert not any(n.title == "Disabled rule" for n in notifs)


def test_complaint_status_changed_fires_create_task_action(
    client, db, director_user, director_token
):
    # 1. Submit complaint as citizen
    create = client.post(
        "/complaints/",
        json={
            "full_name": "Tester",
            "phone": "0900000000",
            "complaint_type": "roads",
            "description": "needs follow-up task",
        },
    )
    complaint_id = create.json()["id"]
    tracking = create.json()["tracking_number"]

    # 2. Configure automation: when complaint becomes UNDER_REVIEW, create a task.
    _create_automation_row(
        db,
        trigger="complaint_status_changed",
        conditions=[
            {"field": "new_status", "operator": "eq", "value": "under_review"}
        ],
        actions=[
            {
                "type": "create_task",
                "params": {
                    "title": "Investigate {complaint.tracking_number}",
                    "description": "follow up",
                    "complaint_id": "{complaint.id}",
                    "priority": "high",
                },
            }
        ],
    )

    # 3. Director updates the complaint status → triggers automation.
    resp = client.put(
        f"/complaints/{complaint_id}",
        headers=_auth_headers(director_token),
        json={"status": "under_review"},
    )
    assert resp.status_code == 200, resp.text

    tasks = db.query(Task).filter(Task.complaint_id == complaint_id).all()
    assert any(t.title == f"Investigate {tracking}" for t in tasks)
    auto_task = [t for t in tasks if t.title == f"Investigate {tracking}"][0]
    assert auto_task.priority.value == "high"


def test_failing_action_does_not_block_other_automations(
    client, db, director_user
):
    # First automation: invalid action params (missing user_id) → fails.
    _create_automation_row(
        db,
        name="bad rule",
        actions=[
            {
                "type": "notification",
                "params": {  # no user_id and no template
                    "title": "boom",
                    "message": "x",
                },
            }
        ],
    )
    # Second automation: valid → should still run.
    _create_automation_row(
        db,
        name="good rule",
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "Good rule fired",
                    "message": "ok",
                },
            }
        ],
    )

    client.post(
        "/complaints/",
        json={
            "full_name": "Tester",
            "phone": "0900000000",
            "complaint_type": "infrastructure",
            "description": "isolation test",
        },
    )

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == director_user.id)
        .all()
    )
    assert any(n.title == "Good rule fired" for n in notifs)

    # Bad rule must have recorded its error.
    bad = db.query(Automation).filter(Automation.name == "bad rule").first()
    assert bad.last_error and "user_id" in bad.last_error
    assert bad.run_count >= 1


def test_run_automation_records_telemetry(db, director_user):
    rule = _create_automation_row(
        db,
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "telemetry",
                    "message": "x",
                },
            }
        ],
    )
    before = rule.run_count
    report = run_automation(
        db, rule, {"complaint": {"complaint_type": "infrastructure"}}
    )
    assert report["matched"] is True
    assert report["actions_executed"] == 1

    db.expire_all()
    refreshed = db.query(Automation).filter(Automation.id == rule.id).first()
    assert refreshed.run_count == before + 1
    assert refreshed.last_run_at is not None
    assert refreshed.last_error is None


# ---------------------------------------------------------------------------
# Manual /test endpoint
# ---------------------------------------------------------------------------


def test_manual_test_endpoint_runs_automation(
    client, db, director_user, director_token
):
    rule = _create_automation_row(
        db,
        conditions=[],  # match anything
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "manual",
                    "message": "ctx",
                },
            }
        ],
    )

    resp = client.post(
        f"/automations/{rule.id}/test",
        headers=_auth_headers(director_token),
        json={"context": {"complaint": {"id": 1}}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matched"] is True
    assert body["actions_executed"] == 1
    assert body["errors"] == []


def test_task_created_fires_notification_action(client, db, director_user, director_token):
    _create_automation_row(
        db,
        trigger="task_created",
        conditions=[],
        actions=[
            {
                "type": "notification",
                "params": {
                    "user_id": director_user.id,
                    "title": "Task {task.id}",
                    "message": "created",
                },
            }
        ],
    )

    from app.models.notification import Notification

    before = db.query(Notification).filter(Notification.user_id == director_user.id).count()

    resp = client.post(
        "/tasks/",
        headers=_auth_headers(director_token),
        json={
            "title": "auto-task-test",
            "description": "task event fan-out",
        },
    )
    assert resp.status_code == 200, resp.text

    after = db.query(Notification).filter(Notification.user_id == director_user.id).count()
    assert after > before
