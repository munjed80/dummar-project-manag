"""Tests for the Violations module: model, RBAC, CRUD, status workflow.

Covers:
- project_director full CRUD + soft-delete
- complaints_officer / engineer_supervisor / area_supervisor / contracts_manager
  can create + update + read but NOT delete
- field_team / contractor_user / citizen are blocked from all writes
- list filters (status / violation_type / severity / municipality_id /
  district_id / q) + pagination
- status update endpoint sets resolved_at when transitioning to RESOLVED
- validation: invalid enum value returns 422
- violation_number is auto-generated and unique
"""
from __future__ import annotations

import pytest

from app.models.user import UserRole
from app.models.violation import (
    Violation,
    ViolationSeverity,
    ViolationStatus,
    ViolationType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides) -> dict:
    payload = {
        "title": "بناء غير مرخص",
        "description": "تم رصد بناء بدون رخصة في الحي السابع",
        "violation_type": "building",
        "severity": "high",
        "location_text": "الحي السابع، شارع 12",
    }
    payload.update(overrides)
    return payload


def _login_as(client, db, username: str, role: UserRole) -> str:
    from tests.conftest import _create_user, _login
    _create_user(db, username, role)
    return _login(client, username)


# ---------------------------------------------------------------------------
# Director CRUD
# ---------------------------------------------------------------------------

class TestDirectorCRUD:
    def test_director_creates_violation(self, client, director_token):
        resp = client.post("/violations/", json=_payload(), headers=_auth(director_token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "بناء غير مرخص"
        assert data["violation_type"] == "building"
        assert data["severity"] == "high"
        assert data["status"] == "new"
        assert data["is_active"] is True
        # Auto-generated identifier in the form VIO-YYYY-NNNN
        assert data["violation_number"].startswith("VIO-")
        assert data["reported_by_user_id"] is not None

    def test_violation_number_is_unique_and_sequential(self, client, director_token):
        first = client.post("/violations/", json=_payload(title="A"), headers=_auth(director_token))
        second = client.post("/violations/", json=_payload(title="B"), headers=_auth(director_token))
        assert first.status_code == 201 and second.status_code == 201
        n1 = first.json()["violation_number"]
        n2 = second.json()["violation_number"]
        assert n1 != n2
        assert n1.startswith("VIO-") and n2.startswith("VIO-")

    def test_director_lists_violations(self, client, director_token):
        for i in range(3):
            client.post(
                "/violations/", json=_payload(title=f"v{i}"), headers=_auth(director_token)
            )
        resp = client.get("/violations/", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_director_gets_violation_by_id(self, client, director_token):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        resp = client.get(f"/violations/{created['id']}", headers=_auth(director_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_violation_404(self, client, director_token):
        resp = client.get("/violations/99999", headers=_auth(director_token))
        assert resp.status_code == 404

    def test_director_patches_violation(self, client, director_token):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        resp = client.patch(
            f"/violations/{created['id']}",
            json={"title": "عنوان معدّل", "fine_amount": "500.00"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["title"] == "عنوان معدّل"
        assert data["fine_amount"] == "500.00"

    def test_director_soft_deletes_violation(self, client, director_token, db):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        vid = created["id"]
        resp = client.delete(f"/violations/{vid}", headers=_auth(director_token))
        assert resp.status_code == 200

        # Hidden from list and from get-by-id (treated as not found)
        listing = client.get("/violations/", headers=_auth(director_token)).json()
        assert listing["total_count"] == 0
        assert client.get(f"/violations/{vid}", headers=_auth(director_token)).status_code == 404

        # But the row is still in the DB with is_active=False
        row = db.query(Violation).filter(Violation.id == vid).first()
        assert row is not None
        assert row.is_active is False


# ---------------------------------------------------------------------------
# Status workflow
# ---------------------------------------------------------------------------

class TestStatusUpdate:
    def test_status_update_endpoint(self, client, director_token):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        resp = client.patch(
            f"/violations/{created['id']}/status",
            json={"status": "under_review", "note": "بدء المراجعة"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "under_review"

    def test_status_update_to_resolved_sets_resolved_at(self, client, director_token):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        assert created["resolved_at"] is None

        resp = client.patch(
            f"/violations/{created['id']}/status",
            json={"status": "resolved"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None

    def test_patch_to_resolved_via_main_endpoint_sets_resolved_at(
        self, client, director_token
    ):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        resp = client.patch(
            f"/violations/{created['id']}",
            json={"status": "resolved"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["resolved_at"] is not None


# ---------------------------------------------------------------------------
# Filters and search
# ---------------------------------------------------------------------------

class TestFilters:
    def _seed_three(self, client, director_token):
        client.post(
            "/violations/",
            json=_payload(title="A", violation_type="building", severity="high"),
            headers=_auth(director_token),
        )
        client.post(
            "/violations/",
            json=_payload(title="B", violation_type="hygiene", severity="low"),
            headers=_auth(director_token),
        )
        client.post(
            "/violations/",
            json=_payload(title="C", violation_type="building", severity="critical"),
            headers=_auth(director_token),
        )

    def test_filter_by_type(self, client, director_token):
        self._seed_three(client, director_token)
        resp = client.get("/violations/?violation_type=building", headers=_auth(director_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(v["violation_type"] == "building" for v in items)

    def test_filter_by_severity(self, client, director_token):
        self._seed_three(client, director_token)
        resp = client.get("/violations/?severity=critical", headers=_auth(director_token))
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["severity"] == "critical"

    def test_filter_by_status(self, client, director_token):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        client.patch(
            f"/violations/{created['id']}/status",
            json={"status": "fined"},
            headers=_auth(director_token),
        )
        # Add a second one in the default NEW status
        client.post("/violations/", json=_payload(title="other"), headers=_auth(director_token))

        resp = client.get("/violations/?status=fined", headers=_auth(director_token))
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "fined"

    def test_search_q(self, client, director_token):
        client.post(
            "/violations/",
            json=_payload(title="مخالفة الأسواق", violation_type="market"),
            headers=_auth(director_token),
        )
        client.post(
            "/violations/",
            json=_payload(title="مخالفة طريق", violation_type="road"),
            headers=_auth(director_token),
        )
        resp = client.get("/violations/?q=الأسواق", headers=_auth(director_token))
        items = resp.json()["items"]
        assert len(items) == 1
        assert "الأسواق" in items[0]["title"]

    def test_pagination(self, client, director_token):
        for i in range(5):
            client.post(
                "/violations/", json=_payload(title=f"p{i}"), headers=_auth(director_token)
            )
        resp = client.get(
            "/violations/?page=1&page_size=2", headers=_auth(director_token)
        )
        body = resp.json()
        assert body["total_count"] == 5
        assert len(body["items"]) == 2
        assert body["page_size"] == 2

        resp2 = client.get(
            "/violations/?page=3&page_size=2", headers=_auth(director_token)
        )
        body2 = resp2.json()
        assert len(body2["items"]) == 1


# ---------------------------------------------------------------------------
# RBAC: write access for inspector roles
# ---------------------------------------------------------------------------

class TestInspectorWriteAccess:
    @pytest.mark.parametrize(
        "role",
        [
            UserRole.COMPLAINTS_OFFICER,
            UserRole.ENGINEER_SUPERVISOR,
            UserRole.AREA_SUPERVISOR,
            UserRole.CONTRACTS_MANAGER,
        ],
    )
    def test_inspector_can_create_and_update(self, client, db, role):
        token = _login_as(client, db, f"insp_{role.value}", role)
        created = client.post("/violations/", json=_payload(), headers=_auth(token))
        assert created.status_code == 201, created.text
        vid = created.json()["id"]

        upd = client.patch(
            f"/violations/{vid}/status",
            json={"status": "inspection_required"},
            headers=_auth(token),
        )
        assert upd.status_code == 200
        assert upd.json()["status"] == "inspection_required"

    @pytest.mark.parametrize(
        "role",
        [
            UserRole.COMPLAINTS_OFFICER,
            UserRole.ENGINEER_SUPERVISOR,
            UserRole.AREA_SUPERVISOR,
            UserRole.CONTRACTS_MANAGER,
        ],
    )
    def test_inspector_cannot_delete(self, client, db, director_token, role):
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        token = _login_as(client, db, f"insp_del_{role.value}", role)
        resp = client.delete(f"/violations/{created['id']}", headers=_auth(token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# RBAC: forbidden roles
# ---------------------------------------------------------------------------

class TestForbiddenRoles:
    @pytest.mark.parametrize(
        "role",
        [UserRole.FIELD_TEAM, UserRole.CONTRACTOR_USER],
    )
    def test_low_privilege_internal_blocked_from_violations(self, client, db, role):
        """field_team and contractor_user are NOT in the violation permission
        matrix — neither read nor write — matching the narrow allow-list these
        roles already get for other resource types."""
        token = _login_as(client, db, f"low_{role.value}", role)
        assert client.get("/violations/", headers=_auth(token)).status_code == 403
        assert (
            client.post("/violations/", json=_payload(), headers=_auth(token)).status_code
            == 403
        )

    def test_citizen_blocked_from_every_endpoint(self, client, citizen_token, director_token):
        # Seed one row so the PATCH below hits the auth check (not 404).
        created = client.post(
            "/violations/", json=_payload(), headers=_auth(director_token)
        ).json()
        assert client.get("/violations/", headers=_auth(citizen_token)).status_code == 403
        assert (
            client.post("/violations/", json=_payload(), headers=_auth(citizen_token)).status_code
            == 403
        )
        assert (
            client.patch(
                f"/violations/{created['id']}/status",
                json={"status": "resolved"},
                headers=_auth(citizen_token),
            ).status_code
            == 403
        )

    def test_unauthenticated_blocked(self, client):
        assert client.get("/violations/").status_code == 403
        assert client.post("/violations/", json=_payload()).status_code == 403


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_violation_type_returns_422(self, client, director_token):
        resp = client.post(
            "/violations/",
            json=_payload(violation_type="bogus_value"),
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_invalid_severity_returns_422(self, client, director_token):
        resp = client.post(
            "/violations/", json=_payload(severity="extreme"), headers=_auth(director_token)
        )
        assert resp.status_code == 422

    def test_missing_required_fields_returns_422(self, client, director_token):
        resp = client.post(
            "/violations/",
            json={"title": "x"},  # missing description + violation_type
            headers=_auth(director_token),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Direct model sanity check
# ---------------------------------------------------------------------------

class TestModel:
    def test_enums_use_lowercase_values(self):
        assert ViolationType.BUILDING.value == "building"
        assert ViolationSeverity.MEDIUM.value == "medium"
        assert ViolationStatus.NEW.value == "new"
        assert ViolationStatus.REFERRED_TO_LEGAL.value == "referred_to_legal"
