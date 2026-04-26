"""Tests for the field-team / contractor task workflow and the public
heating complaint type plus public-tracking repair-result surfacing.

Covers:
  * Field-team / contractor users CAN update a task assigned to them via
    PUT /tasks/{id}, restricted to safe fields (status, notes, photos).
  * They CANNOT change assignment, team, project, title, priority, etc.
  * They CANNOT update a task that is not assigned to them.
  * They CAN only set status to in_progress or completed.
  * The public submit form accepts the new HEATING_NETWORK complaint type.
  * /complaints/track exposes a public-safe ``repair_result`` block once
    the complaint is resolved and a linked task captured after-photos /
    notes.
"""
from app.models.user import UserRole
from app.models.task import Task, TaskStatus
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from tests.test_e2e import _auth_headers, _create_user, _login


def _make_task(db, *, assigned_to_id=None, org_unit_id=None,
               status=TaskStatus.ASSIGNED) -> Task:
    t = Task(
        title="Heating fix",
        description="Fix heating riser",
        assigned_to_id=assigned_to_id,
        org_unit_id=org_unit_id,
        status=status,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


class TestFieldTeamTaskUpdates:
    def test_field_team_can_update_assigned_task_status(
        self, client, db, field_user, field_token
    ):
        t = _make_task(db, assigned_to_id=field_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={"status": "in_progress", "notes": "Started repair"},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "in_progress"
        assert body["notes"] == "Started repair"

    def test_field_team_can_complete_assigned_task_with_after_photos(
        self, client, db, field_user, field_token
    ):
        t = _make_task(db, assigned_to_id=field_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={
                "status": "completed",
                "after_photos": ["tasks/after1.jpg"],
            },
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert body["after_photos"] == ["tasks/after1.jpg"]
        assert body["completed_at"] is not None

    def test_field_team_cannot_reassign_task(
        self, client, db, field_user, field_token, director_user
    ):
        t = _make_task(db, assigned_to_id=field_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={"assigned_to_id": director_user.id},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_field_team_cannot_change_title_or_priority(
        self, client, db, field_user, field_token
    ):
        t = _make_task(db, assigned_to_id=field_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={"priority": "urgent"},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_field_team_cannot_set_status_to_cancelled(
        self, client, db, field_user, field_token
    ):
        t = _make_task(db, assigned_to_id=field_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={"status": "cancelled"},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_field_team_cannot_update_unassigned_task(
        self, client, db, field_user, field_token, director_user
    ):
        # Task assigned to someone else
        t = _make_task(db, assigned_to_id=director_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={"status": "in_progress"},
            headers=_auth_headers(field_token),
        )
        assert resp.status_code == 403

    def test_contractor_can_update_assigned_task(
        self, client, db, contractor_user, contractor_token
    ):
        t = _make_task(db, assigned_to_id=contractor_user.id)
        resp = client.put(
            f"/tasks/{t.id}",
            json={"status": "in_progress", "notes": "On site"},
            headers=_auth_headers(contractor_token),
        )
        assert resp.status_code == 200, resp.text


class TestFieldTeamTaskListScoping:
    """List/detail visibility: field_team & contractor see only their own."""

    def test_field_team_list_excludes_unassigned_tasks(
        self, client, db, field_user, field_token, director_user
    ):
        own = _make_task(db, assigned_to_id=field_user.id)
        other = _make_task(db, assigned_to_id=director_user.id)
        unassigned = _make_task(db, assigned_to_id=None)
        resp = client.get("/tasks/", headers=_auth_headers(field_token))
        assert resp.status_code == 200, resp.text
        ids = {t["id"] for t in resp.json()["items"]}
        assert own.id in ids
        assert other.id not in ids
        assert unassigned.id not in ids

    def test_contractor_list_excludes_unassigned_tasks(
        self, client, db, contractor_user, contractor_token, director_user
    ):
        own = _make_task(db, assigned_to_id=contractor_user.id)
        other = _make_task(db, assigned_to_id=director_user.id)
        resp = client.get("/tasks/", headers=_auth_headers(contractor_token))
        assert resp.status_code == 200, resp.text
        ids = {t["id"] for t in resp.json()["items"]}
        assert own.id in ids
        assert other.id not in ids

    def test_field_team_get_unassigned_task_returns_403(
        self, client, db, field_token, director_user
    ):
        t = _make_task(db, assigned_to_id=director_user.id)
        resp = client.get(f"/tasks/{t.id}", headers=_auth_headers(field_token))
        assert resp.status_code == 403

    def test_director_still_sees_all_tasks(
        self, client, db, field_user, director_token
    ):
        # Sanity: management roles are unaffected by the field-team filter.
        t1 = _make_task(db, assigned_to_id=field_user.id)
        t2 = _make_task(db, assigned_to_id=None)
        resp = client.get("/tasks/", headers=_auth_headers(director_token))
        assert resp.status_code == 200, resp.text
        ids = {t["id"] for t in resp.json()["items"]}
        assert t1.id in ids
        assert t2.id in ids


class TestComplaintToTaskDuplicatePrevention:
    """POST /complaints/{id}/create-task must avoid silently creating
    duplicate tasks for the same complaint unless force=true."""

    def _make_heating_complaint(self, db) -> Complaint:
        c = Complaint(
            tracking_number="CMPHEATDUP1",
            full_name="Dup",
            phone="0994444444",
            complaint_type=ComplaintType.HEATING_NETWORK,
            description="leak",
            status=ComplaintStatus.NEW,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    def test_first_conversion_succeeds(self, client, db, director_token):
        c = self._make_heating_complaint(db)
        resp = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix"},
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200, resp.text

    def test_second_conversion_blocked_with_409(
        self, client, db, director_token
    ):
        c = self._make_heating_complaint(db)
        r1 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix"},
            headers=_auth_headers(director_token),
        )
        assert r1.status_code == 200, r1.text
        r2 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair2", "description": "Fix2"},
            headers=_auth_headers(director_token),
        )
        assert r2.status_code == 409
        assert "already exists" in (r2.json().get("detail") or "")

    def test_force_flag_allows_additional_task(
        self, client, db, director_token
    ):
        c = self._make_heating_complaint(db)
        client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix"},
            headers=_auth_headers(director_token),
        )
        r2 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Followup", "description": "Followup", "force": True},
            headers=_auth_headers(director_token),
        )
        assert r2.status_code == 200, r2.text

    def test_cancelled_task_does_not_block_new_one(
        self, client, db, director_token
    ):
        c = self._make_heating_complaint(db)
        r1 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix"},
            headers=_auth_headers(director_token),
        )
        first_id = r1.json()["id"]
        # Cancel the first task
        cancel = client.put(
            f"/tasks/{first_id}",
            json={"status": "cancelled"},
            headers=_auth_headers(director_token),
        )
        assert cancel.status_code == 200, cancel.text
        # Now a new one should be allowed without force
        r2 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "New", "description": "New"},
            headers=_auth_headers(director_token),
        )
        assert r2.status_code == 200, r2.text


class TestHeatingComplaintType:
    def test_public_can_submit_heating_request(self, client):
        payload = {
            "full_name": "أحمد",
            "phone": "0991111111",
            "complaint_type": "heating_network",
            "description": "تسرب في شبكة التدفئة",
            "location_text": "جزيرة أ، البرج 3، الطابق 2",
        }
        resp = client.post("/complaints/", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["complaint_type"] == "heating_network"
        assert data["tracking_number"]


class TestPublicTrackingRepairResult:
    def test_resolved_complaint_exposes_repair_result(self, client, db):
        # Create complaint
        complaint = Complaint(
            tracking_number="CMPHEAT0001",
            full_name="Tracker",
            phone="0992222222",
            complaint_type=ComplaintType.HEATING_NETWORK,
            description="x",
            status=ComplaintStatus.RESOLVED,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        # Linked task with after-repair evidence
        task = Task(
            title="t",
            description="d",
            complaint_id=complaint.id,
            status=TaskStatus.COMPLETED,
            notes="استبدال صمام رئيسي",
            after_photos='["tasks/after_heat.jpg"]',
        )
        db.add(task)
        db.commit()

        resp = client.post(
            "/complaints/track",
            json={"tracking_number": "CMPHEAT0001", "phone": "0992222222"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["repair_result"] is not None
        assert body["repair_result"]["notes"] == "استبدال صمام رئيسي"
        assert body["repair_result"]["after_photos"] == ["tasks/after_heat.jpg"]
        assert body["repair_result"]["task_status"] == "completed"

    def test_open_complaint_has_no_repair_result(self, client, db):
        complaint = Complaint(
            tracking_number="CMPHEAT0002",
            full_name="Tracker2",
            phone="0993333333",
            complaint_type=ComplaintType.HEATING_NETWORK,
            description="y",
            status=ComplaintStatus.IN_PROGRESS,
        )
        db.add(complaint)
        db.commit()
        resp = client.post(
            "/complaints/track",
            json={"tracking_number": "CMPHEAT0002", "phone": "0993333333"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["repair_result"] is None
