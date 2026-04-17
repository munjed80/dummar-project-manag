"""
Tests for the unified Locations API — hierarchy, detail, stats, reports, search.

Covers:
- Location CRUD (create, list, update, delete)
- Hierarchy (parent-child, tree view, breadcrumb)
- Detail page (dossier with complaints, tasks, contracts)
- Operational statistics and indicators
- Reports endpoint (hotspots, delays, coverage)
- Search and filtering
- Contract-location linking
- Audit logging for location changes
- RBAC enforcement
"""

import pytest
from tests.conftest import _auth_headers, _login, _create_user
from app.models.user import UserRole
from app.models.location import Location, LocationType, LocationStatus, ContractLocation
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.models.task import Task, TaskStatus, TaskSourceType, TaskPriority
from app.models.contract import Contract, ContractType, ContractStatus
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Location CRUD
# ---------------------------------------------------------------------------

class TestLocationCRUD:
    def test_create_location(self, client, db, director_token):
        resp = client.post("/locations/", json={
            "name": "جزيرة 1",
            "code": "ISL-001",
            "location_type": "island",
            "description": "الجزيرة الأولى في مشروع دمر",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "جزيرة 1"
        assert data["code"] == "ISL-001"
        assert data["location_type"] == "island"
        assert data["is_active"] == 1

    def test_create_location_duplicate_code(self, client, db, director_token, sample_location):
        resp = client.post("/locations/", json={
            "name": "duplicate",
            "code": sample_location.code,
            "location_type": "island",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 400

    def test_list_locations(self, client, db, director_token, sample_location):
        resp = client.get("/locations/list", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(loc["code"] == sample_location.code for loc in data)

    def test_update_location(self, client, db, director_token, sample_location):
        resp = client.put(f"/locations/{sample_location.id}", json={
            "description": "وصف محدث",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["description"] == "وصف محدث"

    def test_delete_location_director_only(self, client, db, director_token, field_token, sample_location):
        # Field team cannot delete
        resp = client.delete(f"/locations/{sample_location.id}", headers=_auth_headers(field_token))
        assert resp.status_code == 403

        # Director can delete (soft)
        resp = client.delete(f"/locations/{sample_location.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert resp.json()["message"] == "Location deactivated"

    def test_anon_cannot_access_locations(self, client):
        resp = client.get("/locations/list")
        assert resp.status_code in (401, 403)

    def test_create_with_parent(self, client, db, director_token, sample_location):
        resp = client.post("/locations/", json={
            "name": "قطاع ب",
            "code": "SEC-001-B",
            "location_type": "sector",
            "parent_id": sample_location.id,
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["parent_id"] == sample_location.id

    def test_create_with_invalid_parent(self, client, db, director_token):
        resp = client.post("/locations/", json={
            "name": "child",
            "code": "INVALID-PARENT",
            "location_type": "block",
            "parent_id": 99999,
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Hierarchy and Tree
# ---------------------------------------------------------------------------

class TestLocationHierarchy:
    def test_tree_view(self, client, db, director_token, sample_location_tree):
        resp = client.get("/locations/tree", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        # The island should be a root node
        islands = [n for n in data if n["code"] == "ISL-005"]
        assert len(islands) == 1
        island = islands[0]
        # Island should have sector as child
        assert len(island["children"]) == 1
        sector = island["children"][0]
        assert sector["location_type"] == "sector"
        # Sector should have building as child
        assert len(sector["children"]) == 1
        assert sector["children"][0]["location_type"] == "building"

    def test_detail_breadcrumb(self, client, db, director_token, sample_location_tree):
        building = sample_location_tree["building"]
        resp = client.get(f"/locations/detail/{building.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        # Breadcrumb should have island and sector
        assert len(data["breadcrumb"]) == 2
        assert data["breadcrumb"][0]["code"] == "ISL-005"
        assert data["breadcrumb"][1]["code"] == "SEC-005-A"

    def test_detail_children(self, client, db, director_token, sample_location_tree):
        island = sample_location_tree["island"]
        resp = client.get(f"/locations/detail/{island.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["children"]) == 1
        assert data["children"][0]["code"] == "SEC-005-A"

    def test_detail_not_found(self, client, db, director_token):
        resp = client.get("/locations/detail/99999", headers=_auth_headers(director_token))
        assert resp.status_code == 404

    def test_prevent_circular_parent(self, client, db, director_token, sample_location_tree):
        island = sample_location_tree["island"]
        building = sample_location_tree["building"]
        # Try to make island a child of building (circular)
        resp = client.put(f"/locations/{island.id}", json={
            "parent_id": building.id,
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Location Detail with Operational Data
# ---------------------------------------------------------------------------

class TestLocationDetail:
    def test_detail_with_complaints(self, client, db, director_token, sample_location, sample_area):
        # Create a complaint linked to the location
        complaint = Complaint(
            tracking_number="CMP00010001",
            full_name="محمد أحمد",
            phone="0991111111",
            complaint_type=ComplaintType.WATER,
            description="تسرب مياه",
            status=ComplaintStatus.NEW,
            area_id=sample_area.id,
            location_id=sample_location.id,
        )
        db.add(complaint)
        db.commit()

        resp = client.get(f"/locations/detail/{sample_location.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["complaint_count"] == 1
        assert data["open_complaint_count"] == 1

    def test_detail_complaints_endpoint(self, client, db, director_token, sample_location, sample_area):
        complaint = Complaint(
            tracking_number="CMP00010002",
            full_name="خالد",
            phone="0992222222",
            complaint_type=ComplaintType.ELECTRICITY,
            description="انقطاع كهرباء",
            status=ComplaintStatus.RESOLVED,
            area_id=sample_area.id,
            location_id=sample_location.id,
        )
        db.add(complaint)
        db.commit()

        resp = client.get(f"/locations/detail/{sample_location.id}/complaints",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert len(data["items"]) == 1

    def test_detail_with_tasks(self, client, db, director_token, sample_location):
        task = Task(
            title="صيانة شبكة المياه",
            description="إصلاح أنبوب مكسور",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            location_id=sample_location.id,
        )
        db.add(task)
        db.commit()

        resp = client.get(f"/locations/detail/{sample_location.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_count"] == 1
        assert data["open_task_count"] == 1

    def test_detail_tasks_endpoint(self, client, db, director_token, sample_location):
        task = Task(
            title="مهمة اختبار",
            description="وصف",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            location_id=sample_location.id,
        )
        db.add(task)
        db.commit()

        resp = client.get(f"/locations/detail/{sample_location.id}/tasks",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1

    def test_detail_with_delayed_tasks(self, client, db, director_token, sample_location):
        task = Task(
            title="مهمة متأخرة",
            description="مهمة تجاوزت موعدها",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.URGENT,
            location_id=sample_location.id,
            due_date=date.today() - timedelta(days=5),
        )
        db.add(task)
        db.commit()

        resp = client.get(f"/locations/detail/{sample_location.id}", headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["delayed_task_count"] == 1

    def test_detail_activity_timeline(self, client, db, director_token, sample_location, sample_area):
        complaint = Complaint(
            tracking_number="CMP00010003",
            full_name="أحمد",
            phone="0993333333",
            complaint_type=ComplaintType.ROADS,
            description="حفرة في الشارع",
            status=ComplaintStatus.NEW,
            area_id=sample_area.id,
            location_id=sample_location.id,
        )
        db.add(complaint)
        db.commit()

        resp = client.get(f"/locations/detail/{sample_location.id}/activity",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["type"] == "complaint"


# ---------------------------------------------------------------------------
# Contract-Location Linking
# ---------------------------------------------------------------------------

class TestContractLocationLink:
    def _create_contract(self, db, director_user):
        contract = Contract(
            contract_number="CNT-LOC-001",
            title="عقد صيانة",
            contractor_name="شركة الصيانة",
            contract_type=ContractType.MAINTENANCE,
            contract_value=100000,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            status=ContractStatus.ACTIVE,
            scope_description="صيانة عامة",
            created_by_id=director_user.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    def test_link_contract_to_location(self, client, db, director_user, director_token, sample_location):
        contract = self._create_contract(db, director_user)
        resp = client.post(
            f"/locations/contracts/link?contract_id={contract.id}&location_id={sample_location.id}",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_duplicate_link(self, client, db, director_user, director_token, sample_location):
        contract = self._create_contract(db, director_user)
        client.post(
            f"/locations/contracts/link?contract_id={contract.id}&location_id={sample_location.id}",
            headers=_auth_headers(director_token),
        )
        resp = client.post(
            f"/locations/contracts/link?contract_id={contract.id}&location_id={sample_location.id}",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Link already exists"

    def test_unlink_contract(self, client, db, director_user, director_token, sample_location):
        contract = self._create_contract(db, director_user)
        client.post(
            f"/locations/contracts/link?contract_id={contract.id}&location_id={sample_location.id}",
            headers=_auth_headers(director_token),
        )
        resp = client.delete(
            f"/locations/contracts/link?contract_id={contract.id}&location_id={sample_location.id}",
            headers=_auth_headers(director_token),
        )
        assert resp.status_code == 200

    def test_detail_contracts_endpoint(self, client, db, director_user, director_token, sample_location):
        contract = self._create_contract(db, director_user)
        client.post(
            f"/locations/contracts/link?contract_id={contract.id}&location_id={sample_location.id}",
            headers=_auth_headers(director_token),
        )
        resp = client.get(f"/locations/detail/{sample_location.id}/contracts",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1


# ---------------------------------------------------------------------------
# Search and Filtering
# ---------------------------------------------------------------------------

class TestLocationSearch:
    def test_search_by_name(self, client, db, director_token, sample_location):
        resp = client.get("/locations/list?search=جزيرة",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_filter_by_type(self, client, db, director_token, sample_location):
        resp = client.get("/locations/list?location_type=island",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert all(loc["location_type"] == "island" for loc in data)

    def test_filter_by_status(self, client, db, director_token, sample_location):
        resp = client.get("/locations/list?status=active",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200

    def test_filter_root_locations(self, client, db, director_token, sample_location):
        resp = client.get("/locations/list?parent_id=0",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert all(loc["parent_id"] is None for loc in data)

    def test_filter_by_parent(self, client, db, director_token, sample_location_tree):
        island = sample_location_tree["island"]
        resp = client.get(f"/locations/list?parent_id={island.id}",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["code"] == "SEC-005-A"


# ---------------------------------------------------------------------------
# Operational Statistics
# ---------------------------------------------------------------------------

class TestLocationStats:
    def test_stats_all(self, client, db, director_token, sample_location):
        resp = client.get("/locations/stats/all",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        stat = next((s for s in data if s["location_id"] == sample_location.id), None)
        assert stat is not None
        assert "complaint_count" in stat
        assert "task_count" in stat
        assert "is_hotspot" in stat

    def test_stats_with_data(self, client, db, director_token, sample_location, sample_area):
        # Add complaints and tasks
        for i in range(3):
            db.add(Complaint(
                tracking_number=f"CMP0002000{i}",
                full_name=f"مقدم {i}",
                phone=f"099000000{i}",
                complaint_type=ComplaintType.WATER,
                description="شكوى اختبار",
                status=ComplaintStatus.NEW,
                area_id=sample_area.id,
                location_id=sample_location.id,
            ))
        db.add(Task(
            title="مهمة إحصاء",
            description="وصف",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            location_id=sample_location.id,
        ))
        db.commit()

        resp = client.get("/locations/stats/all",
                          headers=_auth_headers(director_token))
        data = resp.json()
        stat = next(s for s in data if s["location_id"] == sample_location.id)
        assert stat["complaint_count"] == 3
        assert stat["open_complaint_count"] == 3
        assert stat["task_count"] == 1


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class TestLocationReports:
    def test_report_summary(self, client, db, director_token, sample_location):
        resp = client.get("/locations/reports/summary",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_locations" in data
        assert "by_type" in data
        assert "hotspots" in data
        assert "most_complaints" in data
        assert "most_delayed" in data
        assert "contract_coverage" in data

    def test_report_with_data(self, client, db, director_token, sample_location, sample_area, director_user):
        # Add complaints
        for i in range(6):
            db.add(Complaint(
                tracking_number=f"CMP0003000{i}",
                full_name=f"مقدم {i}",
                phone=f"099100000{i}",
                complaint_type=ComplaintType.CLEANING,
                description="شكوى تنظيف",
                status=ComplaintStatus.NEW,
                area_id=sample_area.id,
                location_id=sample_location.id,
            ))
        # Add delayed task
        db.add(Task(
            title="مهمة متأخرة",
            description="وصف",
            source_type=TaskSourceType.INTERNAL,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            location_id=sample_location.id,
            due_date=date.today() - timedelta(days=10),
        ))
        # Add contract coverage
        contract = Contract(
            contract_number="CNT-RPT-001",
            title="عقد تقرير",
            contractor_name="شركة",
            contract_type=ContractType.MAINTENANCE,
            contract_value=50000,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=180),
            status=ContractStatus.ACTIVE,
            scope_description="نطاق",
            created_by_id=director_user.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        link = ContractLocation(contract_id=contract.id, location_id=sample_location.id)
        db.add(link)
        db.commit()

        resp = client.get("/locations/reports/summary",
                          headers=_auth_headers(director_token))
        data = resp.json()
        assert data["total_locations"] >= 1
        # With 6 open complaints, this location should be a hotspot
        hotspot_ids = [h["location_id"] for h in data["hotspots"]]
        assert sample_location.id in hotspot_ids
        # Should appear in most_delayed
        delayed_ids = [d["location_id"] for d in data["most_delayed"]]
        assert sample_location.id in delayed_ids
        # Should appear in contract_coverage
        coverage_ids = [c["location_id"] for c in data["contract_coverage"]]
        assert sample_location.id in coverage_ids


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

class TestLocationRBAC:
    def test_citizen_cannot_access(self, client, db, citizen_token):
        resp = client.get("/locations/list", headers=_auth_headers(citizen_token))
        assert resp.status_code == 403

    def test_field_team_can_read(self, client, db, field_token, sample_location):
        resp = client.get("/locations/list", headers=_auth_headers(field_token))
        assert resp.status_code == 200

    def test_field_team_can_create(self, client, db, field_token):
        resp = client.post("/locations/", json={
            "name": "موقع ميداني",
            "code": "FLD-001",
            "location_type": "service_point",
        }, headers=_auth_headers(field_token))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------

class TestLocationAudit:
    def test_create_audit(self, client, db, director_token):
        resp = client.post("/locations/", json={
            "name": "موقع تدقيق",
            "code": "AUD-001",
            "location_type": "island",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200

        # Check audit log exists
        from app.models.audit import AuditLog
        logs = db.query(AuditLog).filter(AuditLog.action == "location_create").all()
        assert len(logs) >= 1

    def test_update_audit(self, client, db, director_token, sample_location):
        resp = client.put(f"/locations/{sample_location.id}", json={
            "description": "تم التحديث",
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200

        from app.models.audit import AuditLog
        logs = db.query(AuditLog).filter(AuditLog.action == "location_update").all()
        assert len(logs) >= 1


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

class TestLocationCSVExport:
    def test_csv_export(self, client, db, director_token, sample_location):
        resp = client.get("/locations/reports/export/csv",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.text
        assert "الاسم" in content  # Arabic header row
        assert sample_location.name in content

    def test_csv_export_with_type_filter(self, client, db, director_token, sample_location):
        resp = client.get("/locations/reports/export/csv?location_type=island",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        content = resp.text
        assert sample_location.name in content

    def test_csv_export_with_status_filter(self, client, db, director_token, sample_location):
        resp = client.get("/locations/reports/export/csv?status=active",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        content = resp.text
        assert sample_location.name in content

    def test_csv_export_requires_auth(self, client, db):
        resp = client.get("/locations/reports/export/csv")
        assert resp.status_code in [401, 403]


# ---------------------------------------------------------------------------
# Map Data
# ---------------------------------------------------------------------------

class TestLocationMapData:
    def test_map_data_endpoint(self, client, db, director_token, sample_location):
        resp = client.get(f"/locations/detail/{sample_location.id}/map-data",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "location" in data
        assert "complaints" in data
        assert "tasks" in data
        assert "children" in data
        assert data["location"]["id"] == sample_location.id

    def test_map_data_with_coordinates(self, client, db, director_token):
        loc = Location(
            name="موقع خريطة",
            code="MAP-001",
            location_type=LocationType.ISLAND,
            status=LocationStatus.ACTIVE,
            latitude=33.5365,
            longitude=36.2204,
            is_active=1,
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)

        resp = client.get(f"/locations/detail/{loc.id}/map-data",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["location"]["point"]["latitude"] == 33.5365
        assert data["location"]["point"]["longitude"] == 36.2204

    def test_map_data_with_linked_complaints(self, client, db, director_token):
        loc = Location(
            name="موقع شكاوى خريطة",
            code="MAP-002",
            location_type=LocationType.BUILDING,
            status=LocationStatus.ACTIVE,
            is_active=1,
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)

        complaint = Complaint(
            tracking_number="MAP-C-001",
            full_name="مواطن",
            phone="0911111111",
            complaint_type=ComplaintType.INFRASTRUCTURE,
            description="شكوى اختبار خريطة",
            location_id=loc.id,
            latitude=33.5370,
            longitude=36.2210,
            status=ComplaintStatus.NEW,
        )
        db.add(complaint)
        db.commit()

        resp = client.get(f"/locations/detail/{loc.id}/map-data",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["complaints"]) == 1
        assert data["complaints"][0]["tracking_number"] == "MAP-C-001"

    def test_map_data_not_found(self, client, db, director_token):
        resp = client.get("/locations/detail/99999/map-data",
                          headers=_auth_headers(director_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auto-location assignment
# ---------------------------------------------------------------------------

class TestAutoLocationAssignment:
    def test_complaint_auto_assign_explicit_location(self, client, db, director_token):
        """When location_id is explicitly provided, it should be used."""
        loc = Location(
            name="موقع تلقائي",
            code="AUTO-001",
            location_type=LocationType.ISLAND,
            status=LocationStatus.ACTIVE,
            is_active=1,
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)

        resp = client.post("/complaints/", json={
            "full_name": "اختبار",
            "phone": "0900000001",
            "complaint_type": "infrastructure",
            "description": "اختبار ربط تلقائي",
            "location_id": loc.id,
        })
        assert resp.status_code == 200
        data = resp.json()
        # Check that complaint was assigned to the location in DB
        c = db.query(Complaint).filter(Complaint.tracking_number == data["tracking_number"]).first()
        assert c.location_id == loc.id

    def test_task_auto_assign_explicit_location(self, client, db, director_token):
        """When location_id is explicitly provided for task, it should be used."""
        loc = Location(
            name="موقع مهمة",
            code="AUTO-002",
            location_type=LocationType.BUILDING,
            status=LocationStatus.ACTIVE,
            is_active=1,
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)

        resp = client.post("/tasks/", json={
            "title": "مهمة اختبار",
            "description": "اختبار ربط تلقائي للمهام",
            "location_id": loc.id,
        }, headers=_auth_headers(director_token))
        assert resp.status_code == 200
        t = db.query(Task).filter(Task.title == "مهمة اختبار").first()
        assert t.location_id == loc.id

    def test_complaint_no_location_no_error(self, client, db):
        """Complaint without any location data should still work."""
        resp = client.post("/complaints/", json={
            "full_name": "بدون موقع",
            "phone": "0900000002",
            "complaint_type": "cleaning",
            "description": "شكوى بدون موقع",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Migration script (unit test)
# ---------------------------------------------------------------------------

class TestMigrationScript:
    def test_migration_functions_exist(self):
        """Ensure migration module imports correctly."""
        from app.scripts.migrate_areas_to_locations import (
            area_code, building_code, street_code,
            migrate_areas, migrate_buildings, migrate_streets,
            backfill_complaints, backfill_tasks,
        )
        # Verify code generators
        class MockArea:
            code = "A1"
        class MockBuilding:
            building_number = "101"
            id = 1
        class MockStreet:
            code = "S1"
            id = 2

        assert area_code(MockArea()) == "LOC-A1"
        assert building_code(MockArea(), MockBuilding()) == "BLD-A1-101"
        assert street_code(MockStreet()) == "STR-S1"

    def test_migration_idempotent(self, db):
        """Running migration with existing codes should skip without error."""
        from app.scripts.migrate_areas_to_locations import _get_or_create_location, LocationType, LocationStatus

        # Create first time
        loc1, created1 = _get_or_create_location(db, "IDEM-001", {
            "name": "test",
            "location_type": LocationType.ISLAND,
            "status": LocationStatus.ACTIVE,
            "is_active": 1,
        })
        assert created1 is True

        # Try again — should skip
        loc2, created2 = _get_or_create_location(db, "IDEM-001", {
            "name": "test2",
            "location_type": LocationType.ISLAND,
            "status": LocationStatus.ACTIVE,
            "is_active": 1,
        })
        assert created2 is False
        assert loc1.id == loc2.id
