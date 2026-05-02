"""Backend enforcement of CORRUPTION (شكوى فساد) complaint visibility.

CORRUPTION is the sensitive complaint type submitted by citizens via
the public form. Only PROJECT_DIRECTOR (admin) may see them; all other
internal staff get filtered lists and 404 on direct access.
"""
import pytest

from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.models.user import UserRole
from tests.conftest import _create_user, _login, _auth_headers


@pytest.fixture()
def complaints_officer(db):
    return _create_user(db, "test_officer", UserRole.COMPLAINTS_OFFICER)


@pytest.fixture()
def complaints_officer_token(client, complaints_officer):
    return _login(client, "test_officer")


@pytest.fixture()
def engineer(db):
    return _create_user(db, "test_engineer", UserRole.ENGINEER_SUPERVISOR)


@pytest.fixture()
def engineer_token(client, engineer):
    return _login(client, "test_engineer")


def _seed_complaint(db, *, ctype: ComplaintType, tracking="CMP-CTEST-1", phone="0999111222"):
    c = Complaint(
        tracking_number=tracking,
        full_name="مواطن اختبار",
        phone=phone,
        complaint_type=ctype,
        description="بلاغ اختبار",
        status=ComplaintStatus.NEW,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestSensitiveComplaintList:
    def test_director_sees_corruption_in_list(self, client, db, director_token):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-CRP-1")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-WAT-1")
        resp = client.get("/complaints/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        types = {item["complaint_type"] for item in resp.json()["items"]}
        assert "corruption" in types
        assert "water" in types

    def test_complaints_officer_does_not_see_corruption(
        self, client, db, complaints_officer_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-CRP-2")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-WAT-2")
        resp = client.get("/complaints/", headers=_auth_headers(complaints_officer_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        types = {item["complaint_type"] for item in items}
        assert "corruption" not in types
        assert "water" in types
        assert resp.json()["total_count"] == 1

    def test_engineer_does_not_see_corruption(self, client, db, engineer_token):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-CRP-3")
        resp = client.get("/complaints/", headers=_auth_headers(engineer_token))
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 0

    def test_search_does_not_leak_corruption(self, client, db, complaints_officer_token):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-CRP-FIND")
        resp = client.get(
            "/complaints/?search=CRP-FIND",
            headers=_auth_headers(complaints_officer_token),
        )
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 0

    def test_director_search_finds_corruption(self, client, db, director_token):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-CRP-FIND2")
        resp = client.get(
            "/complaints/?search=CRP-FIND2",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1


class TestSensitiveComplaintDetail:
    def test_director_can_get_corruption(self, client, db, director_token):
        c = _seed_complaint(db, ctype=ComplaintType.CORRUPTION)
        resp = client.get(f"/complaints/{c.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["complaint_type"] == "corruption"

    def test_officer_get_corruption_returns_404(
        self, client, db, complaints_officer_token
    ):
        c = _seed_complaint(db, ctype=ComplaintType.CORRUPTION)
        resp = client.get(f"/complaints/{c.id}", headers=_auth_headers(complaints_officer_token))
        assert resp.status_code == 404

    def test_officer_update_corruption_returns_404(
        self, client, db, complaints_officer_token
    ):
        c = _seed_complaint(db, ctype=ComplaintType.CORRUPTION)
        resp = client.put(
            f"/complaints/{c.id}",
            json={"status": "under_review"},
            headers=_auth_headers(complaints_officer_token),
        )
        assert resp.status_code == 404

    def test_officer_activities_corruption_returns_404(
        self, client, db, complaints_officer_token
    ):
        c = _seed_complaint(db, ctype=ComplaintType.CORRUPTION)
        resp = client.get(
            f"/complaints/{c.id}/activities",
            headers=_auth_headers(complaints_officer_token),
        )
        assert resp.status_code == 404

    def test_officer_create_task_from_corruption_returns_404(
        self, client, db, complaints_officer_token, complaints_officer
    ):
        c = _seed_complaint(db, ctype=ComplaintType.CORRUPTION)
        resp = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "X", "assigned_to_id": complaints_officer.id},
            headers=_auth_headers(complaints_officer_token),
        )
        assert resp.status_code == 404


class TestSensitiveComplaintTracking:
    """Citizen public tracking by tracking_number+phone still works for the
    submitter — they have the right to see their own complaint."""

    def test_citizen_can_track_own_corruption_complaint(self, client, db):
        c = _seed_complaint(
            db, ctype=ComplaintType.CORRUPTION, tracking="CMP-OWN-1", phone="0999000111"
        )
        resp = client.post(
            "/complaints/track",
            json={"tracking_number": c.tracking_number, "phone": c.phone},
        )
        assert resp.status_code == 200
        assert resp.json()["complaint_type"] == "corruption"


class TestSensitiveComplaintDashboard:
    def test_dashboard_stats_exclude_corruption_for_officer(
        self, client, db, complaints_officer_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-D-1")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-D-2")
        resp = client.get(
            "/dashboard/stats", headers=_auth_headers(complaints_officer_token)
        )
        assert resp.status_code == 200
        assert resp.json()["total_complaints"] == 1

    def test_dashboard_stats_include_corruption_for_director(
        self, client, db, director_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-D-3")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-D-4")
        resp = client.get(
            "/dashboard/stats", headers=_auth_headers(director_token)
        )
        assert resp.status_code == 200
        assert resp.json()["total_complaints"] == 2

    def test_recent_activity_excludes_corruption_for_officer(
        self, client, db, complaints_officer_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-RA-1")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-RA-2")
        resp = client.get(
            "/dashboard/recent-activity",
            headers=_auth_headers(complaints_officer_token),
        )
        assert resp.status_code == 200
        types = {c["type"] for c in resp.json()["recent_complaints"]}
        assert "corruption" not in types
        assert "water" in types


class TestSensitiveComplaintReports:
    def test_reports_summary_excludes_corruption_for_officer(
        self, client, db, complaints_officer_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-R-1")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-R-2")
        resp = client.get(
            "/reports/summary", headers=_auth_headers(complaints_officer_token)
        )
        assert resp.status_code == 200
        assert resp.json()["complaints"]["total"] == 1

    def test_reports_complaints_excludes_corruption_for_officer(
        self, client, db, complaints_officer_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-R-3")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-R-4")
        resp = client.get(
            "/reports/complaints", headers=_auth_headers(complaints_officer_token)
        )
        assert resp.status_code == 200
        types = {item["complaint_type"] for item in resp.json()["items"]}
        assert "corruption" not in types

    def test_reports_csv_excludes_corruption_for_officer(
        self, client, db, complaints_officer_token
    ):
        _seed_complaint(db, ctype=ComplaintType.CORRUPTION, tracking="CMP-CSV-1")
        _seed_complaint(db, ctype=ComplaintType.WATER, tracking="CMP-CSV-2")
        resp = client.get(
            "/reports/complaints/csv",
            headers=_auth_headers(complaints_officer_token),
        )
        assert resp.status_code == 200
        body = resp.text
        assert "CMP-CSV-1" not in body
        assert "CMP-CSV-2" in body
