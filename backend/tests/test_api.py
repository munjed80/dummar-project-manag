"""
Critical-flow API tests covering:
- Anonymous access denial on protected endpoints
- Anonymous complaint creation
- RBAC enforcement (unauthorized role cannot update complaints/tasks/contracts)
- Privileged director can create users
- File-related fields return arrays consistently
- Report endpoints return expected shapes
- Pagination metadata on list endpoints
"""

import pytest
from tests.conftest import _auth_headers, _login, _create_user
from app.models.user import UserRole


# ---------------------------------------------------------------------------
# 1. Anonymous user cannot access /users/
# ---------------------------------------------------------------------------

class TestAnonymousAccess:
    def test_anon_cannot_list_users(self, client):
        resp = client.get("/users/")
        assert resp.status_code in (401, 403)

    def test_anon_cannot_list_complaints(self, client):
        resp = client.get("/complaints/")
        assert resp.status_code in (401, 403)

    def test_anon_cannot_list_tasks(self, client):
        resp = client.get("/tasks/")
        assert resp.status_code in (401, 403)

    def test_anon_cannot_list_contracts(self, client):
        resp = client.get("/contracts/")
        assert resp.status_code in (401, 403)

    def test_anon_cannot_access_reports(self, client):
        resp = client.get("/reports/summary")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 2. Anonymous user can create a complaint (public endpoint)
# ---------------------------------------------------------------------------

class TestPublicComplaintCreation:
    def test_anon_can_create_complaint(self, client, sample_area):
        payload = {
            "full_name": "أحمد محمد",
            "phone": "0991234567",
            "complaint_type": "water",
            "description": "تسرب مياه في الطابق الثالث",
            "area_id": sample_area.id,
        }
        resp = client.post("/complaints/", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["tracking_number"].startswith("CMP")
        assert data["full_name"] == "أحمد محمد"
        assert data["status"] == "new"

    def test_anon_complaint_with_images(self, client, sample_area):
        payload = {
            "full_name": "سارة",
            "phone": "0991111111",
            "complaint_type": "electricity",
            "description": "انقطاع كهرباء",
            "images": ["/uploads/complaints/img1.jpg", "/uploads/complaints/img2.jpg"],
        }
        resp = client.post("/complaints/", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # images must come back as an array
        assert isinstance(data["images"], list)
        assert len(data["images"]) == 2


# ---------------------------------------------------------------------------
# 3. Unauthorized roles cannot update protected records
# ---------------------------------------------------------------------------

class TestRBACEnforcement:
    def test_field_team_cannot_update_complaint(self, client, db, field_token, sample_area):
        # Create a complaint first
        payload = {
            "full_name": "Test",
            "phone": "0990000000",
            "complaint_type": "roads",
            "description": "Test",
        }
        create_resp = client.post("/complaints/", json=payload)
        complaint_id = create_resp.json()["id"]

        # Field team tries to update → 403
        resp = client.put(
            f"/complaints/{complaint_id}",
            json={"status": "under_review"},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_field_team_cannot_create_task(self, client, field_token):
        resp = client.post(
            "/tasks/",
            json={
                "title": "Test task",
                "description": "Should fail",
                "source_type": "internal",
                "priority": "medium",
            },
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_contractor_cannot_update_contract(self, client, db, contractor_token, director_token):
        # Director creates a contract
        contract_payload = {
            "contract_number": "CTR-001",
            "title": "عقد صيانة",
            "contractor_name": "شركة الإعمار",
            "contract_type": "maintenance",
            "contract_value": 50000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_description": "صيانة شاملة",
        }
        create_resp = client.post(
            "/contracts/",
            json=contract_payload,
            headers=_auth_headers(director_token),
        )
        assert create_resp.status_code == 200, create_resp.text
        contract_id = create_resp.json()["id"]

        # Contractor tries to update → 403
        resp = client.put(
            f"/contracts/{contract_id}",
            json={"title": "Hacked title"},
            headers=_auth_headers(contractor_token),
        )
        assert resp.status_code == 403

    def test_contractor_cannot_create_user(self, client, contractor_token):
        resp = client.post(
            "/users/",
            json={
                "username": "hacker",
                "full_name": "Hacker",
                "password": "hack123",
                "role": "project_director",
            },
            headers=_auth_headers(contractor_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. Director can create users
# ---------------------------------------------------------------------------

class TestDirectorPrivileges:
    def test_director_can_create_user(self, client, director_token):
        resp = client.post(
            "/users/",
            json={
                "username": "new_officer",
                "full_name": "مسؤول جديد",
                "password": "securePass1!",
                "role": "complaints_officer",
            },
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == "new_officer"
        assert data["role"] == "complaints_officer"

    def test_director_can_list_users(self, client, director_token):
        resp = client.get("/users/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data
        assert isinstance(data["items"], list)


# ---------------------------------------------------------------------------
# 5. File-related fields return arrays consistently
# ---------------------------------------------------------------------------

class TestFileFieldConsistency:
    def test_complaint_images_is_array(self, client, director_token, sample_area):
        # Create complaint with images
        payload = {
            "full_name": "Test Files",
            "phone": "0990000001",
            "complaint_type": "infrastructure",
            "description": "Test",
            "images": ["/uploads/complaints/a.jpg"],
        }
        resp = client.post("/complaints/", json=payload)
        assert resp.status_code == 200
        complaint_id = resp.json()["id"]

        # Fetch single complaint — images must be array
        get_resp = client.get(
            f"/complaints/{complaint_id}",
            headers=_auth_headers(director_token),
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert isinstance(data["images"], list)

    def test_complaint_null_images_is_none_or_array(self, client, director_token):
        payload = {
            "full_name": "No Images",
            "phone": "0990000002",
            "complaint_type": "cleaning",
            "description": "No photos",
        }
        resp = client.post("/complaints/", json=payload)
        complaint_id = resp.json()["id"]

        get_resp = client.get(
            f"/complaints/{complaint_id}",
            headers=_auth_headers(director_token),
        )
        data = get_resp.json()
        # images should be null or empty array, never a raw string
        assert data["images"] is None or isinstance(data["images"], list)


# ---------------------------------------------------------------------------
# 6. Report endpoints return expected shapes
# ---------------------------------------------------------------------------

class TestReportEndpoints:
    def test_summary_shape(self, client, director_token):
        resp = client.get("/reports/summary", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "complaints" in data
        assert "tasks" in data
        assert "contracts" in data
        assert "total" in data["complaints"]
        assert "by_status" in data["complaints"]
        assert isinstance(data["complaints"]["by_status"], list)

    def test_complaints_report_paginated(self, client, director_token):
        resp = client.get(
            "/reports/complaints?skip=0&limit=10",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_tasks_report_paginated(self, client, director_token):
        resp = client.get(
            "/reports/tasks?skip=0&limit=10",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data

    def test_contracts_report_paginated(self, client, director_token):
        resp = client.get(
            "/reports/contracts?skip=0&limit=10",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data

    def test_complaints_csv_export(self, client, director_token):
        resp = client.get(
            "/reports/complaints/csv",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_tasks_csv_export(self, client, director_token):
        resp = client.get(
            "/reports/tasks/csv",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_contracts_csv_export(self, client, director_token):
        resp = client.get(
            "/reports/contracts/csv",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 7. List endpoints return pagination metadata
# ---------------------------------------------------------------------------

class TestPaginationMetadata:
    def test_complaints_list_returns_total_count(self, client, director_token):
        resp = client.get("/complaints/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data

    def test_tasks_list_returns_total_count(self, client, director_token):
        resp = client.get("/tasks/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data

    def test_contracts_list_returns_total_count(self, client, director_token):
        resp = client.get("/contracts/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data

    def test_complaints_list_search(self, client, db, director_token, sample_area):
        # Create a complaint via the DB directly to avoid rate limits
        from app.models.complaint import Complaint, ComplaintType, ComplaintStatus
        complaint = Complaint(
            tracking_number="CMP00001234",
            full_name="بحث مميز",
            phone="0991111111",
            complaint_type=ComplaintType.WATER,
            description="اختبار البحث",
            status=ComplaintStatus.NEW,
            area_id=sample_area.id,
        )
        db.add(complaint)
        db.commit()

        resp = client.get(
            "/complaints/?search=بحث",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 1


# ---------------------------------------------------------------------------
# 8. Citizen role is denied access to internal/operational endpoints
# ---------------------------------------------------------------------------

class TestCitizenDenial:
    """Citizen users must NOT access internal operational endpoints."""

    def test_citizen_cannot_list_complaints(self, client, citizen_token):
        resp = client.get("/complaints/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_get_complaint_detail(self, client, citizen_token):
        resp = client.get("/complaints/1", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_list_tasks(self, client, citizen_token):
        resp = client.get("/tasks/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_get_task_detail(self, client, citizen_token):
        resp = client.get("/tasks/1", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_list_contracts(self, client, citizen_token):
        resp = client.get("/contracts/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_get_contract_detail(self, client, citizen_token):
        resp = client.get("/contracts/1", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_access_reports(self, client, citizen_token):
        resp = client.get("/reports/summary", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_list_users(self, client, citizen_token):
        resp = client.get("/users/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_access_dashboard_stats(self, client, citizen_token):
        resp = client.get("/dashboard/stats", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_access_dashboard_activity(self, client, citizen_token):
        resp = client.get("/dashboard/recent-activity", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_get_map_markers(self, client, citizen_token):
        resp = client.get("/complaints/map/markers", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 9. Citizen CAN access their own complaints
# ---------------------------------------------------------------------------

class TestCitizenAccess:
    """Citizen users can access their own complaint endpoint."""

    def test_citizen_can_access_my_complaints(self, client, db, citizen_token):
        resp = client.get("/complaints/citizen/my-complaints", headers=_auth_headers(citizen_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data
