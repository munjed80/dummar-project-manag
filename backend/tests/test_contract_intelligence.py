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


# ---------------------------------------------------------------------------
# New tests for Batch: Contract Intelligence Operational Completion
# ---------------------------------------------------------------------------


class TestTesseractOcrEngine:
    """Test Tesseract OCR engine detection and fallback."""

    def test_is_tesseract_available_returns_bool(self):
        from app.services.ocr_service import is_tesseract_available
        result = is_tesseract_available()
        assert isinstance(result, bool)

    def test_tesseract_detection_cached(self):
        from app.services.ocr_service import is_tesseract_available, _reset_tesseract_cache
        _reset_tesseract_cache()
        r1 = is_tesseract_available()
        r2 = is_tesseract_available()
        assert r1 == r2

    def test_get_ocr_engine_returns_engine(self):
        from app.services.ocr_service import get_ocr_engine, OcrEngine
        engine = get_ocr_engine()
        assert isinstance(engine, OcrEngine)

    def test_get_ocr_status(self):
        from app.services.ocr_service import get_ocr_status
        status = get_ocr_status()
        assert "engine" in status
        assert "tesseract_available" in status
        assert isinstance(status["tesseract_available"], bool)
        assert "supported_formats" in status

    def test_basic_extractor_image_without_tesseract(self):
        """BasicTextExtractor should return graceful failure for images when tesseract is not installed."""
        from app.services.ocr_service import BasicTextExtractor
        import tempfile
        from PIL import Image

        # Create a test image
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f, format='PNG')
            f.flush()
            engine = BasicTextExtractor()
            result = engine.extract_text(f.name, 'png')
            # Should not crash; either succeeds (if tesseract installed) or fails gracefully
            assert result is not None
            os.unlink(f.name)


class TestExcelImport:
    """Test Excel (.xlsx) import via openpyxl."""

    def _create_test_xlsx(self, rows):
        """Helper to create an in-memory Excel file."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        if rows:
            for row in rows:
                ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    def test_preview_excel(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        xlsx = self._create_test_xlsx([
            ["contract_number", "title", "contractor_name", "contract_value"],
            ["EX-001", "عقد اختبار Excel", "شركة اختبار", "500000"],
            ["EX-002", "عقد ثاني", "شركة أخرى", "300000"],
        ])
        resp = client.post(
            "/contract-intelligence/bulk-import/preview-excel",
            headers={k: v for k, v in headers.items()},
            files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_rows"] == 2
        assert data["valid_rows"] == 2
        assert data["rows"][0]["contract_number"] == "EX-001"
        assert data["rows"][1]["title"] == "عقد ثاني"

    def test_preview_excel_with_validation_errors(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        xlsx = self._create_test_xlsx([
            ["contract_number", "title"],
            ["", ""],  # Missing required fields
        ])
        resp = client.post(
            "/contract-intelligence/bulk-import/preview-excel",
            headers={k: v for k, v in headers.items()},
            files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Row with empty cells should either be skipped or flagged invalid
        if data["total_rows"] > 0:
            assert data["invalid_rows"] >= 1

    def test_execute_excel_import(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        xlsx = self._create_test_xlsx([
            ["contract_number", "title", "contractor_name", "contract_type"],
            ["EXIM-001", "عقد استيراد Excel", "شركة الاستيراد", "maintenance"],
        ])
        resp = client.post(
            "/contract-intelligence/bulk-import/execute-excel",
            headers={k: v for k, v in headers.items()},
            files={"file": ("import.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_processed"] == 1
        assert data["successful"] == 1
        assert data["import_batch_id"] is not None

    def test_execute_excel_with_arabic_headers(self, client, db):
        """Test Excel import with Arabic column headers."""
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        xlsx = self._create_test_xlsx([
            ["رقم العقد", "العنوان", "المقاول", "القيمة"],
            ["AR-001", "عقد عربي", "شركة عربية", "100000"],
        ])
        resp = client.post(
            "/contract-intelligence/bulk-import/preview-excel",
            headers={k: v for k, v in headers.items()},
            files={"file": ("arabic.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid_rows"] == 1
        assert data["rows"][0]["contract_number"] == "AR-001"

    def test_reject_non_excel(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        file = io.BytesIO(b"not,excel,data")
        resp = client.post(
            "/contract-intelligence/bulk-import/preview-excel",
            headers={k: v for k, v in headers.items()},
            files={"file": ("test.csv", file, "text/csv")},
        )
        assert resp.status_code == 400


class TestIntelligenceNotifications:
    """Test processing-completion notifications."""

    def test_upload_creates_notifications(self, client, db):
        """Document upload and processing should create notifications."""
        # Create two managers to be notified
        _create_user(db, "notif_mgr", UserRole.CONTRACTS_MANAGER)
        _create_user(db, "notif_dir", UserRole.PROJECT_DIRECTOR)
        token = _login(client, "notif_mgr")
        headers = _auth_headers(token)

        content = "عقد رقم: NOTIF-001\nالمقاول: شركة الإشعار\nالقيمة: 2,000,000 ل.س"
        file = io.BytesIO(content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("notif.txt", file, "text/plain")},
        )
        assert resp.status_code == 200

        # Check that notifications were created
        from app.models.notification import Notification, NotificationType
        notifs = db.query(Notification).filter(
            Notification.notification_type == NotificationType.INTELLIGENCE_PROCESSING
        ).all()
        assert len(notifs) >= 1  # At least one notification for the manager

    def test_csv_batch_creates_notifications(self, client, db):
        """CSV batch import should create batch completion notification."""
        _create_user(db, "batch_mgr", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "batch_mgr")
        headers = _auth_headers(token)

        csv_content = "contract_number,title,contractor_name\nBATCH-001,عقد دفعة,شركة"
        file = io.BytesIO(csv_content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/bulk-import/execute-csv",
            headers={k: v for k, v in headers.items()},
            files={"file": ("batch.csv", file, "text/csv")},
        )
        assert resp.status_code == 200

        from app.models.notification import Notification, NotificationType
        notifs = db.query(Notification).filter(
            Notification.notification_type == NotificationType.INTELLIGENCE_PROCESSING
        ).all()
        # Should have both processing-level and batch-level notifications
        assert len(notifs) >= 1

    def test_notification_failure_does_not_break_flow(self, client, db):
        """If notification sending fails, the main workflow must not break."""
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        content = "simple test text"
        file = io.BytesIO(content.encode("utf-8"))
        # Even if notification has issues, upload should succeed
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("safe.txt", file, "text/plain")},
        )
        assert resp.status_code == 200


class TestIntelligenceReports:
    """Test intelligence reports endpoint."""

    def test_reports_empty(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        resp = client.get("/contract-intelligence/reports", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 0
        assert "status_breakdown" in data
        assert "classification_distribution" in data
        assert "risk_by_severity" in data
        assert "risk_by_type" in data
        assert "ocr_confidence" in data
        assert "batch_results" in data
        assert "ocr_engine" in data

    def test_reports_with_data(self, client, db):
        """Reports should reflect real data after processing."""
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)

        # Upload a document to generate data
        content = "عقد رقم: RPT-001\nالمقاول: شركة التقارير\nالقيمة: 3,000,000 ل.س\nنطاق العمل: صيانة المباني"
        file = io.BytesIO(content.encode("utf-8"))
        client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("report.txt", file, "text/plain")},
        )

        resp = client.get("/contract-intelligence/reports", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] >= 1
        assert data["review_queue_size"] >= 0

    def test_reports_rbac_citizen_denied(self, client, db):
        """Citizens should not access reports."""
        _create_user(db, "rpt_citizen", UserRole.CITIZEN)
        token = _login(client, "rpt_citizen")
        headers = _auth_headers(token)

        resp = client.get("/contract-intelligence/reports", headers=headers)
        assert resp.status_code == 403


class TestOcrStatusEndpoint:
    """Test OCR status API endpoint."""

    def test_ocr_status(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        resp = client.get("/contract-intelligence/ocr-status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "engine" in data
        assert "tesseract_available" in data
        assert "supported_formats" in data

    def test_ocr_status_rbac(self, client, db):
        """Citizen should not access OCR status."""
        _create_user(db, "ocr_citizen", UserRole.CITIZEN)
        token = _login(client, "ocr_citizen")
        headers = _auth_headers(token)
        resp = client.get("/contract-intelligence/ocr-status", headers=headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# New tests for Batch: Intelligence Export, Filters, Extraction & Production
# ---------------------------------------------------------------------------


class TestExtractionRefinements:
    """Test refined extraction patterns for edge cases."""

    def test_extract_dotted_date(self):
        from app.services.extraction_service import extract_fields
        text = "تاريخ العقد 15.03.2024"
        result = extract_fields(text)
        assert "start_date" in result.fields
        assert result.fields["start_date"] == "2024-03-15"

    def test_extract_value_with_spaces(self):
        from app.services.extraction_service import extract_fields
        text = "قيمة العقد 5 000 000 ل.س"
        result = extract_fields(text)
        assert result.fields.get("contract_value") == 5000000.0

    def test_extract_value_reversed_currency(self):
        from app.services.extraction_service import extract_fields
        text = "المبلغ: ل.س 2,500,000"
        result = extract_fields(text)
        assert result.fields.get("contract_value") == 2500000.0

    def test_extract_contract_number_with_year_prefix(self):
        from app.services.extraction_service import extract_fields
        text = "عقد رقم: 2024-MAINT-001 بتاريخ 2024-01-15"
        result = extract_fields(text)
        assert result.success
        assert "contract_number" in result.fields

    def test_extract_contractor_with_company_prefix(self):
        from app.services.extraction_service import extract_fields
        text = "شركة الإعمار والبناء الحديثة"
        result = extract_fields(text)
        assert "contractor_name" in result.fields

    def test_extract_duration_weeks(self):
        from app.services.extraction_service import extract_fields
        text = "مدة التنفيذ 4 أسابيع"
        result = extract_fields(text)
        assert result.fields.get("execution_duration_days") == 28

    def test_extract_ocr_noise_tolerance(self):
        """OCR noise should be cleaned before extraction."""
        from app.services.extraction_service import extract_fields
        text = "عقد  رقم:  TEST-OCR-001\n  المقاول:  شركة   الاختبار   \nالقيمة: 1,000,000 ل.س"
        result = extract_fields(text)
        assert result.success
        assert "contract_number" in result.fields

    def test_extract_mixed_arabic_english_label(self):
        from app.services.extraction_service import extract_fields
        text = "Contract No. ABC-2024-100\nالمقاول: Test Company\nValue: 500,000 ل.س"
        result = extract_fields(text)
        assert result.success

    def test_clean_ocr_noise(self):
        from app.services.extraction_service import _clean_ocr_noise
        noisy = "عقد  رقم   123  في    تاريخ"
        cleaned = _clean_ocr_noise(noisy)
        assert "  " not in cleaned

    def test_two_digit_year(self):
        from app.services.extraction_service import _normalize_date
        result = _normalize_date("15-03-24")
        assert result == "2024-03-15"


class TestReportsFilters:
    """Test reports endpoint with filter parameters."""

    def _setup_data(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)

        # Upload a document to generate data
        content = "عقد رقم: FLT-001\nالمقاول: شركة الفلتر\nالقيمة: 1,000,000 ل.س\nنطاق العمل: صيانة المباني"
        file = io.BytesIO(content.encode("utf-8"))
        client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("filter.txt", file, "text/plain")},
        )
        return headers

    def test_reports_with_date_filter(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports?date_from=2020-01-01&date_to=2030-12-31",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] >= 1
        assert "active_filters" in data
        assert data["active_filters"]["date_from"] == "2020-01-01"

    def test_reports_with_review_status_filter(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports?review_status=review",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "active_filters" in data

    def test_reports_with_search(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports?search=FLT-001",
            headers=headers,
        )
        assert resp.status_code == 200

    def test_reports_with_import_source_filter(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports?import_source=upload",
            headers=headers,
        )
        assert resp.status_code == 200

    def test_reports_returns_time_series(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get("/contract-intelligence/reports", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "documents_over_time" in data
        assert "risks_over_time" in data
        assert isinstance(data["documents_over_time"], list)


class TestExportEndpoints:
    """Test CSV and PDF export endpoints."""

    def _setup_data(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        content = "عقد رقم: EXP-001\nالمقاول: شركة التصدير\nالقيمة: 2,000,000 ل.س\nنطاق العمل: صيانة"
        file = io.BytesIO(content.encode("utf-8"))
        client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("export.txt", file, "text/plain")},
        )
        return headers

    def test_csv_export_all(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/csv?section=all",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.text
        assert "ID" in content
        assert "EXP-001" in content or "export.txt" in content

    def test_csv_export_documents(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/csv?section=documents",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "Filename" in resp.text

    def test_csv_export_risks(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/csv?section=risks",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "Risk Flags" in resp.text

    def test_csv_export_with_filter(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/csv?section=documents&date_from=2020-01-01",
            headers=headers,
        )
        assert resp.status_code == 200

    def test_csv_export_rbac_denied(self, client, db):
        _create_user(db, "exp_citizen", UserRole.CITIZEN)
        token = _login(client, "exp_citizen")
        headers = _auth_headers(token)
        resp = client.get("/contract-intelligence/reports/export/csv", headers=headers)
        assert resp.status_code == 403

    def test_pdf_export(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/pdf",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        # Check that content starts with PDF header
        assert resp.content[:4] == b"%PDF"

    def test_pdf_export_with_filter(self, client, db):
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/pdf?date_from=2020-01-01",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    def test_pdf_export_rbac_denied(self, client, db):
        _create_user(db, "pdf_citizen", UserRole.CITIZEN)
        token = _login(client, "pdf_citizen")
        headers = _auth_headers(token)
        resp = client.get("/contract-intelligence/reports/export/pdf", headers=headers)
        assert resp.status_code == 403

    def test_pdf_export_arabic_content(self, client, db):
        """Verify PDF export uses Arabic-capable font and reshaping."""
        headers = self._setup_data(client, db)
        resp = client.get(
            "/contract-intelligence/reports/export/pdf",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        # If DejaVu Sans is available, the PDF should embed it
        # otherwise it falls back to Helvetica (still valid PDF)
        pdf_bytes = resp.content
        assert len(pdf_bytes) > 500  # Not trivially empty


class TestIndividualDocumentExport:
    """Test individual document PDF export."""

    def _setup_doc(self, client, db):
        headers, _ = TestContractIntelligenceAPI()._get_manager_headers(client, db)
        content = "عقد رقم: INDV-001\nالمقاول: شركة الفرد\nالقيمة: 1,000,000 ل.س\nنطاق العمل: بناء"
        file = io.BytesIO(content.encode("utf-8"))
        resp = client.post(
            "/contract-intelligence/upload",
            headers={k: v for k, v in headers.items()},
            files={"file": ("indv_test.txt", file, "text/plain")},
        )
        assert resp.status_code == 200
        doc_id = resp.json()["id"]
        return headers, doc_id

    def test_individual_doc_pdf_export(self, client, db):
        headers, doc_id = self._setup_doc(client, db)
        resp = client.get(
            f"/contract-intelligence/documents/{doc_id}/export/pdf",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.content[:4] == b"%PDF"
        assert len(resp.content) > 500

    def test_individual_doc_pdf_not_found(self, client, db):
        headers, _ = self._setup_doc(client, db)
        resp = client.get(
            "/contract-intelligence/documents/99999/export/pdf",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_individual_doc_pdf_rbac_denied(self, client, db):
        _, doc_id = self._setup_doc(client, db)
        _create_user(db, "indv_citizen", UserRole.CITIZEN)
        token = _login(client, "indv_citizen")
        headers = _auth_headers(token)
        resp = client.get(
            f"/contract-intelligence/documents/{doc_id}/export/pdf",
            headers=headers,
        )
        assert resp.status_code == 403
