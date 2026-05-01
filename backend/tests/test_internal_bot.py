from tests.conftest import _auth_headers
from app.models.complaint import Complaint, ComplaintType, ComplaintStatus, ComplaintPriority
from app.models.task import Task, TaskStatus, TaskPriority, TaskSourceType
from app.models.audit import AuditLog
from app.models.project import Project, ProjectStatus


def test_internal_bot_supports_natural_language_and_audit(client, director_token, db, sample_location):
    complaint = Complaint(
        tracking_number="CMP-BOT-1",
        full_name="Tester",
        phone="0999999999",
        complaint_type=ComplaintType.WATER,
        description="test",
        status=ComplaintStatus.NEW,
        location_id=sample_location.id,
    )
    db.add(complaint)
    db.commit()

    resp = client.post(
        "/internal-bot/query",
        json={"question": "اعطني ملخص الشكاوى", "location_id": sample_location.id, "days": 30},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "complaints_summary"
    assert isinstance(data["data"], list)

    audit = db.query(AuditLog).filter(AuditLog.action == "internal_bot_query").first()
    assert audit is not None


def test_internal_bot_tasks_with_project_filter(client, director_token, db):
    p1 = Project(title="P1", code="P-1", status=ProjectStatus.ACTIVE)
    p2 = Project(title="P2", code="P-2", status=ProjectStatus.ACTIVE)
    db.add_all([p1, p2])
    db.commit()

    db.add(
        Task(
            title="t1",
            description="d1",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            project_id=p1.id,
        )
    )
    db.add(
        Task(
            title="t2",
            description="d2",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            project_id=p2.id,
        )
    )
    db.commit()

    resp = client.post(
        "/internal-bot/query",
        json={"intent": "tasks_summary", "project_id": p1.id, "days": 60},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    statuses = {row["status"]: row["count"] for row in resp.json()["data"]}
    assert statuses.get("pending") == 1
    assert statuses.get("completed") in (None, 0)


# ── Phase 3: context-aware analysis ──────────────────────────────────────────


def _make_complaint(db, **kwargs):
    base = dict(
        tracking_number="CTX-BOT-1",
        full_name="Tester",
        phone="0991111111",
        complaint_type=ComplaintType.WATER,
        description="leak",
        status=ComplaintStatus.NEW,
    )
    base.update(kwargs)
    c = Complaint(**base)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_internal_bot_context_complaint_returns_structured_analysis(client, director_token, db):
    complaint = _make_complaint(
        db,
        tracking_number="CTX-BOT-100",
        status=ComplaintStatus.NEW,
    )
    resp = client.post(
        "/internal-bot/query",
        json={"context_type": "complaint", "context_id": complaint.id},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["intent"] == "context_analysis"
    assert body["context_type"] == "complaint"
    assert body["context_id"] == complaint.id
    assert body["risk_level"] in ("low", "medium", "high")
    assert isinstance(body["key_points"], list) and body["key_points"]
    assert isinstance(body["recommended_actions"], list) and body["recommended_actions"]
    assert isinstance(body["related_items"], list)
    assert isinstance(body["data"], list) and body["data"]
    payload = body["data"][0]
    assert payload["complaint"]["tracking_number"] == "CTX-BOT-100"


def test_internal_bot_context_includes_task_and_thread(client, director_token, db, director_user):
    from app.models.internal_message import Message, MessageThread, MessageThreadParticipant, MessageThreadType

    complaint = _make_complaint(
        db,
        tracking_number="CTX-BOT-200",
        status=ComplaintStatus.IN_PROGRESS,
        priority=ComplaintPriority.HIGH,
    )
    task = Task(
        title="إصلاح تسريب",
        description="d",
        source_type=TaskSourceType.COMPLAINT,
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        complaint_id=complaint.id,
    )
    db.add(task)

    thread = MessageThread(
        title="نقاش",
        thread_type=MessageThreadType.GROUP,
        created_by_user_id=director_user.id,
        context_type="complaint",
        context_id=complaint.id,
    )
    db.add(thread)
    db.flush()
    db.add(MessageThreadParticipant(thread_id=thread.id, user_id=director_user.id))
    db.add(Message(thread_id=thread.id, sender_user_id=director_user.id, body="أرسلت الفريق"))
    db.add(Message(thread_id=thread.id, sender_user_id=director_user.id, body="بانتظار التقرير"))
    db.commit()

    resp = client.post(
        "/internal-bot/query",
        json={"context_type": "complaint", "context_id": complaint.id},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    payload = body["data"][0]
    assert payload["task"]["id"] == task.id
    assert payload["thread"]["message_count"] == 2
    assert len(payload["thread"]["last_messages"]) == 2
    related_types = {item["type"] for item in body["related_items"]}
    assert "task" in related_types
    assert "message_thread" in related_types


def test_internal_bot_context_404_when_complaint_missing(client, director_token):
    resp = client.post(
        "/internal-bot/query",
        json={"context_type": "complaint", "context_id": 999999},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 404


def test_internal_bot_context_rejects_unsupported_type(client, director_token):
    resp = client.post(
        "/internal-bot/query",
        json={"context_type": "contract", "context_id": 1},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 400


def test_internal_bot_context_requires_both_fields(client, director_token):
    resp = client.post(
        "/internal-bot/query",
        json={"context_type": "complaint"},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 422
