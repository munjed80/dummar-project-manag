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
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus, ComplaintType
from app.models.team import Team, TeamType
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

    def test_first_conversion_succeeds(self, client, db, director_token, director_user):
        c = self._make_heating_complaint(db)
        resp = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix", "assigned_to_id": director_user.id},
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200, resp.text

    def test_second_conversion_blocked_with_409(
        self, client, db, director_token, director_user
    ):
        c = self._make_heating_complaint(db)
        r1 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix", "assigned_to_id": director_user.id},
            headers=_auth_headers(director_token),
        )
        assert r1.status_code == 200, r1.text
        r2 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair2", "description": "Fix2", "assigned_to_id": director_user.id},
            headers=_auth_headers(director_token),
        )
        assert r2.status_code == 409
        assert "already exists" in (r2.json().get("detail") or "")

    def test_force_flag_allows_additional_task(
        self, client, db, director_token, director_user
    ):
        c = self._make_heating_complaint(db)
        client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix", "assigned_to_id": director_user.id},
            headers=_auth_headers(director_token),
        )
        r2 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Followup", "description": "Followup", "assigned_to_id": director_user.id, "force": True},
            headers=_auth_headers(director_token),
        )
        assert r2.status_code == 200, r2.text

    def test_cancelled_task_does_not_block_new_one(
        self, client, db, director_token, director_user
    ):
        c = self._make_heating_complaint(db)
        r1 = client.post(
            f"/complaints/{c.id}/create-task",
            json={"title": "Repair", "description": "Fix", "assigned_to_id": director_user.id},
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
            json={"title": "New", "description": "New", "assigned_to_id": director_user.id},
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


class TestComplaintToMaintenanceWorkflow:
    def test_end_to_end_heating_complaint_to_resolution(
        self, client, db, director_token, field_user
    ):
        # 1) Resident submits heating complaint with a photo.
        create = client.post(
            "/complaints/",
            json={
                "full_name": "Resident A",
                "phone": "0998888888",
                "complaint_type": "heating_network",
                "description": "Boiler leak in stairwell",
                "location_text": "Building A - Floor 2",
                "images": ["complaints/before_heat_1.jpg"],
                "priority": "high",
            },
        )
        assert create.status_code == 200, create.text
        complaint = create.json()

        # 2) Admin converts complaint to task and assigns a responsible user.
        convert = client.post(
            f"/complaints/{complaint['id']}/create-task",
            json={
                "title": "Fix heating leak",
                "description": "Inspect and replace faulty valve",
                "assigned_to_id": field_user.id,
            },
            headers=_auth_headers(director_token),
        )
        assert convert.status_code == 200, convert.text
        task = convert.json()
        assert task["complaint_id"] == complaint["id"]
        assert task["location_text"] == "Building A - Floor 2"
        assert task["before_photos"] == ["complaints/before_heat_1.jpg"]

        # 3) Assigned field worker sees only own task and can execute it.
        field_token = _login(client, field_user.username)
        own_list = client.get("/tasks/", headers=_auth_headers(field_token))
        assert own_list.status_code == 200, own_list.text
        ids = {t["id"] for t in own_list.json()["items"]}
        assert task["id"] in ids

        in_progress = client.put(
            f"/tasks/{task['id']}",
            json={"status": "in_progress"},
            headers=_auth_headers(field_token),
        )
        assert in_progress.status_code == 200, in_progress.text

        completed = client.put(
            f"/tasks/{task['id']}",
            json={
                "status": "completed",
                "notes": "Valve replaced and pressure tested",
                "after_photos": ["tasks/after_heat_1.jpg"],
            },
            headers=_auth_headers(field_token),
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["after_photos"] == ["tasks/after_heat_1.jpg"]

        # 4) Director reviews task result and resolves the original complaint.
        reviewed = client.get(f"/tasks/{task['id']}", headers=_auth_headers(director_token))
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "completed"
        assert reviewed.json()["notes"] == "Valve replaced and pressure tested"
        assert reviewed.json()["after_photos"] == ["tasks/after_heat_1.jpg"]

        resolve = client.put(
            f"/complaints/{complaint['id']}",
            json={"status": "resolved"},
            headers=_auth_headers(director_token),
        )
        assert resolve.status_code == 200, resolve.text
        assert resolve.json()["status"] == "resolved"

        # 5) Public tracking reveals repair_result only after resolution.
        tracked = client.post(
            "/complaints/track",
            json={"tracking_number": complaint["tracking_number"], "phone": "0998888888"},
        )
        assert tracked.status_code == 200, tracked.text
        repair = tracked.json()["repair_result"]
        assert repair is not None
        assert repair["notes"] == "Valve replaced and pressure tested"
        assert repair["after_photos"] == ["tasks/after_heat_1.jpg"]
        assert repair["task_status"] == "completed"

    def test_create_task_allows_team_assignment_without_user(
        self, client, db, director_token
    ):
        team = Team(name="Field Crew A", team_type=TeamType.FIELD_CREW)
        db.add(team)
        db.commit()
        db.refresh(team)

        complaint = Complaint(
            tracking_number="CMPTEAMWARN1",
            full_name="Resident",
            phone="0991212121",
            complaint_type=ComplaintType.HEATING_NETWORK,
            description="desc",
            status=ComplaintStatus.NEW,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        resp = client.post(
            f"/complaints/{complaint.id}/create-task",
            json={"title": "Repair", "description": "d", "team_id": team.id},
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["team_id"] == team.id
        assert resp.json()["assigned_to_id"] is None

    def test_create_task_requires_assignee_or_team(
        self, client, db, director_token
    ):
        complaint = Complaint(
            tracking_number="CMPTEAMWARN2",
            full_name="Resident",
            phone="0991212122",
            complaint_type=ComplaintType.HEATING_NETWORK,
            description="desc",
            status=ComplaintStatus.NEW,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        resp = client.post(
            f"/complaints/{complaint.id}/create-task",
            json={"title": "Repair", "description": "d"},
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 422
        assert "assigned_to_id or team_id" in (resp.json().get("detail") or "")

    def test_create_task_priority_is_safely_mapped(
        self, client, db, director_token, field_user
    ):
        complaint = Complaint(
            tracking_number="CMPPRIOR001",
            full_name="Resident",
            phone="0993434343",
            complaint_type=ComplaintType.HEATING_NETWORK,
            description="desc",
            status=ComplaintStatus.NEW,
            priority=ComplaintPriority.HIGH,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        # Default from complaint priority
        default_resp = client.post(
            f"/complaints/{complaint.id}/create-task",
            json={"title": "Repair", "description": "d", "assigned_to_id": field_user.id},
            headers=_auth_headers(director_token),
        )
        assert default_resp.status_code == 200, default_resp.text
        created = db.query(Task).filter(Task.id == default_resp.json()["id"]).first()
        assert created is not None
        assert created.priority == TaskPriority.HIGH

        # Explicit valid task priority by value
        second = client.post(
            f"/complaints/{complaint.id}/create-task",
            json={
                "title": "Repair 2",
                "description": "d2",
                "assigned_to_id": field_user.id,
                "priority": "urgent",
                "force": True,
            },
            headers=_auth_headers(director_token),
        )
        assert second.status_code == 200, second.text
        created2 = db.query(Task).filter(Task.id == second.json()["id"]).first()
        assert created2 is not None
        assert created2.priority == TaskPriority.URGENT

        invalid = client.post(
            f"/complaints/{complaint.id}/create-task",
            json={
                "title": "Repair 3",
                "description": "d3",
                "assigned_to_id": field_user.id,
                "priority": "invalid_priority",
                "force": True,
            },
            headers=_auth_headers(director_token),
        )
        assert invalid.status_code == 422
