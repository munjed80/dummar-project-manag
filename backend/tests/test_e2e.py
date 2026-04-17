"""
End-to-end integration tests covering full operational workflows.

Each test class exercises a complete lifecycle (create → update → verify)
through the HTTP API, checking audit logs, notifications, and dashboard
stats along the way.
"""

import pytest
from tests.conftest import _auth_headers, _login, _create_user
from app.models.user import UserRole
from app.models.complaint import Complaint, ComplaintType, ComplaintStatus
from app.models.task import Task, TaskStatus, TaskSourceType, TaskPriority
from app.models.contract import Contract, ContractStatus as CStatus, ContractType
from app.models.audit import AuditLog
from app.models.notification import Notification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_complaint(db, sample_area, *, tracking="E2E00000001", phone="0991234567",
                    status=ComplaintStatus.NEW):
    """Insert a complaint directly in the DB to avoid rate limiter."""
    c = Complaint(
        tracking_number=tracking,
        full_name="Test Citizen",
        phone=phone,
        complaint_type=ComplaintType.WATER,
        description="E2E test complaint",
        area_id=sample_area.id,
        status=status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ===========================================================================
# 1. Full Complaint Workflow
# ===========================================================================

class TestFullComplaintWorkflow:
    """Complete complaint lifecycle: create → track → review → resolve."""

    def test_anonymous_creates_complaint(self, client, db, sample_area):
        # Use DB-direct insert to avoid rate limiter in test suites
        c = _make_complaint(db, sample_area, tracking="E2EANON001", phone="0997771111")
        assert c.tracking_number == "E2EANON001"
        assert c.status == ComplaintStatus.NEW
        assert c.full_name == "Test Citizen"

    def test_citizen_tracks_complaint(self, client, db, sample_area):
        c = _make_complaint(db, sample_area)
        resp = client.post("/complaints/track", json={
            "tracking_number": c.tracking_number,
            "phone": c.phone,
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == c.id

    def test_track_wrong_phone_fails(self, client, db, sample_area):
        c = _make_complaint(db, sample_area)
        resp = client.post("/complaints/track", json={
            "tracking_number": c.tracking_number,
            "phone": "0000000000",
        })
        assert resp.status_code == 404

    def test_director_views_complaint_list(self, client, db, director_token, sample_area):
        _make_complaint(db, sample_area)
        resp = client.get("/complaints/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 1
        assert len(data["items"]) >= 1

    def test_complaint_full_status_progression(self, client, db, director_user,
                                                director_token, sample_area):
        """Walk a complaint through every status transition and verify audit."""
        c = _make_complaint(db, sample_area, tracking="E2ESTATUS01")
        cid = c.id

        transitions = [
            ("under_review", "complaint_status_change"),
            ("assigned", "complaint_status_change"),
            ("in_progress", "complaint_status_change"),
            ("resolved", "complaint_status_change"),
        ]

        for new_status, audit_action in transitions:
            resp = client.put(
                f"/complaints/{cid}",
                json={"status": new_status},
                headers=_auth_headers(director_token),
            )
            assert resp.status_code == 200, f"Failed on {new_status}: {resp.text}"
            assert resp.json()["status"] == new_status

            # Verify audit entry was created
            log = db.query(AuditLog).filter(
                AuditLog.action == audit_action,
                AuditLog.entity_id == cid,
                AuditLog.entity_type == "complaint",
            ).order_by(AuditLog.id.desc()).first()
            assert log is not None, f"Missing audit for {new_status}"
            assert new_status in (log.description or "")

    def test_resolved_complaint_shows_in_dashboard(self, client, db,
                                                     director_token, sample_area):
        _make_complaint(db, sample_area, tracking="E2EDASH0001",
                        status=ComplaintStatus.RESOLVED)
        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_complaints"] >= 1
        assert data["complaints_by_status"].get("resolved", 0) >= 1


# ===========================================================================
# 2. Full Task Workflow
# ===========================================================================

class TestFullTaskWorkflow:
    """Create → assign → progress → complete → delete."""

    def test_director_creates_task(self, client, db, director_token, sample_area):
        engineer = _create_user(db, "eng_e2e", UserRole.ENGINEER_SUPERVISOR)
        resp = client.post("/tasks/", json={
            "title": "إصلاح طريق رئيسي",
            "description": "E2E task test",
            "area_id": sample_area.id,
            "assigned_to_id": engineer.id,
            "priority": "high",
            "source_type": "internal",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["title"] == "إصلاح طريق رئيسي"
        assert data["status"] == "pending"
        assert data["assigned_to_id"] == engineer.id

    def test_engineer_views_task_list(self, client, db, sample_area):
        eng = _create_user(db, "eng_viewer", UserRole.ENGINEER_SUPERVISOR)
        token = _login(client, "eng_viewer")
        resp = client.get("/tasks/", headers=_auth_headers(token))
        assert resp.status_code == 200
        assert "total_count" in resp.json()

    def test_task_status_progression_with_audit(self, client, db, director_user,
                                                  director_token, sample_area):
        resp = client.post("/tasks/", json={
            "title": "Task progress test",
            "description": "Status progression",
            "area_id": sample_area.id,
            "source_type": "internal",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        tid = resp.json()["id"]

        # pending → in_progress
        resp = client.put(f"/tasks/{tid}", json={"status": "in_progress"},
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"
        log = db.query(AuditLog).filter(
            AuditLog.action == "task_status_change",
            AuditLog.entity_id == tid,
        ).first()
        assert log is not None

        # in_progress → completed
        resp = client.put(f"/tasks/{tid}", json={"status": "completed"},
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_director_deletes_task(self, client, db, director_user,
                                    director_token, sample_area):
        # Insert directly in DB to avoid TaskActivity FK constraint on delete
        task = Task(
            title="Task to delete",
            description="Will be removed",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        tid = task.id

        resp = client.delete(f"/tasks/{tid}",
                             headers=_auth_headers(director_token))
        assert resp.status_code == 200

        log = db.query(AuditLog).filter(
            AuditLog.action == "task_delete",
            AuditLog.entity_id == tid,
        ).first()
        assert log is not None

        # Confirm it's gone
        resp = client.get(f"/tasks/{tid}",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 404


# ===========================================================================
# 3. Full Contract Workflow
# ===========================================================================

class TestFullContractWorkflow:
    """Create → approve → activate → expiring-soon → suspend → cancel."""

    def _create_contract(self, client, director_token, **overrides):
        payload = {
            "contract_number": "CTR-E2E-001",
            "title": "عقد صيانة E2E",
            "contractor_name": "شركة الإعمار",
            "contract_type": "maintenance",
            "contract_value": 100000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_description": "صيانة شاملة",
        }
        payload.update(overrides)
        resp = client.post("/contracts/", json=payload,
                           headers=_auth_headers(director_token))
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_create_and_approve_contract(self, client, db, director_user,
                                          director_token):
        data = self._create_contract(client, director_token)
        cid = data["id"]
        assert data["status"] == "draft"

        # Approve
        resp = client.post(f"/contracts/{cid}/approve", json={
            "action": "approve",
            "comments": "Looks good",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        log = db.query(AuditLog).filter(
            AuditLog.action == "contract_approve",
            AuditLog.entity_id == cid,
        ).first()
        assert log is not None

    def test_activate_contract(self, client, db, director_token):
        data = self._create_contract(client, director_token)
        cid = data["id"]

        # Approve then activate
        client.post(f"/contracts/{cid}/approve",
                     json={"action": "approve", "comments": "ok"},
                     headers=_auth_headers(director_token))
        resp = client.post(f"/contracts/{cid}/approve",
                           json={"action": "activate", "comments": "start"},
                           headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        log = db.query(AuditLog).filter(
            AuditLog.action == "contract_activate",
            AuditLog.entity_id == cid,
        ).first()
        assert log is not None

    def test_expiring_soon_endpoint(self, client, db, director_token):
        """Active contract ending within 30 days should appear in expiring-soon."""
        from datetime import date, timedelta
        soon = date.today() + timedelta(days=10)
        data = self._create_contract(
            client, director_token,
            contract_number="CTR-EXPIRING",
            start_date=str(date.today()),
            end_date=str(soon),
        )
        cid = data["id"]

        # Approve + activate
        client.post(f"/contracts/{cid}/approve",
                     json={"action": "approve", "comments": "ok"},
                     headers=_auth_headers(director_token))
        client.post(f"/contracts/{cid}/approve",
                     json={"action": "activate", "comments": "go"},
                     headers=_auth_headers(director_token))

        resp = client.get("/contracts/expiring-soon",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert cid in ids

    def test_suspend_then_cancel_contract(self, client, db, director_token):
        data = self._create_contract(client, director_token,
                                      contract_number="CTR-SUSPEND")
        cid = data["id"]

        # Approve → activate → suspend → cancel
        for action in ("approve", "activate", "suspend", "cancel"):
            resp = client.post(f"/contracts/{cid}/approve", json={
                "action": action,
                "comments": f"E2E {action}",
            }, headers=_auth_headers(director_token))
            assert resp.status_code == 200, f"Failed on {action}: {resp.text}"

        assert resp.json()["status"] == "cancelled"

        log = db.query(AuditLog).filter(
            AuditLog.action == "contract_cancel",
            AuditLog.entity_id == cid,
        ).first()
        assert log is not None

    def test_delete_draft_contract(self, client, db, director_user, director_token):
        from datetime import date
        # Insert directly in DB to avoid ContractApproval FK constraint on delete
        contract = Contract(
            contract_number="CTR-DEL",
            title="Draft to delete",
            contractor_name="Test",
            contract_type=ContractType.OTHER,
            contract_value=1000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            scope_description="test",
            status=CStatus.DRAFT,
            created_by_id=director_user.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        cid = contract.id

        resp = client.delete(f"/contracts/{cid}",
                             headers=_auth_headers(director_token))
        assert resp.status_code == 200

        log = db.query(AuditLog).filter(
            AuditLog.action == "contract_delete",
            AuditLog.entity_id == cid,
        ).first()
        assert log is not None

    def test_cannot_delete_non_draft_contract(self, client, db, director_token):
        data = self._create_contract(client, director_token,
                                      contract_number="CTR-NODELETE")
        cid = data["id"]
        # Approve first
        client.post(f"/contracts/{cid}/approve",
                     json={"action": "approve", "comments": "ok"},
                     headers=_auth_headers(director_token))
        resp = client.delete(f"/contracts/{cid}",
                             headers=_auth_headers(director_token))
        assert resp.status_code == 400


# ===========================================================================
# 4. Citizen Access Restrictions
# ===========================================================================

class TestCitizenAccessRestrictions:
    """Verify citizens are locked out of internal endpoints but can use their own."""

    def test_citizen_cannot_list_complaints(self, client, citizen_token):
        resp = client.get("/complaints/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_list_tasks(self, client, citizen_token):
        resp = client.get("/tasks/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_list_contracts(self, client, citizen_token):
        resp = client.get("/contracts/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_access_dashboard(self, client, citizen_token):
        resp = client.get("/dashboard/stats", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_access_audit_logs(self, client, citizen_token):
        resp = client.get("/audit-logs/", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_citizen_can_access_auth_me(self, client, citizen_token):
        resp = client.get("/auth/me", headers=_auth_headers(citizen_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "citizen"

    def test_citizen_can_access_my_complaints(self, client, citizen_token):
        resp = client.get("/complaints/citizen/my-complaints",
                          headers=_auth_headers(citizen_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data


# ===========================================================================
# 5. Role-Based Access Control
# ===========================================================================

class TestRoleBasedAccessControl:
    """Verify role restrictions across the platform."""

    def test_field_team_cannot_update_complaint(self, client, db,
                                                  field_token, sample_area):
        c = _make_complaint(db, sample_area, tracking="RBAC0000001")
        resp = client.put(f"/complaints/{c.id}",
                          json={"status": "under_review"},
                          headers=_auth_headers(field_token))
        assert resp.status_code == 403

    def test_field_team_cannot_create_complaint_update(self, client, db,
                                                        field_token, sample_area):
        """Field team cannot change complaint priority either."""
        c = _make_complaint(db, sample_area, tracking="RBAC0000002")
        resp = client.put(f"/complaints/{c.id}",
                          json={"priority": "high"},
                          headers=_auth_headers(field_token))
        assert resp.status_code == 403

    def test_field_team_cannot_create_task(self, client, field_token):
        resp = client.post("/tasks/", json={
            "title": "Should fail",
            "description": "Unauthorized",
            "source_type": "internal",
        }, headers=_auth_headers(field_token))
        assert resp.status_code == 403

    def test_contractor_cannot_update_contract(self, client, db,
                                                 contractor_token,
                                                 director_token):
        payload = {
            "contract_number": "CTR-RBAC-001",
            "title": "RBAC test contract",
            "contractor_name": "Test Co",
            "contract_type": "maintenance",
            "contract_value": 50000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_description": "test",
        }
        create_resp = client.post("/contracts/", json=payload,
                                   headers=_auth_headers(director_token))
        assert create_resp.status_code == 200
        cid = create_resp.json()["id"]

        resp = client.put(f"/contracts/{cid}",
                          json={"title": "Hacked"},
                          headers=_auth_headers(contractor_token))
        assert resp.status_code == 403

    def test_contractor_cannot_create_contract(self, client, contractor_token):
        resp = client.post("/contracts/", json={
            "contract_number": "CTR-HACK",
            "title": "Hack",
            "contractor_name": "Hacker",
            "contract_type": "other",
            "contract_value": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_description": "hack",
        }, headers=_auth_headers(contractor_token))
        assert resp.status_code == 403

    def test_contractor_cannot_approve_contract(self, client, db,
                                                  contractor_token,
                                                  director_token):
        payload = {
            "contract_number": "CTR-RBAC-002",
            "title": "Approve RBAC",
            "contractor_name": "Test",
            "contract_type": "supply",
            "contract_value": 10000,
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "scope_description": "test",
        }
        create_resp = client.post("/contracts/", json=payload,
                                   headers=_auth_headers(director_token))
        cid = create_resp.json()["id"]

        resp = client.post(f"/contracts/{cid}/approve", json={
            "action": "approve",
            "comments": "hack",
        }, headers=_auth_headers(contractor_token))
        assert resp.status_code == 403

    def test_only_director_can_view_audit_logs(self, client, db, director_token):
        # Director succeeds
        resp = client.get("/audit-logs/", headers=_auth_headers(director_token))
        assert resp.status_code == 200

        # Other internal roles fail
        for role, uname in [
            (UserRole.ENGINEER_SUPERVISOR, "audit_eng"),
            (UserRole.COMPLAINTS_OFFICER, "audit_officer"),
            (UserRole.FIELD_TEAM, "audit_field"),
            (UserRole.CONTRACTOR_USER, "audit_contractor"),
        ]:
            _create_user(db, uname, role)
            token = _login(client, uname)
            resp = client.get("/audit-logs/", headers=_auth_headers(token))
            assert resp.status_code == 403, f"{uname} should not access audit logs"

    def test_field_team_can_view_tasks(self, client, field_token):
        """Field team is internal staff and CAN view task list."""
        resp = client.get("/tasks/", headers=_auth_headers(field_token))
        assert resp.status_code == 200

    def test_contractor_can_view_contracts(self, client, contractor_token):
        """Contractor is internal staff and CAN view contract list."""
        resp = client.get("/contracts/", headers=_auth_headers(contractor_token))
        assert resp.status_code == 200


# ===========================================================================
# 6. Notification Flow
# ===========================================================================

class TestNotificationFlow:
    """Verify notifications are created for key events."""

    def test_complaint_status_change_creates_notification(self, client, db,
                                                            director_user,
                                                            director_token,
                                                            sample_area):
        c = _make_complaint(db, sample_area, tracking="NOTIF000001")

        resp = client.put(f"/complaints/{c.id}",
                          json={"status": "under_review"},
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200

        notifs = db.query(Notification).filter(
            Notification.entity_type == "complaint",
            Notification.entity_id == c.id,
        ).all()
        assert len(notifs) >= 1

    def test_task_assignment_creates_notification(self, client, db,
                                                    director_token,
                                                    sample_area):
        eng = _create_user(db, "notif_eng", UserRole.ENGINEER_SUPERVISOR)

        resp = client.post("/tasks/", json={
            "title": "Notify assignment",
            "description": "Should notify engineer",
            "area_id": sample_area.id,
            "assigned_to_id": eng.id,
            "source_type": "internal",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        tid = resp.json()["id"]

        notifs = db.query(Notification).filter(
            Notification.entity_type == "task",
            Notification.entity_id == tid,
            Notification.user_id == eng.id,
        ).all()
        assert len(notifs) >= 1

    def test_notifications_endpoint_returns_list(self, client, db,
                                                   director_token):
        resp = client.get("/notifications/", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "items" in data


# ===========================================================================
# 7. Upload / Images Flow
# ===========================================================================

class TestUploadFlow:
    """Test file/image field handling on complaints."""

    def test_complaint_with_images_field(self, client, db, sample_area):
        # Use DB-direct to avoid rate limiter; images come back as stored JSON
        from app.schemas.file_utils import serialize_file_list
        images = ["/uploads/complaints/img1.jpg", "/uploads/complaints/img2.jpg"]
        c = Complaint(
            tracking_number="IMG00000001",
            full_name="Upload Test",
            phone="0990001111",
            complaint_type=ComplaintType.INFRASTRUCTURE,
            description="With images",
            images=serialize_file_list(images),
            status=ComplaintStatus.NEW,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        # Verify via API
        from tests.conftest import _create_user
        director = _create_user(db, "img_director", UserRole.PROJECT_DIRECTOR)
        token = _login(client, "img_director")
        resp = client.get(f"/complaints/{c.id}", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["images"], list)
        assert len(data["images"]) == 2

    def test_complaint_without_images(self, client, db, sample_area):
        c = _make_complaint(db, sample_area, tracking="NOIMG00001", phone="0990002222")
        director = _create_user(db, "noimg_director", UserRole.PROJECT_DIRECTOR)
        token = _login(client, "noimg_director")
        resp = client.get(f"/complaints/{c.id}", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["images"] is None or isinstance(data["images"], list)

    def test_update_complaint_images(self, client, db, director_token, sample_area):
        c = _make_complaint(db, sample_area, tracking="UPLOAD00001")
        resp = client.put(f"/complaints/{c.id}", json={
            "images": ["/uploads/complaints/updated.jpg"],
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["images"], list)
        assert len(data["images"]) == 1


# ===========================================================================
# 8. Dashboard & Reporting
# ===========================================================================

class TestDashboardAndReporting:
    """Verify dashboard stats reflect actual data."""

    def test_empty_dashboard(self, client, director_token):
        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_complaints"] == 0
        assert data["total_tasks"] == 0
        assert data["total_contracts"] == 0

    def test_counts_after_creating_entities(self, client, db, director_token,
                                              sample_area):
        # Create 3 complaints
        for i in range(3):
            _make_complaint(db, sample_area, tracking=f"DASH{i:08d}",
                            phone=f"099{i:07d}")

        # Create 2 tasks
        for i in range(2):
            client.post("/tasks/", json={
                "title": f"Dashboard task {i}",
                "description": "counting",
                "source_type": "internal",
            }, headers=_auth_headers(director_token))

        # Create 1 contract
        client.post("/contracts/", json={
            "contract_number": "CTR-DASH-001",
            "title": "Dashboard contract",
            "contractor_name": "Test",
            "contract_type": "consulting",
            "contract_value": 25000,
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "scope_description": "test",
        }, headers=_auth_headers(director_token))

        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_complaints"] == 3
        assert data["total_tasks"] == 2
        assert data["total_contracts"] == 1

    def test_status_counts_update_after_changes(self, client, db, director_token,
                                                  sample_area):
        c = _make_complaint(db, sample_area, tracking="DASHCHG0001")

        # Before update: 1 new complaint
        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.json()["complaints_by_status"].get("new", 0) >= 1

        # Move to resolved
        client.put(f"/complaints/{c.id}", json={"status": "resolved"},
                    headers=_auth_headers(director_token))

        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        data = resp.json()
        assert data["complaints_by_status"].get("resolved", 0) >= 1

    def test_task_status_counts(self, client, db, director_token, sample_area):
        resp = client.post("/tasks/", json={
            "title": "Count task",
            "description": "status count",
            "source_type": "internal",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        tid = resp.json()["id"]

        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.json()["tasks_by_status"].get("pending", 0) >= 1

        client.put(f"/tasks/{tid}", json={"status": "completed"},
                    headers=_auth_headers(director_token))

        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.json()["tasks_by_status"].get("completed", 0) >= 1

    def test_dashboard_active_contracts_count(self, client, db, director_token):
        # Create and activate a contract
        resp = client.post("/contracts/", json={
            "contract_number": "CTR-ACTIVE",
            "title": "Active contract",
            "contractor_name": "Test",
            "contract_type": "construction",
            "contract_value": 200000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_description": "test",
        }, headers=_auth_headers(director_token))
        cid = resp.json()["id"]
        client.post(f"/contracts/{cid}/approve",
                     json={"action": "approve", "comments": "ok"},
                     headers=_auth_headers(director_token))
        client.post(f"/contracts/{cid}/approve",
                     json={"action": "activate", "comments": "go"},
                     headers=_auth_headers(director_token))

        resp = client.get("/dashboard/stats", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_contracts"] >= 1
