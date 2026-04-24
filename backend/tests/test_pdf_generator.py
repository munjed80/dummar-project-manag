"""Tests for the contract PDF generator service."""

import os
from datetime import date
from types import SimpleNamespace

from app.core.config import settings
from app.services import pdf_generator
from app.services.pdf_generator import generate_contract_pdf


def _make_contract(contract_number="CN-2024-001"):
    return SimpleNamespace(
        contract_number=contract_number,
        title="Test Contract",
        contractor_name="ACME Co.",
        contractor_contact=None,
        contract_type="CONSTRUCTION",
        contract_value=12345.67,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        execution_duration_days=365,
        status="ACTIVE",
        related_areas=None,
        scope_description="Build something nice. " * 50,
    )


def _disk_path(returned_path: str) -> str:
    # generate_contract_pdf returns a public URL like /uploads/contracts/pdf/<file>
    assert returned_path.startswith("/uploads/")
    return os.path.join(settings.UPLOAD_DIR, returned_path[len("/uploads/"):])


def test_generate_contract_pdf_creates_valid_pdf():
    path = generate_contract_pdf(_make_contract())
    full = _disk_path(path)
    assert os.path.exists(full)
    assert os.path.getsize(full) > 0
    with open(full, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_generate_contract_pdf_sanitizes_unsafe_filename(tmp_path, monkeypatch):
    # Use an isolated upload dir so we can assert containment
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    # Filename contains path separators, backslashes and a parent-dir traversal
    contract = _make_contract(contract_number="../../etc/passwd\\evil/01..")
    path = generate_contract_pdf(contract)

    pdf_dir = tmp_path / "contracts" / "pdf"
    full = _disk_path(path)
    # Resulting file must live inside the intended pdf directory
    assert os.path.commonpath([os.path.realpath(full), os.path.realpath(str(pdf_dir))]) == os.path.realpath(str(pdf_dir))
    assert os.path.exists(full)
    # No path traversal characters should remain in the filename
    name = os.path.basename(full)
    for bad in ("/", "\\", ".."):
        assert bad not in name
    assert name.startswith("contract_") and name.endswith(".pdf")


def test_pdf_generator_module_imports_without_syntax_error():
    # Re-import to ensure the module is syntactically valid on the runtime Python.
    import importlib

    importlib.reload(pdf_generator)
    assert hasattr(pdf_generator, "generate_contract_pdf")
