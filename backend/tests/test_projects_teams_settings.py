"""
Tests for Projects, Teams, and Settings endpoints.
"""
import pytest
from app.models.user import UserRole
from app.models.project import ProjectStatus
from app.models.team import TeamType
from app.models.complaint import ComplaintStatus


def test_create_project(client, director_token, db):
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.post(
        "/projects/",
        json={
            "title": "Test Project",
            "code": "PROJ-001",
            "description": "Test project description",
            "status": "active",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Project"
    assert data["code"] == "PROJ-001"
    assert data["status"] == "active"


def test_list_projects(client, director_token, db):
    from app.models.project import Project
    
    p1 = Project(title="Project 1", code="P1", status=ProjectStatus.ACTIVE)
    p2 = Project(title="Project 2", code="P2", status=ProjectStatus.PLANNED)
    db.add_all([p1, p2])
    db.commit()
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get("/projects/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2
    assert len(data["items"]) == 2


def test_get_project_by_id(client, director_token, db):
    from app.models.project import Project
    
    p = Project(title="Test Project", code="TP1", status=ProjectStatus.ACTIVE)
    db.add(p)
    db.commit()
    db.refresh(p)
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get(f"/projects/{p.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Project"


def test_update_project(client, director_token, db):
    from app.models.project import Project
    
    p = Project(title="Old Title", code="P1", status=ProjectStatus.ACTIVE)
    db.add(p)
    db.commit()
    db.refresh(p)
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.put(
        f"/projects/{p.id}",
        json={"title": "New Title", "status": "on_hold"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    assert data["status"] == "on_hold"


def test_delete_project(client, director_token, db):
    from app.models.project import Project
    
    p = Project(title="To Delete", code="DEL1", status=ProjectStatus.ACTIVE)
    db.add(p)
    db.commit()
    db.refresh(p)
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.delete(f"/projects/{p.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Project deleted successfully"


def test_create_team(client, director_token, db):
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.post(
        "/teams/",
        json={
            "name": "Alpha Team",
            "team_type": "internal_team",
            "contact_name": "John Doe",
            "is_active": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Alpha Team"
    assert data["team_type"] == "internal_team"
    assert data["is_active"] is True


def test_list_teams(client, director_token, db):
    from app.models.team import Team
    
    t1 = Team(name="Team 1", team_type=TeamType.INTERNAL_TEAM, is_active=True)
    t2 = Team(name="Team 2", team_type=TeamType.CONTRACTOR, is_active=False)
    db.add_all([t1, t2])
    db.commit()
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get("/teams/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2


def test_list_active_teams(client, director_token, db):
    from app.models.team import Team
    
    t1 = Team(name="Active Team", team_type=TeamType.INTERNAL_TEAM, is_active=True)
    t2 = Team(name="Inactive Team", team_type=TeamType.CONTRACTOR, is_active=False)
    db.add_all([t1, t2])
    db.commit()
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get("/teams/active", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Active Team"


def test_update_team(client, director_token, db):
    from app.models.team import Team
    
    t = Team(name="Old Name", team_type=TeamType.INTERNAL_TEAM, is_active=True)
    db.add(t)
    db.commit()
    db.refresh(t)
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.put(
        f"/teams/{t.id}",
        json={"name": "New Name", "is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["is_active"] is False


def test_settings_get_seeds_defaults(client, director_token, db):
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get("/settings/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "project" in data
    assert "organization" in data
    assert "defaults" in data


def test_settings_get_requires_auth(client, db):
    """Anonymous callers must not be able to read settings."""
    resp = client.get("/settings/")
    assert resp.status_code in (401, 403)


def test_settings_update_privileged(client, director_token, db):
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.put(
        "/settings/",
        json={
            "items": [
                {
                    "key": "project.name_ar",
                    "value": "مشروع دمّر المحدث",
                    "value_type": "string",
                    "category": "project",
                    "description": "اسم المشروع",
                }
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Settings updated successfully"


def test_settings_update_non_privileged_forbidden(client, field_token, db):
    headers = {"Authorization": f"Bearer {field_token}"}
    resp = client.put(
        "/settings/",
        json={"items": [{"key": "test.key", "value": "test", "value_type": "string", "category": "test"}]},
        headers=headers,
    )
    assert resp.status_code == 403


def test_create_task_from_complaint(client, director_token, db, sample_area):
    from app.models.complaint import Complaint, ComplaintType
    from app.models.task import Task
    
    # Create a complaint
    complaint = Complaint(
        tracking_number="CMP12345678",
        full_name="Test User",
        phone="0991234567",
        complaint_type=ComplaintType.ROADS,
        description="Pothole in the road",
        area_id=sample_area.id,
        status=ComplaintStatus.NEW,
        priority="high",
        latitude=33.5,
        longitude=36.3,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.post(
        f"/complaints/{complaint.id}/create-task",
        json={
            "title": "Fix pothole",
            "description": "Repair pothole from complaint",
            "priority": "high",
            "assigned_to_id": 1,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Fix pothole"
    assert data["source_type"] == "complaint"
    assert data["complaint_id"] == complaint.id
    
    # Verify complaint status changed to ASSIGNED
    db.refresh(complaint)
    assert complaint.status == ComplaintStatus.ASSIGNED
    
    # Verify task was created
    task = db.query(Task).filter(Task.id == data["id"]).first()
    assert task is not None
    assert task.complaint_id == complaint.id


# ── Cross-entity filter tests (project_id, team_id) ──

def test_list_complaints_filtered_by_project(client, director_token, db, sample_area):
    """Complaints list endpoint must accept ?project_id and only return complaints linked to that project."""
    from app.models.complaint import Complaint, ComplaintType
    from app.models.project import Project

    p1 = Project(title="Proj A", code="PA", status=ProjectStatus.ACTIVE)
    p2 = Project(title="Proj B", code="PB", status=ProjectStatus.ACTIVE)
    db.add_all([p1, p2])
    db.commit()

    c_a = Complaint(
        tracking_number="CMPP00001", full_name="A", phone="0991111111",
        complaint_type=ComplaintType.ROADS, description="x", status=ComplaintStatus.NEW,
        area_id=sample_area.id, project_id=p1.id,
    )
    c_b = Complaint(
        tracking_number="CMPP00002", full_name="B", phone="0992222222",
        complaint_type=ComplaintType.ROADS, description="x", status=ComplaintStatus.NEW,
        area_id=sample_area.id, project_id=p2.id,
    )
    c_none = Complaint(
        tracking_number="CMPP00003", full_name="C", phone="0993333333",
        complaint_type=ComplaintType.ROADS, description="x", status=ComplaintStatus.NEW,
        area_id=sample_area.id,
    )
    db.add_all([c_a, c_b, c_none])
    db.commit()

    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get(f"/complaints/?project_id={p1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["tracking_number"] == "CMPP00001"


def test_list_tasks_filtered_by_project_and_team(client, director_token, db):
    """Tasks list endpoint must accept ?project_id and ?team_id."""
    from app.models.task import Task, TaskStatus, TaskPriority
    from app.models.project import Project
    from app.models.team import Team

    p1 = Project(title="Proj T", code="PT1", status=ProjectStatus.ACTIVE)
    t_team = Team(name="Crew A", team_type=TeamType.FIELD_CREW, is_active=True)
    other_team = Team(name="Crew B", team_type=TeamType.FIELD_CREW, is_active=True)
    db.add_all([p1, t_team, other_team])
    db.commit()

    t1 = Task(title="T1", description="d", status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
              project_id=p1.id, team_id=t_team.id)
    t2 = Task(title="T2", description="d", status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
              project_id=p1.id, team_id=other_team.id)
    t3 = Task(title="T3", description="d", status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM)
    db.add_all([t1, t2, t3])
    db.commit()

    headers = {"Authorization": f"Bearer {director_token}"}

    # Filter by project only
    resp = client.get(f"/tasks/?project_id={p1.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 2

    # Filter by team only
    resp = client.get(f"/tasks/?team_id={t_team.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["title"] == "T1"

    # Filter by both
    resp = client.get(f"/tasks/?project_id={p1.id}&team_id={other_team.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["title"] == "T2"


def test_list_contracts_filtered_by_project(client, director_token, db, director_user):
    """Contracts list endpoint must accept ?project_id."""
    from datetime import date
    from decimal import Decimal
    from app.models.contract import Contract, ContractType, ContractStatus
    from app.models.project import Project

    p1 = Project(title="Proj C", code="PC1", status=ProjectStatus.ACTIVE)
    p2 = Project(title="Proj D", code="PC2", status=ProjectStatus.ACTIVE)
    db.add_all([p1, p2])
    db.commit()

    c1 = Contract(
        contract_number="C-PRJ-1", title="X", contractor_name="Y",
        contract_type=ContractType.CONSTRUCTION, contract_value=Decimal("1000"),
        start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
        scope_description="scope", status=ContractStatus.DRAFT,
        created_by_id=director_user.id, project_id=p1.id,
    )
    c2 = Contract(
        contract_number="C-PRJ-2", title="X2", contractor_name="Y2",
        contract_type=ContractType.MAINTENANCE, contract_value=Decimal("2000"),
        start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
        scope_description="scope", status=ContractStatus.DRAFT,
        created_by_id=director_user.id, project_id=p2.id,
    )
    db.add_all([c1, c2])
    db.commit()

    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get(f"/contracts/?project_id={p1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["contract_number"] == "C-PRJ-1"


def test_list_tasks_filtered_by_complaint(client, director_token, db, sample_area):
    """Tasks list endpoint must accept ?complaint_id so the complaint detail page
    can show the tasks that were created from a given complaint."""
    from app.models.complaint import Complaint, ComplaintType
    from app.models.task import Task, TaskStatus, TaskPriority

    c1 = Complaint(
        tracking_number="CMPLNK001", full_name="X", phone="0991111111",
        complaint_type=ComplaintType.ROADS, description="d",
        status=ComplaintStatus.ASSIGNED, area_id=sample_area.id,
    )
    c2 = Complaint(
        tracking_number="CMPLNK002", full_name="Y", phone="0992222222",
        complaint_type=ComplaintType.ROADS, description="d",
        status=ComplaintStatus.NEW, area_id=sample_area.id,
    )
    db.add_all([c1, c2])
    db.commit()

    t_a = Task(title="A1", description="d", status=TaskStatus.PENDING,
               priority=TaskPriority.MEDIUM, complaint_id=c1.id)
    t_b = Task(title="A2", description="d", status=TaskStatus.IN_PROGRESS,
               priority=TaskPriority.MEDIUM, complaint_id=c1.id)
    t_other = Task(title="B1", description="d", status=TaskStatus.PENDING,
                   priority=TaskPriority.MEDIUM, complaint_id=c2.id)
    t_unrelated = Task(title="N1", description="d", status=TaskStatus.PENDING,
                       priority=TaskPriority.MEDIUM)
    db.add_all([t_a, t_b, t_other, t_unrelated])
    db.commit()

    headers = {"Authorization": f"Bearer {director_token}"}
    resp = client.get(f"/tasks/?complaint_id={c1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2
    titles = sorted(item["title"] for item in data["items"])
    assert titles == ["A1", "A2"]

    # Other complaint returns only its own task
    resp = client.get(f"/tasks/?complaint_id={c2.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 1
    assert resp.json()["items"][0]["title"] == "B1"
