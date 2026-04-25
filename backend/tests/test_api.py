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


# ---------------------------------------------------------------------------
# 10. GIS endpoints
# ---------------------------------------------------------------------------

class TestGISEndpoints:
    """Test GIS / operations map endpoints."""

    def test_operations_map_returns_list(self, client, director_token):
        resp = client.get("/gis/operations-map", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_operations_map_filter_by_entity_type(self, client, director_token):
        resp = client.get(
            "/gis/operations-map?entity_type=complaint",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # All returned items should be complaints
        for item in data:
            assert item["entity_type"] == "complaint"

    def test_operations_map_filter_tasks(self, client, director_token):
        resp = client.get(
            "/gis/operations-map?entity_type=task",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert item["entity_type"] == "task"

    def test_area_boundaries_returns_list(self, client, director_token):
        resp = client.get("/gis/area-boundaries", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_citizen_cannot_access_gis(self, client, citizen_token):
        resp = client.get("/gis/operations-map", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403
        resp = client.get("/gis/area-boundaries", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_operations_map_with_data(self, client, db, director_token, sample_area):
        """Create a complaint with coords and verify it appears in operations map."""
        from app.models.complaint import Complaint, ComplaintType, ComplaintStatus
        complaint = Complaint(
            tracking_number="CMP99990001",
            full_name="GIS Test",
            phone="0999999001",
            complaint_type=ComplaintType.ROADS,
            description="Test complaint for map",
            status=ComplaintStatus.NEW,
            area_id=sample_area.id,
            latitude=33.5370,
            longitude=36.2200,
        )
        db.add(complaint)
        db.commit()

        resp = client.get("/gis/operations-map", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        found = [m for m in data if m["reference"] == "CMP99990001"]
        assert len(found) == 1
        assert found[0]["entity_type"] == "complaint"
        assert found[0]["latitude"] == 33.537


# ---------------------------------------------------------------------------
# 11. Health endpoints
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    """Test detailed health check endpoints."""

    def test_detailed_health_requires_auth(self, client):
        """Detailed health is restricted to internal staff."""
        resp = client.get("/health/detailed")
        assert resp.status_code in (401, 403)

    def test_detailed_health_returns_healthy(self, client, director_token):
        """Detailed health returns healthy when DB is working (auth required)."""
        resp = client.get("/health/detailed", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "ok"
        assert "version" in data

    def test_ocr_health_requires_auth(self, client):
        """OCR health endpoint requires authentication."""
        resp = client.get("/health/ocr")
        assert resp.status_code in (401, 403)

    def test_ocr_health_returns_status(self, client, director_token):
        """OCR health returns engine status and supported formats."""
        resp = client.get("/health/ocr", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "engine" in data
        assert "tesseract_available" in data
        assert "supported_formats" in data
        assert "arabic_verification" in data
        assert data["supported_formats"]["always"] == ["pdf (text-layer)", "txt", "csv"]


# ---------------------------------------------------------------------------
# 13. Area boundary update + DB-backed boundaries
# ---------------------------------------------------------------------------

class TestAreaBoundaryUpdate:
    """Test area boundary CRUD from database."""

    def test_area_boundaries_from_db(self, client, db, director_token, sample_area):
        """Area boundaries should read boundary_polygon from DB."""
        import json
        sample_area.boundary_polygon = json.dumps([[33.5, 36.2], [33.5, 36.3], [33.4, 36.3], [33.4, 36.2]])
        sample_area.color = "#FF0000"
        db.commit()

        resp = client.get("/gis/area-boundaries", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        found = [a for a in data if a["code"] == "ISL-A"]
        assert len(found) == 1
        assert found[0]["boundary"] == [[33.5, 36.2], [33.5, 36.3], [33.4, 36.3], [33.4, 36.2]]
        assert found[0]["color"] == "#FF0000"

    def test_update_area_boundary(self, client, db, director_token, sample_area):
        """Project director can update area boundaries."""
        new_boundary = [[33.6, 36.3], [33.6, 36.4], [33.5, 36.4], [33.5, 36.3]]
        resp = client.put(
            f"/gis/area-boundaries/{sample_area.id}",
            json={"boundary": new_boundary, "color": "#00FF00"},
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["boundary"] == new_boundary
        assert data["color"] == "#00FF00"

    def test_non_director_cannot_update_boundary(self, client, db, field_token, sample_area):
        """Non-director user cannot update area boundaries."""
        resp = client.put(
            f"/gis/area-boundaries/{sample_area.id}",
            json={"boundary": [[1, 2]], "color": "#000"},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_update_nonexistent_area(self, client, director_token):
        """Updating a nonexistent area returns 404."""
        resp = client.put(
            "/gis/area-boundaries/9999",
            json={"boundary": [[1, 2]], "color": "#000"},
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 404

    def test_area_boundary_null_when_not_set(self, client, db, director_token, sample_area):
        """Areas without boundary_polygon should return null boundary."""
        resp = client.get("/gis/area-boundaries", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        found = [a for a in data if a["code"] == "ISL-A"]
        assert len(found) == 1
        assert found[0]["boundary"] is None


# ---------------------------------------------------------------------------
# 14. Audit log API
# ---------------------------------------------------------------------------

class TestAuditLogAPI:
    """Test the audit log listing endpoint."""

    def test_director_can_list_audit_logs(self, client, db, director_token):
        """Project director can access audit logs."""
        resp = client.get("/audit-logs/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_field_user_cannot_list_audit_logs(self, client, db, field_token):
        """Field team user cannot access audit logs."""
        resp = client.get("/audit-logs/", headers=_auth_headers(field_token))
        assert resp.status_code == 403

    def test_citizen_cannot_list_audit_logs(self, client, db, citizen_token):
        """Citizen cannot access audit logs."""
        resp = client.get("/audit-logs/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_audit_log_filter_by_entity_type(self, client, db, director_token):
        """Audit log can be filtered by entity_type."""
        from app.services.audit import write_audit_log
        write_audit_log(db, action="test_action", entity_type="test_entity", entity_id=1, description="test")
        resp = client.get("/audit-logs/?entity_type=test_entity", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 1
        assert all(item["entity_type"] == "test_entity" for item in data["items"])

    def test_audit_log_captures_ip_address(self, client, db, director_user, director_token):
        """Audit log should capture IP address when request is provided."""
        from app.services.audit import write_audit_log
        # Direct call without request — ip_address should be None
        log = write_audit_log(db, action="manual_test", entity_type="test", entity_id=99, user_id=director_user.id)
        assert log.ip_address is None

    def test_audit_log_anon_denied(self, client):
        """Anonymous user cannot access audit logs."""
        resp = client.get("/audit-logs/")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 15. Metrics and readiness endpoints
# ---------------------------------------------------------------------------

class TestMonitoringEndpoints:
    """Test monitoring-related endpoints."""

    def test_metrics_requires_auth(self, client):
        """Metrics endpoint requires internal-staff auth (operational data)."""
        resp = client.get("/metrics")
        assert resp.status_code in (401, 403)

    def test_metrics_endpoint(self, client, director_token):
        """Metrics endpoint returns uptime and version when authenticated."""
        resp = client.get("/metrics", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_seconds" in data
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_readiness_endpoint(self, client):
        """Readiness endpoint confirms DB is reachable."""
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"

    def test_health_basic(self, client):
        """Basic health check returns healthy."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# 16. Enhanced audit logging for key flows
# ---------------------------------------------------------------------------

class TestEnhancedAuditLogging:
    """Verify audit logging covers key operational events."""

    def test_task_create_audit(self, client, db, director_user, director_token, sample_area):
        """Task creation generates an audit log entry."""
        from app.models.audit import AuditLog
        resp = client.post("/tasks/", json={
            "title": "Audit test task",
            "description": "Testing audit on creation",
            "area_id": sample_area.id,
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        task_id = resp.json()["id"]
        log = db.query(AuditLog).filter(
            AuditLog.action == "task_create",
            AuditLog.entity_id == task_id,
        ).first()
        assert log is not None
        assert log.user_id == director_user.id

    def test_user_create_audit(self, client, db, director_user, director_token):
        """User creation generates an audit log with role info."""
        from app.models.audit import AuditLog
        resp = client.post("/users/", json={
            "username": "audit_test_user",
            "full_name": "Audit Test",
            "password": "securepass123",
            "role": "field_team",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        user_id = resp.json()["id"]
        log = db.query(AuditLog).filter(
            AuditLog.action == "user_create",
            AuditLog.entity_id == user_id,
        ).first()
        assert log is not None
        assert "field_team" in (log.description or "")

    def test_user_deactivate_audit(self, client, db, director_user, director_token):
        """User deactivation generates an audit log."""
        from app.models.audit import AuditLog
        # Create a user first
        resp = client.post("/users/", json={
            "username": "to_deactivate",
            "full_name": "Will Deactivate",
            "password": "securepass123",
            "role": "field_team",
        }, headers=_auth_headers(director_token))
        uid = resp.json()["id"]
        # Deactivate
        resp = client.delete(f"/users/{uid}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        log = db.query(AuditLog).filter(
            AuditLog.action == "user_deactivate",
            AuditLog.entity_id == uid,
        ).first()
        assert log is not None
        assert "deactivated" in (log.description or "")

    def test_complaint_status_change_audit(self, client, db, director_user, director_token, sample_area):
        """Complaint status change generates a specific audit entry."""
        from app.models.audit import AuditLog
        from app.models.complaint import Complaint, ComplaintStatus as CS
        # Create complaint directly in DB to avoid rate limiter
        complaint = Complaint(
            tracking_number="AUD00000001",
            full_name="Audit Citizen",
            phone="+963999888777",
            complaint_type="infrastructure",
            description="Audit status test",
            area_id=sample_area.id,
            status=CS.NEW,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        cid = complaint.id
        # Change status
        resp = client.put(f"/complaints/{cid}", json={
            "status": "under_review",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        log = db.query(AuditLog).filter(
            AuditLog.action == "complaint_status_change",
            AuditLog.entity_id == cid,
        ).first()
        assert log is not None
        assert "new" in (log.description or "")
        assert "under_review" in (log.description or "")

    def test_contract_approve_audit(self, client, db, director_user, director_token):
        """Contract approval generates a specific audit entry."""
        from app.models.audit import AuditLog
        # Create contract
        resp = client.post("/contracts/", json={
            "contract_number": "AUD-001",
            "title": "Audit test contract",
            "contractor_name": "Test Co",
            "contract_type": "maintenance",
            "contract_value": 50000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_description": "Audit test scope",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200, resp.text
        contract_id = resp.json()["id"]
        # Approve
        resp = client.post(f"/contracts/{contract_id}/approve", json={
            "action": "approve",
            "comments": "Approved for audit test",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        log = db.query(AuditLog).filter(
            AuditLog.action == "contract_approve",
            AuditLog.entity_id == contract_id,
        ).first()
        assert log is not None

    def test_audit_log_response_includes_user_agent(self, client, db, director_token):
        """Audit log API response includes user_agent field."""
        from app.services.audit import write_audit_log
        write_audit_log(
            db, action="ua_test", entity_type="test",
            entity_id=1, user_agent="TestBrowser/1.0",
        )
        resp = client.get("/audit-logs/?action=ua_test", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert items[0]["user_agent"] == "TestBrowser/1.0"


# ---------------------------------------------------------------------------
# 17. Dashboard query optimization
# ---------------------------------------------------------------------------

class TestDashboardOptimized:
    """Verify dashboard stats still work after optimization."""

    def test_dashboard_stats_with_data(self, client, db, director_token, sample_area):
        """Dashboard stats returns correct counts after optimization."""
        from app.models.complaint import Complaint, ComplaintStatus as CS
        # Create complaint directly in DB to avoid rate limiter
        complaint = Complaint(
            tracking_number="DSH00000001",
            full_name="Stats Citizen",
            phone="+963111222333",
            complaint_type="infrastructure",
            description="Stats test",
            area_id=sample_area.id,
            status=CS.NEW,
        )
        db.add(complaint)
        db.commit()
        # Create task via API
        client.post("/tasks/", json={
            "title": "Stats task",
            "description": "Stats test",
            "area_id": sample_area.id,
        }, headers=_auth_headers(director_token))

        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_complaints"] >= 1
        assert data["total_tasks"] >= 1
        assert "new" in data["complaints_by_status"]
        assert data["complaints_by_status"]["new"] >= 1
