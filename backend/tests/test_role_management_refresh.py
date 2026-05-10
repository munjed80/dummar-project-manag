"""Permission tests for the user/role-management refresh:

  * complaints_officer (رئيس القسم الفني) can manage executive teams
    (create / update) but cannot delete them.
  * investment_manager (مكتب الاستثمار) can reach the contract intelligence
    center.
  * project_director self-edit returns the updated full_name (regression
    test for the user-edit / cached_user bug).
"""
import pytest

from app.models.user import UserRole
from app.models.team import Team, TeamType


def _login(client, username, password="testpass123"):
    resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _create_user(db, username, role):
    from app.core.security import get_password_hash
    from app.models.user import User

    u = User(
        username=username,
        full_name=f"Test {username}",
        hashed_password=get_password_hash("testpass123"),
        role=role,
        is_active=1,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ──────────────────────────────────────────────────────────────────────────
# complaints_officer / رئيس القسم الفني — team management
# ──────────────────────────────────────────────────────────────────────────


def test_complaints_officer_can_create_team(client, db):
    _create_user(db, "co_user", UserRole.COMPLAINTS_OFFICER)
    token = _login(client, "co_user")
    resp = client.post(
        "/teams/",
        json={"name": "Repair Team", "team_type": "internal_team", "is_active": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Repair Team"


def test_complaints_officer_can_update_team(client, db):
    _create_user(db, "co_user2", UserRole.COMPLAINTS_OFFICER)
    token = _login(client, "co_user2")
    t = Team(name="Old", team_type=TeamType.INTERNAL_TEAM, is_active=True)
    db.add(t)
    db.commit()
    db.refresh(t)
    resp = client.put(
        f"/teams/{t.id}",
        json={"name": "New"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "New"


def test_complaints_officer_cannot_delete_team(client, db):
    """Team deletion remains director-only — complaints_officer must get 403."""
    _create_user(db, "co_user3", UserRole.COMPLAINTS_OFFICER)
    token = _login(client, "co_user3")
    t = Team(name="Doomed", team_type=TeamType.INTERNAL_TEAM, is_active=True)
    db.add(t)
    db.commit()
    db.refresh(t)
    resp = client.delete(
        f"/teams/{t.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_complaints_officer_has_task_assign_permission_in_matrix(client, db):
    _create_user(db, "co_user4", UserRole.COMPLAINTS_OFFICER)
    token = _login(client, "co_user4")
    resp = client.get(
        "/auth/me/permissions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    perms = resp.json()["permissions"]
    assert {"resource": "task", "action": "assign"} in perms


# ──────────────────────────────────────────────────────────────────────────
# investment_manager / مكتب الاستثمار — contract intelligence access
# ──────────────────────────────────────────────────────────────────────────


def test_investment_manager_can_access_contract_intelligence_dashboard(client, db):
    _create_user(db, "inv_office", UserRole.INVESTMENT_MANAGER)
    token = _login(client, "inv_office")
    resp = client.get(
        "/contract-intelligence/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 200 (dashboard returned) is the success criterion. We assert NOT 403
    # so any internal pipeline error doesn't mask the permission regression.
    assert resp.status_code != 403, resp.text


def test_field_team_still_blocked_from_contract_intelligence(client, field_token):
    resp = client.get(
        "/contract-intelligence/dashboard",
        headers={"Authorization": f"Bearer {field_token}"},
    )
    assert resp.status_code == 403


# ──────────────────────────────────────────────────────────────────────────
# user-edit bug regression — director self-edit returns updated full_name
# ──────────────────────────────────────────────────────────────────────────


def test_director_self_edit_returns_updated_full_name(client, director_token, director_user):
    resp = client.put(
        f"/users/{director_user.id}",
        json={"full_name": "د. ضياء"},
        headers={"Authorization": f"Bearer {director_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_name"] == "د. ضياء"

    # Subsequent GET must reflect the persisted value (no stale cache).
    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {director_token}"}
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "د. ضياء"
