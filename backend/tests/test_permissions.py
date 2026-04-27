"""Tests for the fine-grained RBAC layer.

Covers:
  * Pure-Python authorize() truth table (no HTTP)
  * user_can_reach_org / scope_query
  * /organization-units CRUD
  * /auth/me/permissions
  * Integration: list scoping, instance 403 vs 404, ownership rules
"""
from __future__ import annotations

import pytest

from app.core import permissions as perms
from app.core.security import get_password_hash
from app.models.complaint import (
    Complaint,
    ComplaintPriority,
    ComplaintStatus,
    ComplaintType,
)
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.organization import OrganizationUnit, OrgLevel
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole
from datetime import date


# ---------------------------------------------------------------------------
# Org hierarchy fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def org_tree(db):
    """Two governorates × two municipalities × two districts each."""
    out = {}
    for g_idx, g_code in enumerate(["GA", "GB"], start=1):
        gov = OrganizationUnit(
            name=f"Governorate {g_code}", code=g_code, level=OrgLevel.GOVERNORATE
        )
        db.add(gov)
        db.commit()
        db.refresh(gov)
        out[f"gov_{g_code.lower()}"] = gov
        for m_idx in (1, 2):
            mun_code = f"{g_code}-M{m_idx}"
            mun = OrganizationUnit(
                name=f"Municipality {mun_code}",
                code=mun_code,
                level=OrgLevel.MUNICIPALITY,
                parent_id=gov.id,
            )
            db.add(mun)
            db.commit()
            db.refresh(mun)
            out[f"mun_{mun_code.lower().replace('-', '_')}"] = mun
            for d_idx in (1, 2):
                dist_code = f"{mun_code}-D{d_idx}"
                dist = OrganizationUnit(
                    name=f"District {dist_code}",
                    code=dist_code,
                    level=OrgLevel.DISTRICT,
                    parent_id=mun.id,
                )
                db.add(dist)
                db.commit()
                db.refresh(dist)
                out[f"dist_{dist_code.lower().replace('-', '_')}"] = dist
    return out


def _make_user(db, username, role, org_unit_id=None):
    u = User(
        username=username,
        full_name=username,
        hashed_password=get_password_hash("testpass123"),
        role=role,
        is_active=1,
        org_unit_id=org_unit_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client, username):
    r = client.post(
        "/auth/login", json={"username": username, "password": "testpass123"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# 1) Unit tests for the pure-Python permission core
# ---------------------------------------------------------------------------


class TestRoleMatrix:
    def test_director_has_every_permission(self):
        assert perms.has_role_permission(
            UserRole.PROJECT_DIRECTOR, perms.ResourceType.CONTRACT, perms.Action.APPROVE
        )
        assert perms.has_role_permission(
            UserRole.PROJECT_DIRECTOR, perms.ResourceType.USER, perms.Action.DELETE
        )

    def test_complaints_officer_cannot_approve_contracts(self):
        assert not perms.has_role_permission(
            UserRole.COMPLAINTS_OFFICER, perms.ResourceType.CONTRACT, perms.Action.APPROVE
        )

    def test_field_team_cannot_delete_tasks(self):
        assert not perms.has_role_permission(
            UserRole.FIELD_TEAM, perms.ResourceType.TASK, perms.Action.DELETE
        )

    def test_field_team_can_read_and_update_tasks(self):
        assert perms.has_role_permission(
            UserRole.FIELD_TEAM, perms.ResourceType.TASK, perms.Action.READ
        )
        assert perms.has_role_permission(
            UserRole.FIELD_TEAM, perms.ResourceType.TASK, perms.Action.UPDATE
        )

    def test_citizen_cannot_create_tasks(self):
        assert not perms.has_role_permission(
            UserRole.CITIZEN, perms.ResourceType.TASK, perms.Action.CREATE
        )


class TestUserCanReachOrg:
    def test_descendant_is_reachable(self, db, org_tree):
        gov = org_tree["gov_ga"]
        dist = org_tree["dist_ga_m1_d1"]
        user = _make_user(db, "u_gov_a", UserRole.AREA_SUPERVISOR, gov.id)
        assert perms.user_can_reach_org(db, user, dist.id)

    def test_sibling_is_not_reachable(self, db, org_tree):
        dist_a = org_tree["dist_ga_m1_d1"]
        dist_b = org_tree["dist_ga_m1_d2"]
        user = _make_user(db, "u_dist_a", UserRole.AREA_SUPERVISOR, dist_a.id)
        assert not perms.user_can_reach_org(db, user, dist_b.id)

    def test_other_governorate_not_reachable(self, db, org_tree):
        gov_a = org_tree["gov_ga"]
        dist_b = org_tree["dist_gb_m1_d1"]
        user = _make_user(db, "u_gov_a2", UserRole.AREA_SUPERVISOR, gov_a.id)
        assert not perms.user_can_reach_org(db, user, dist_b.id)

    def test_null_target_unit_is_visible_to_anyone(self, db, org_tree):
        dist = org_tree["dist_ga_m1_d1"]
        user = _make_user(db, "u_dist_n", UserRole.AREA_SUPERVISOR, dist.id)
        assert perms.user_can_reach_org(db, user, None)

    def test_director_global_reaches_everything(self, db, org_tree):
        director = _make_user(db, "u_dir", UserRole.PROJECT_DIRECTOR, None)
        for unit in org_tree.values():
            assert perms.user_can_reach_org(db, director, unit.id)

    def test_user_without_org_unit_has_global_scope(self, db, org_tree):
        # Lenient default: legacy users without org_unit_id remain global
        user = _make_user(db, "u_legacy", UserRole.AREA_SUPERVISOR, None)
        assert perms.user_scope_unit_ids(db, user) is None


class TestAuthorize:
    def test_inactive_user_denied(self, db, org_tree):
        user = _make_user(db, "u_inactive", UserRole.AREA_SUPERVISOR, None)
        user.is_active = 0
        db.commit()
        assert not perms.authorize(
            db, user, perms.Action.READ, perms.ResourceType.COMPLAINT
        )

    def test_role_without_permission_denied(self, db, org_tree):
        user = _make_user(db, "u_co", UserRole.COMPLAINTS_OFFICER, None)
        assert not perms.authorize(
            db, user, perms.Action.APPROVE, perms.ResourceType.CONTRACT
        )

    def test_field_team_owns_assigned_task(self, db, org_tree):
        dist = org_tree["dist_ga_m1_d1"]
        ft = _make_user(db, "u_ft", UserRole.FIELD_TEAM, dist.id)
        task = Task(
            title="t",
            description="d",
            assigned_to_id=ft.id,
            org_unit_id=dist.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        assert perms.authorize(
            db, ft, perms.Action.UPDATE, perms.ResourceType.TASK, resource=task
        )

    def test_field_team_cannot_update_unassigned_task_in_same_district(
        self, db, org_tree
    ):
        dist = org_tree["dist_ga_m1_d1"]
        ft = _make_user(db, "u_ft2", UserRole.FIELD_TEAM, dist.id)
        someone = _make_user(db, "u_other", UserRole.FIELD_TEAM, dist.id)
        task = Task(
            title="t",
            description="d",
            assigned_to_id=someone.id,
            org_unit_id=dist.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        assert not perms.authorize(
            db, ft, perms.Action.UPDATE, perms.ResourceType.TASK, resource=task
        )

    def test_supervisor_blocked_outside_scope(self, db, org_tree):
        own_dist = org_tree["dist_ga_m1_d1"]
        other_dist = org_tree["dist_ga_m1_d2"]
        sup = _make_user(db, "u_sup", UserRole.AREA_SUPERVISOR, own_dist.id)
        complaint = Complaint(
            tracking_number="CMP00000001",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=other_dist.id,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        assert not perms.authorize(
            db,
            sup,
            perms.Action.UPDATE,
            perms.ResourceType.COMPLAINT,
            resource=complaint,
        )

    def test_complaints_officer_cannot_approve_contract_in_own_unit(
        self, db, org_tree
    ):
        dist = org_tree["dist_ga_m1_d1"]
        co = _make_user(db, "u_co2", UserRole.COMPLAINTS_OFFICER, dist.id)
        director = _make_user(db, "u_dir2", UserRole.PROJECT_DIRECTOR, None)
        contract = Contract(
            contract_number="C-1",
            title="T",
            contractor_name="C",
            contract_type=ContractType.CONSTRUCTION,
            contract_value=1000,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            scope_description="x",
            created_by_id=director.id,
            org_unit_id=dist.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        assert not perms.authorize(
            db,
            co,
            perms.Action.APPROVE,
            perms.ResourceType.CONTRACT,
            resource=contract,
        )


class TestScopeQuery:
    def test_filters_to_subtree(self, db, org_tree):
        gov = org_tree["gov_ga"]
        # Director of gov_ga
        user = _make_user(db, "u_dir_ga", UserRole.PROJECT_DIRECTOR, gov.id)
        # Add complaints in two different governorates
        in_scope = Complaint(
            tracking_number="CMP-IN",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=org_tree["dist_ga_m1_d1"].id,
        )
        out_of_scope = Complaint(
            tracking_number="CMP-OUT",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=org_tree["dist_gb_m1_d1"].id,
        )
        unscoped = Complaint(
            tracking_number="CMP-NULL",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
        )
        db.add_all([in_scope, out_of_scope, unscoped])
        db.commit()

        q = perms.scope_query(db.query(Complaint), db, user, Complaint)
        rows = q.all()
        codes = {c.tracking_number for c in rows}
        assert "CMP-IN" in codes
        assert "CMP-NULL" in codes  # lenient: legacy rows visible
        assert "CMP-OUT" not in codes


# ---------------------------------------------------------------------------
# 2) /organization-units CRUD
# ---------------------------------------------------------------------------


class TestOrganizationUnitsAPI:
    def test_director_can_create_governorate(self, client, db, director_token):
        r = client.post(
            "/organization-units/",
            headers={"Authorization": f"Bearer {director_token}"},
            json={"name": "G", "code": "G-1", "level": "governorate"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["level"] == "governorate"
        assert body["parent_id"] is None

    def test_governorate_requires_no_parent(self, client, db, director_token):
        r = client.post(
            "/organization-units/",
            headers={"Authorization": f"Bearer {director_token}"},
            json={
                "name": "G",
                "code": "G-2",
                "level": "municipality",
                "parent_id": None,
            },
        )
        assert r.status_code == 400

    def test_district_requires_municipality_parent(self, client, db, director_token):
        h = {"Authorization": f"Bearer {director_token}"}
        gov = client.post(
            "/organization-units/",
            headers=h,
            json={"name": "G", "code": "GG", "level": "governorate"},
        ).json()
        # district directly under governorate should fail
        r = client.post(
            "/organization-units/",
            headers=h,
            json={
                "name": "D",
                "code": "DD",
                "level": "district",
                "parent_id": gov["id"],
            },
        )
        assert r.status_code == 400

    def test_tree_endpoint_returns_nested(self, client, db, director_token, org_tree):
        r = client.get(
            "/organization-units/tree",
            headers={"Authorization": f"Bearer {director_token}"},
        )
        assert r.status_code == 200
        roots = r.json()
        assert len(roots) == 2  # two governorates
        for root in roots:
            assert root["level"] == "governorate"
            assert len(root["children"]) == 2

    def test_field_team_cannot_create_unit(self, client, field_token):
        r = client.post(
            "/organization-units/",
            headers={"Authorization": f"Bearer {field_token}"},
            json={"name": "G", "code": "G-X", "level": "governorate"},
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 3) /auth/me/permissions
# ---------------------------------------------------------------------------


class TestMePermissions:
    def test_director_returns_global_scope(self, client, director_token):
        r = client.get(
            "/auth/me/permissions",
            headers={"Authorization": f"Bearer {director_token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["role"] == "project_director"
        # permissions list non-empty and contains contract.approve
        actions = {(p["resource"], p["action"]) for p in body["permissions"]}
        assert ("contract", "approve") in actions

    def test_supervisor_in_district_lists_subtree(self, client, db, org_tree):
        dist = org_tree["dist_ga_m1_d1"]
        _make_user(db, "u_sup_me", UserRole.AREA_SUPERVISOR, dist.id)
        h = _login(client, "u_sup_me")
        r = client.get("/auth/me/permissions", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["org_unit_id"] == dist.id
        assert body["district_id"] == dist.id
        assert body["municipality_id"] is not None
        assert body["governorate_id"] is not None
        assert body["scope_unit_ids"] == [dist.id]


# ---------------------------------------------------------------------------
# 4) Integration: list scoping & instance 403
# ---------------------------------------------------------------------------


class TestComplaintScoping:
    def test_list_scopes_to_user_subtree(self, client, db, org_tree):
        gov = org_tree["gov_ga"]
        _make_user(db, "u_gov_dir", UserRole.PROJECT_DIRECTOR, gov.id)
        h = _login(client, "u_gov_dir")
        # add an in-scope and out-of-scope complaint
        c_in = Complaint(
            tracking_number="CMP-IN-1",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=org_tree["dist_ga_m1_d1"].id,
        )
        c_out = Complaint(
            tracking_number="CMP-OUT-1",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=org_tree["dist_gb_m1_d1"].id,
        )
        db.add_all([c_in, c_out])
        db.commit()

        r = client.get("/complaints/", headers=h)
        assert r.status_code == 200
        codes = {c["tracking_number"] for c in r.json()["items"]}
        assert "CMP-IN-1" in codes
        assert "CMP-OUT-1" not in codes

    def test_get_out_of_scope_complaint_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        _make_user(db, "u_sup_403", UserRole.AREA_SUPERVISOR, own.id)
        h = _login(client, "u_sup_403")
        c = Complaint(
            tracking_number="CMP-403",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=other.id,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        r = client.get(f"/complaints/{c.id}", headers=h)
        assert r.status_code == 403

    def test_get_in_scope_complaint_returns_200(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        _make_user(db, "u_sup_ok", UserRole.AREA_SUPERVISOR, own.id)
        h = _login(client, "u_sup_ok")
        c = Complaint(
            tracking_number="CMP-OK",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=own.id,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        r = client.get(f"/complaints/{c.id}", headers=h)
        assert r.status_code == 200

    def test_update_out_of_scope_complaint_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        _make_user(db, "u_co_403", UserRole.COMPLAINTS_OFFICER, own.id)
        h = _login(client, "u_co_403")
        c = Complaint(
            tracking_number="CMP-U-403",
            full_name="x",
            phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x",
            status=ComplaintStatus.NEW,
            org_unit_id=other.id,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        r = client.put(
            f"/complaints/{c.id}",
            headers=h,
            json={"status": "under_review"},
        )
        assert r.status_code == 403


class TestTaskScoping:
    def test_list_scopes(self, client, db, org_tree):
        gov = org_tree["gov_ga"]
        _make_user(db, "u_gov_dir2", UserRole.PROJECT_DIRECTOR, gov.id)
        h = _login(client, "u_gov_dir2")
        t_in = Task(
            title="In",
            description="d",
            org_unit_id=org_tree["dist_ga_m1_d1"].id,
        )
        t_out = Task(
            title="Out",
            description="d",
            org_unit_id=org_tree["dist_gb_m1_d1"].id,
        )
        db.add_all([t_in, t_out])
        db.commit()
        r = client.get("/tasks/", headers=h)
        assert r.status_code == 200
        titles = {t["title"] for t in r.json()["items"]}
        assert "In" in titles
        assert "Out" not in titles

    def test_field_team_cannot_get_out_of_scope_task(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        ft = _make_user(db, "u_ft_403", UserRole.FIELD_TEAM, own.id)
        h = _login(client, "u_ft_403")
        t = Task(
            title="Other",
            description="d",
            assigned_to_id=ft.id,
            org_unit_id=other.id,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        r = client.get(f"/tasks/{t.id}", headers=h)
        assert r.status_code == 403

    def test_unscoped_task_visible_to_legacy_user(self, client, db, director_token):
        # Lenient default: org_unit_id IS NULL rows visible to everyone
        t = Task(title="Legacy", description="d")
        db.add(t)
        db.commit()
        r = client.get(
            "/tasks/", headers={"Authorization": f"Bearer {director_token}"}
        )
        assert r.status_code == 200
        assert any(item["title"] == "Legacy" for item in r.json()["items"])

    def test_create_stamps_org_unit(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        _make_user(db, "u_dir_stamp", UserRole.PROJECT_DIRECTOR, own.id)
        h = _login(client, "u_dir_stamp")
        r = client.post(
            "/tasks/",
            headers=h,
            json={
                "title": "Stamped",
                "description": "x",
                "source_type": "internal",
            },
        )
        assert r.status_code == 200, r.text
        # Confirm via DB
        task = db.query(Task).filter(Task.title == "Stamped").first()
        assert task is not None
        assert task.org_unit_id == own.id


class TestContractScoping:
    def test_contract_list_scoped(self, client, db, org_tree):
        gov_a = org_tree["gov_ga"]
        director = _make_user(db, "u_cdir", UserRole.PROJECT_DIRECTOR, gov_a.id)
        h = _login(client, "u_cdir")
        c_in = Contract(
            contract_number="CT-IN",
            title="t",
            contractor_name="c",
            contract_type=ContractType.CONSTRUCTION,
            contract_value=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            scope_description="x",
            created_by_id=director.id,
            org_unit_id=org_tree["dist_ga_m1_d1"].id,
        )
        c_out = Contract(
            contract_number="CT-OUT",
            title="t",
            contractor_name="c",
            contract_type=ContractType.CONSTRUCTION,
            contract_value=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            scope_description="x",
            created_by_id=director.id,
            org_unit_id=org_tree["dist_gb_m1_d1"].id,
        )
        db.add_all([c_in, c_out])
        db.commit()
        r = client.get("/contracts/", headers=h)
        assert r.status_code == 200
        codes = {c["contract_number"] for c in r.json()["items"]}
        assert "CT-IN" in codes
        assert "CT-OUT" not in codes


# ---------------------------------------------------------------------------
# 5) Org-scope on additional endpoints (production-readiness pass)
# ---------------------------------------------------------------------------


class TestComplaintMapMarkersScoping:
    def test_map_markers_filtered_to_subtree(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        _make_user(db, "u_sup_map", UserRole.AREA_SUPERVISOR, own.id)
        h = _login(client, "u_sup_map")
        c_in = Complaint(
            tracking_number="CMP-MAP-IN",
            full_name="x", phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x", status=ComplaintStatus.NEW,
            latitude=33.5, longitude=36.3,
            org_unit_id=own.id,
        )
        c_out = Complaint(
            tracking_number="CMP-MAP-OUT",
            full_name="x", phone="0",
            complaint_type=ComplaintType.OTHER,
            description="x", status=ComplaintStatus.NEW,
            latitude=33.5, longitude=36.3,
            org_unit_id=other.id,
        )
        db.add_all([c_in, c_out])
        db.commit()
        r = client.get("/complaints/map/markers", headers=h)
        assert r.status_code == 200
        codes = {c["tracking_number"] for c in r.json()}
        assert "CMP-MAP-IN" in codes
        assert "CMP-MAP-OUT" not in codes


def _make_active_contract(db, director, *, number, org_unit_id):
    c = Contract(
        contract_number=number,
        title="t", contractor_name="c",
        contract_type=ContractType.CONSTRUCTION,
        contract_value=1,
        start_date=date(2025, 1, 1),
        end_date=date(2099, 12, 31),
        scope_description="x",
        created_by_id=director.id,
        status=ContractStatus.ACTIVE,
        org_unit_id=org_unit_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestContractsExpiringSoonScoping:
    def test_expiring_soon_filtered_to_subtree(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director = _make_user(db, "u_dir_exp", UserRole.PROJECT_DIRECTOR, None)
        sup = _make_user(db, "u_sup_exp", UserRole.AREA_SUPERVISOR, own.id)
        from datetime import timedelta
        soon = date.today() + timedelta(days=10)
        c_in = Contract(
            contract_number="CT-EXP-IN", title="t", contractor_name="c",
            contract_type=ContractType.CONSTRUCTION, contract_value=1,
            start_date=date.today(), end_date=soon,
            scope_description="x", created_by_id=director.id,
            status=ContractStatus.ACTIVE, org_unit_id=own.id,
        )
        c_out = Contract(
            contract_number="CT-EXP-OUT", title="t", contractor_name="c",
            contract_type=ContractType.CONSTRUCTION, contract_value=1,
            start_date=date.today(), end_date=soon,
            scope_description="x", created_by_id=director.id,
            status=ContractStatus.ACTIVE, org_unit_id=other.id,
        )
        db.add_all([c_in, c_out])
        db.commit()
        h = _login(client, "u_sup_exp")
        r = client.get("/contracts/expiring-soon", headers=h)
        assert r.status_code == 200
        codes = {c["contract_number"] for c in r.json()}
        assert "CT-EXP-IN" in codes
        assert "CT-EXP-OUT" not in codes


class TestContractInstanceAuthz:
    def test_update_out_of_scope_contract_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director = _make_user(db, "u_dir_cu", UserRole.PROJECT_DIRECTOR, None)
        cm = _make_user(db, "u_cm_cu", UserRole.CONTRACTS_MANAGER, own.id)
        c = _make_active_contract(db, director, number="CT-CU-OUT", org_unit_id=other.id)
        h = _login(client, "u_cm_cu")
        r = client.put(f"/contracts/{c.id}", json={"title": "nope"}, headers=h)
        assert r.status_code == 403

    def test_approve_out_of_scope_contract_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director = _make_user(db, "u_dir_ca", UserRole.PROJECT_DIRECTOR, None)
        cm = _make_user(db, "u_cm_ca", UserRole.CONTRACTS_MANAGER, own.id)
        c = _make_active_contract(db, director, number="CT-CA-OUT", org_unit_id=other.id)
        c.status = ContractStatus.DRAFT
        db.commit()
        h = _login(client, "u_cm_ca")
        r = client.post(
            f"/contracts/{c.id}/approve",
            json={"action": "approve", "comments": "x"},
            headers=h,
        )
        assert r.status_code == 403

    def test_generate_pdf_out_of_scope_contract_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director = _make_user(db, "u_dir_pdf", UserRole.PROJECT_DIRECTOR, None)
        ft = _make_user(db, "u_ft_pdf", UserRole.FIELD_TEAM, own.id)
        c = _make_active_contract(db, director, number="CT-PDF-OUT", org_unit_id=other.id)
        h = _login(client, "u_ft_pdf")
        r = client.post(f"/contracts/{c.id}/generate-pdf", headers=h)
        assert r.status_code == 403


class TestProjectInstanceAuthz:
    def _make_project(self, db, director, *, code, org_unit_id):
        from app.models.project import Project, ProjectStatus
        p = Project(
            title="P", code=code, description="d",
            status=ProjectStatus.PLANNED,
            created_by_id=director.id,
            org_unit_id=org_unit_id,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p

    def test_get_out_of_scope_project_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director = _make_user(db, "u_dir_pg", UserRole.PROJECT_DIRECTOR, None)
        sup = _make_user(db, "u_sup_pg", UserRole.AREA_SUPERVISOR, own.id)
        p = self._make_project(db, director, code="P-G-OUT", org_unit_id=other.id)
        h = _login(client, "u_sup_pg")
        r = client.get(f"/projects/{p.id}", headers=h)
        assert r.status_code == 403

    def test_update_out_of_scope_project_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director = _make_user(db, "u_dir_pu", UserRole.PROJECT_DIRECTOR, None)
        cm = _make_user(db, "u_cm_pu", UserRole.CONTRACTS_MANAGER, own.id)
        p = self._make_project(db, director, code="P-U-OUT", org_unit_id=other.id)
        h = _login(client, "u_cm_pu")
        r = client.put(f"/projects/{p.id}", json={"title": "nope"}, headers=h)
        assert r.status_code == 403


class TestRestrictedRoleAccess:
    def _make_project(self, db, director, *, code, org_unit_id):
        from app.models.project import Project, ProjectStatus
        p = Project(
            title="P", code=code, description="d",
            status=ProjectStatus.PLANNED,
            created_by_id=director.id,
            org_unit_id=org_unit_id,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p

    def test_field_team_cannot_manage_locations(self, client, db):
        _make_user(db, "u_ft_loc", UserRole.FIELD_TEAM, None)
        h = _login(client, "u_ft_loc")
        r = client.post(
            "/locations/",
            json={"name": "منع-1", "code": "NOLOC-1", "location_type": "other", "status": "active"},
            headers=h,
        )
        assert r.status_code == 403

    def test_contractor_cannot_manage_locations(self, client, db):
        _make_user(db, "u_con_loc", UserRole.CONTRACTOR_USER, None)
        h = _login(client, "u_con_loc")
        r = client.post(
            "/locations/",
            json={"name": "منع-2", "code": "NOLOC-2", "location_type": "other", "status": "active"},
            headers=h,
        )
        assert r.status_code == 403

    def test_field_team_contracts_list_is_empty_when_unowned(self, client, db):
        _make_user(db, "u_ft_con", UserRole.FIELD_TEAM, None)
        h = _login(client, "u_ft_con")
        r = client.get("/contracts/", headers=h)
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_contractor_contracts_list_is_empty_when_unowned(self, client, db):
        _make_user(db, "u_con_con", UserRole.CONTRACTOR_USER, None)
        h = _login(client, "u_con_con")
        r = client.get("/contracts/", headers=h)
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_delete_out_of_scope_project_returns_403(self, client, db, org_tree):
        own = org_tree["dist_ga_m1_d1"]
        other = org_tree["dist_gb_m1_d1"]
        director_global = _make_user(db, "u_dir_pdg", UserRole.PROJECT_DIRECTOR, None)
        director_scoped = _make_user(db, "u_dir_pds", UserRole.PROJECT_DIRECTOR, own.id)
        p = self._make_project(db, director_global, code="P-D-OUT", org_unit_id=other.id)
        h = _login(client, "u_dir_pds")
        r = client.delete(f"/projects/{p.id}", headers=h)
        assert r.status_code == 403


class TestSettingsAuth:
    def test_settings_get_anonymous_blocked(self, client, db):
        r = client.get("/settings/")
        assert r.status_code in (401, 403)

    def test_settings_get_internal_user_ok(self, client, db, org_tree):
        _make_user(db, "u_ft_set", UserRole.FIELD_TEAM, org_tree["dist_ga_m1_d1"].id)
        h = _login(client, "u_ft_set")
        r = client.get("/settings/", headers=h)
        assert r.status_code == 200

    def test_settings_get_citizen_blocked(self, client, db):
        _make_user(db, "u_cit_set", UserRole.CITIZEN, None)
        h = _login(client, "u_cit_set")
        r = client.get("/settings/", headers=h)
        assert r.status_code == 403
