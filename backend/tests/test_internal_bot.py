from tests.conftest import _auth_headers
from app.models.complaint import Complaint, ComplaintType, ComplaintStatus
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
