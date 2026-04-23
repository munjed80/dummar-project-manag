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


def test_settings_get_seeds_defaults(client, db):
    resp = client.get("/settings/")
    assert resp.status_code == 200
    data = resp.json()
    assert "project" in data
    assert "organization" in data
    assert "defaults" in data


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
