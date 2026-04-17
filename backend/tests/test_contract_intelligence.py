"""
Tests for the Contract Intelligence Center.

Tests cover:
- Document upload and processing pipeline
- OCR service abstraction
- Field extraction
- Classification
- Summary generation
- Risk analysis
- Duplicate detection
- Bulk import (CSV)
- Dashboard stats
- Processing queue
- Document review/approve/reject flow
- Convert to contract
- RBAC enforcement
- Audit logging
"""

import io
import json
import os
import pytest
from tests.conftest import _create_user, _login, _auth_headers
from app.models.user import UserRole
from app.models.contract import ContractType


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestExtractionService:
    """Test field extraction from text."""

    def test_extract_contract_number(self):
        from app.services.extraction_service import extract_fields
        text = "عقد رقم: ABC-2024-001 بتاريخ 2024-01-15"
        result = extract_fields(text)
        assert result.success
        assert result.fields.get("contract_number") == "ABC-2024-001"

    def test_extract_dates(self):
        from app.services.extraction_service import extract_fields
        text = "يبدأ العقد من 2024-03-01 وينتهي في 2025-02-28"
        result = extract_fields(text)
        assert "start_date" in result.fields or "end_date" in result.fields

    def test_extract_value_syp(self):
        from app.services.extraction_service import extract_fields
        text = "قيمة العقد 5,000,000 ل.س"
        result = extract_fields(text)
        assert result.fields.get("contract_value") == 5000000.0

    def test_extract_contractor(self):
        from app.services.extraction_service import extract_fields
        text = "المقاول: شركة الإعمار للمقاولات\nالتاريخ: 2024-01-01"
        result = extract_fields(text)
        assert "contractor_name" in result.fields

    def test_extract_empty_text(self):
        from app.services.extraction_service import extract_fields
        result = extract_fields("")
        assert not result.success
        assert result.confidence == 0.0

    def test_extract_duration_days(self):
        from app.services.extraction_service import extract_fields
        text = "مدة التنفيذ 180 يوم"
        result = extract_fields(text)
        assert result.fields.get("execution_duration_days") == 180

    def test_extract_duration_months(self):
        from app.services.extraction_service import extract_fields
        text = "مدة العقد 6 أشهر"
        result = extract_fields(text)
        assert result.fields.get("execution_duration_days") == 180

    def test_fields_json_roundtrip(self):
        from app.services.extraction_service import fields_to_json, fields_from_json
        fields = {"contract_number": "X-001", "contract_value": 100000}
        serialized = fields_to_json(fields)
        deserialized = fields_from_json(serialized)
        assert deserialized["contract_number"] == "X-001"
        assert deserialized["contract_value"] == 100000


class TestClassificationService:
    """Test contract classification."""

    def test_classify_maintenance(self):
        from app.services.classification_service import classify_contract
        result = classify_contract(text="عقد صيانة أبنية وترميم الطرق")
        assert result.suggested_type == "maintenance"
        assert result.confidence > 0

    def test_classify_construction(self):
        from app.services.classification_service import classify_contract
        result = classify_contract(text="إنشاء مبنى سكني جديد وتشييد")
        assert result.suggested_type == "construction"

    def test_classify_empty(self):
        from app.services.classification_service import classify_contract
        result = classify_contract()
        assert result.suggested_type == "other"
        assert result.confidence == 0.0

    def test_classify_from_fields(self):
        from app.services.classification_service import classify_contract
        result = classify_contract(extracted_fields={"contract_type": "supply"})
        assert result.suggested_type == "supply"


class TestSummaryService:
    """Test summary generation."""

    def test_generate_summary_full(self):
        from app.services.summary_service import generate_summary
        fields = {
            "title": "عقد صيانة المباني",
            "contractor_name": "شركة الإعمار",
            "contract_value": 5000000,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "scope_summary": "صيانة وترميم المباني السكنية",
        }
        summary = generate_summary(fields, contract_type="maintenance")
        assert "شركة الإعمار" in summary
        assert "صيانة" in summary

    def test_generate_summary_empty(self):
        from app.services.summary_service import generate_summary
        summary = generate_summary(None, None)
        assert "لا تتوفر" in summary


class TestRiskService:
    """Test risk analysis."""

    def test_risk_missing_fields(self):
        from app.services.risk_service import analyze_contract_risks
        flags = analyze_contract_risks(extracted_fields={})
        assert len(flags) > 0
        types = [f.risk_type for f in flags]
        assert "incomplete_extraction" in types

    def test_risk_invalid_dates(self):
        from app.services.risk_service import analyze_contract_risks
        flags = analyze_contract_risks(extracted_fields={
            "start_date": "2025-12-31",
            "end_date": "2024-01-01",
        })
        types = [f.risk_type for f in flags]
        assert "invalid_extracted_dates" in types

    def test_risk_short_text(self):
        from app.services.risk_service import analyze_contract_risks
        flags = analyze_contract_risks(ocr_text="short")
        types = [f.risk_type for f in flags]
        assert "very_short_text" in types

    def test_risk_empty_text(self):
        from app.services.risk_service import analyze_contract_risks
        flags = analyze_contract_risks(ocr_text="")
        types = [f.risk_type for f in flags]
        assert "empty_ocr_text" in types


class TestOcrService:
    """Test OCR service abstraction."""

    def test_ocr_text_file(self, tmp_path):
        from app.services.ocr_service import process_ocr
        test_file = tmp_path / "test.txt"
        test_file.write_text("عقد رقم 123\nالمقاول: شركة اختبار\n")
        result = process_ocr(str(test_file), "txt")
        assert result.success
        assert "عقد" in result.text
        assert result.confidence > 0

    def test_ocr_missing_file(self):
        from app.services.ocr_service import process_ocr
        result = process_ocr("/nonexistent/file.pdf", "pdf")
        assert not result.success
        assert result.confidence == 0.0

    def test_ocr_unsupported_type(self, tmp_path):
        from app.services.ocr_service import process_ocr
        test_file = tmp_path / "test.xyz"
        test_file.write_text("data")
        result = process_ocr(str(test_file), "xyz")
        assert not result.success

    def test_ocr_engine_swap(self):
        from app.services.ocr_service import get_ocr_engine, set_ocr_engine, BasicTextExtractor
        original = get_ocr_engine()
        new_engine = BasicTextExtractor()
        set_ocr_engine(new_engine)
        assert get_ocr_engine() is new_engine
        set_ocr_engine(original)


class TestDuplicateService:
    """Test duplicate detection."""

    def test_find_duplicates_exact_number(self, db, director_user):
        from app.services.duplicate_service import find_duplicates
        from app.models.contract import Contract, ContractStatus, ContractType
        from datetime import date

        c = Contract(
            contract_number="DUP-001",
            title="Test Contract",
            contractor_name="Test Co",
            contract_type=ContractType.MAINTENANCE,
            contract_value=100000,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            scope_description="Test scope",
            status=ContractStatus.DRAFT,
            created_by_id=director_user.id,
        )
        db.add(c)
        db.commit()

        matches = find_duplicates(
            db,
            contract_number="DUP-001",
            contractor_name="Test Co",
        )
        assert len(matches) > 0
        assert matches[0].contract_id == c.id

    def test_find_duplicates_no_match(self, db, director_user):
        from app.services.duplicate_service import find_duplicates
        matches = find_duplicates(
            db,
            contract_number="UNIQUE-999",
        )
        assert len(matches) == 0


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

class TestContractIntelligenceAPI:
    """Test contract intelligence API endpoints."""

    def _get_manager_headers(self, client, db):
        user = _create_user(db, "ci_manager", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "ci_manager")
        return _auth_headers(token), user

    def _get_director_headers(self, client, db):
        user = _create_user(db, "ci_director", UserRole.PROJECT_DIRECTOR)
        token = _login(client, "ci_director")
        return _auth_headers(token), user

    def test_dashboard_empty(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        resp = client.get("/contract-intelligence/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 0
        assert data["total_risk_flags"] == 0

    def test_queue_empty(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        resp = client.get("/contract-intelligence/queue", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["queue_length"] == 0

    def test_upload_text_document(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        content = "عقد رقم: TEST-001\nالمقاول: شركة الاختبار\nالقيمة: 1,000,000 ل.س\nتاريخ البدء: 2024-01-01\nتاريخ الانتهاء: 2024-12-31\nنطاق العمل: صيانة المباني السكنية في منطقة دمر"
        file = io.BytesIO(content.encode("utf-8"))

        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("contract.txt", file, "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["original_filename"] == "contract.txt"
        assert data["processing_status"] in ["review", "extracted", "ocr_complete"]
        assert data["ocr_text"] is not None or data["extracted_fields"] is not None

    def test_upload_invalid_type(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        file = io.BytesIO(b"data")
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("test.exe", file, "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_document_review_flow(self, client, db):
        """Test upload → review → approve flow."""
        headers, _ = self._get_manager_headers(client, db)

        # Upload
        content = "عقد رقم: FLOW-001\nالمقاول: شركة\n"
        file = io.BytesIO(content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("flow.txt", file, "text/plain")},
        )
        assert resp.status_code == 200
        doc_id = resp.json()["id"]

        # Get document
        resp = client.get(f"/contract-intelligence/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200

        # Approve
        resp = client.post(f"/contract-intelligence/documents/{doc_id}/approve", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["processing_status"] == "approved"

    def test_document_reject(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        content = "test text"
        file = io.BytesIO(content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("test.txt", file, "text/plain")},
        )
        doc_id = resp.json()["id"]

        resp = client.post(f"/contract-intelligence/documents/{doc_id}/reject", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["processing_status"] == "rejected"

    def test_convert_to_contract(self, client, db):
        """Test converting a document to a real contract."""
        headers, _ = self._get_manager_headers(client, db)

        content = "عقد رقم: CONV-001\nالمقاول: شركة التحويل\nالقيمة: 500,000 ل.س\nتاريخ البدء: 2024-01-01\nتاريخ الانتهاء: 2025-01-01\nنطاق العمل: أعمال صيانة المباني"
        file = io.BytesIO(content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("conv.txt", file, "text/plain")},
        )
        doc_id = resp.json()["id"]

        # Convert to contract
        resp = client.post(f"/contract-intelligence/documents/{doc_id}/convert-to-contract", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "contract_id" in data
        assert data["contract_id"] > 0

        # Verify contract exists
        resp = client.get(f"/contracts/{data['contract_id']}", headers=headers)
        assert resp.status_code == 200

    def test_csv_preview(self, client, db):
        """Test CSV bulk import preview."""
        headers, _ = self._get_manager_headers(client, db)
        csv_content = "contract_number,title,contractor_name,contract_type,contract_value,start_date,end_date\nCSV-001,Test Contract,Test Co,maintenance,100000,2024-01-01,2024-12-31\nCSV-002,Second Contract,Second Co,construction,200000,2024-06-01,2025-05-31"
        file = io.BytesIO(csv_content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/bulk-import/preview-csv",
            headers={k: v for k, v in headers.items()},
            files={"file": ("import.csv", file, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 2
        assert data["valid_rows"] == 2

    def test_csv_execute(self, client, db):
        """Test CSV bulk import execution."""
        headers, _ = self._get_manager_headers(client, db)
        csv_content = "contract_number,title,contractor_name,contract_type,contract_value\nEXEC-001,Test,TestCo,maintenance,100000"
        file = io.BytesIO(csv_content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/bulk-import/execute-csv",
            headers={k: v for k, v in headers.items()},
            files={"file": ("exec.csv", file, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_processed"] == 1
        assert data["import_batch_id"] is not None

    def test_risk_flags_api(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        resp = client.get("/contract-intelligence/risks", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_duplicates_api(self, client, db):
        headers, _ = self._get_manager_headers(client, db)
        resp = client.get("/contract-intelligence/duplicates", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_dashboard_with_data(self, client, db):
        """Dashboard reflects uploaded documents."""
        headers, _ = self._get_manager_headers(client, db)

        # Upload a document
        content = "عقد رقم: DASH-001\nصيانة"
        file = io.BytesIO(content.encode("utf-8"))
        client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("dash.txt", file, "text/plain")},
        )

        # Check dashboard
        resp = client.get("/contract-intelligence/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] >= 1

    def test_analyze_existing_contract_risks(self, client, db):
        """Test risk analysis on an existing contract."""
        headers, user = self._get_manager_headers(client, db)

        # Create a contract with missing data
        contract_data = {
            "contract_number": "RISK-001",
            "title": "Test",
            "contractor_name": "Test",
            "contract_type": "maintenance",
            "contract_value": 1000,
            "start_date": "2024-01-01",
            "end_date": "2023-12-31",  # End before start!
            "scope_description": "x",  # Too short
        }
        resp = client.post("/contracts/", json=contract_data, headers=headers)
        assert resp.status_code == 200
        contract_id = resp.json()["id"]

        # Run risk analysis
        resp = client.post(
            f"/contract-intelligence/contracts/{contract_id}/analyze-risks",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["flags_count"] > 0

    def test_contract_intelligence_view(self, client, db):
        """Test getting intelligence data for an existing contract."""
        headers, _ = self._get_manager_headers(client, db)

        contract_data = {
            "contract_number": "INTEL-001",
            "title": "Intelligence Test",
            "contractor_name": "Test Co",
            "contract_type": "maintenance",
            "contract_value": 50000,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "scope_description": "Testing intelligence integration",
        }
        resp = client.post("/contracts/", json=contract_data, headers=headers)
        contract_id = resp.json()["id"]

        resp = client.get(
            f"/contract-intelligence/contracts/{contract_id}/intelligence",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_id"] == contract_id
        assert "documents" in data
        assert "risk_flags" in data
        assert "duplicates" in data


class TestContractIntelligenceRBAC:
    """Test RBAC enforcement for contract intelligence."""

    def test_citizen_denied(self, client, db):
        """Citizens cannot access contract intelligence."""
        user = _create_user(db, "ci_citizen", UserRole.CITIZEN)
        token = _login(client, "ci_citizen")
        headers = _auth_headers(token)

        resp = client.get("/contract-intelligence/dashboard", headers=headers)
        assert resp.status_code == 403

    def test_field_team_denied(self, client, db):
        """Field team cannot access contract intelligence management."""
        user = _create_user(db, "ci_field", UserRole.FIELD_TEAM)
        token = _login(client, "ci_field")
        headers = _auth_headers(token)

        resp = client.get("/contract-intelligence/dashboard", headers=headers)
        assert resp.status_code == 403

    def test_internal_user_can_view_intelligence(self, client, db):
        """Internal users can view contract intelligence data."""
        user = _create_user(db, "ci_internal", UserRole.ENGINEER_SUPERVISOR)
        token = _login(client, "ci_internal")
        headers = _auth_headers(token)

        # Create a contract first (needs manager)
        manager = _create_user(db, "ci_mgr2", UserRole.CONTRACTS_MANAGER)
        mgr_token = _login(client, "ci_mgr2")
        mgr_headers = _auth_headers(mgr_token)

        contract_data = {
            "contract_number": "VIEW-001",
            "title": "View Test",
            "contractor_name": "Test",
            "contract_type": "maintenance",
            "contract_value": 10000,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "scope_description": "Test scope for viewing",
        }
        resp = client.post("/contracts/", json=contract_data, headers=mgr_headers)
        contract_id = resp.json()["id"]

        # Internal user can view intelligence
        resp = client.get(
            f"/contract-intelligence/contracts/{contract_id}/intelligence",
            headers=headers,
        )
        assert resp.status_code == 200
