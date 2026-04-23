import os
import re
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.api.deps import get_current_user, get_current_internal_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

limiter = Limiter(key_func=get_remote_address)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"}
ALLOWED_CATEGORIES = {"general", "contracts", "complaints", "tasks", "profiles", "contract_intelligence"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Extensions allowed for public (anonymous) complaint attachments
_PUBLIC_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf"}

# Categories that may be served WITHOUT authentication.
PUBLIC_CATEGORIES = {"complaints", "profiles", "general", "tasks"}

# Categories that contain sensitive operational data.
SENSITIVE_CATEGORIES = {"contracts", "contract_intelligence"}

# Strict allowlist regex for stored filenames. We only ever write filenames
# of the form `<uuid4().hex><ext>` so this is sufficient and cannot match
# any path-traversal sequence.
_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}\.[A-Za-z0-9]{1,8}$")


def _safe_filepath(category: str, filename: str) -> str:
    """Resolve a stored file path while defending against path traversal.

    Defense in depth:
      1. Category must be in the static ALLOWED_CATEGORIES set.
      2. Filename must match a strict allowlist regex (no separators, no dots
         other than the single extension dot, no spaces, no unicode tricks).
      3. The realpath of the resolved file must be inside the configured
         upload root.
    """
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid file category")

    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    category_root = os.path.realpath(os.path.join(upload_root, category))
    candidate = os.path.realpath(os.path.join(category_root, filename))

    # The category directory must live inside (or be) the upload root.
    if not (category_root.startswith(upload_root + os.sep) or category_root == upload_root):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not (candidate == os.path.join(category_root, filename)
            or candidate.startswith(category_root + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return candidate


@router.post("/public")
@limiter.limit("10/minute")
async def upload_public_file(
    request: Request,
    file: UploadFile = File(...),
):
    """Public upload endpoint for complaint attachments (no auth required)."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _PUBLIC_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "complaints")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "original_name": file.filename,
        "path": f"/uploads/complaints/{filename}",
        "size": len(content),
    }


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    category: str = "general",
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

    # Only allow predefined categories to prevent path traversal
    if category not in ALLOWED_CATEGORIES:
        category = "general"

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    upload_dir = os.path.join(settings.UPLOAD_DIR, category)
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "original_name": file.filename,
        "path": f"/uploads/{category}/{filename}",
        "size": len(content),
    }


# ---------------------------------------------------------------------------
# Authenticated download for SENSITIVE categories (contracts, contract_intelligence).
# This is the canonical access path now that the unauthenticated StaticFiles
# mount has been removed from app/main.py. nginx proxies /uploads/contracts/*
# and /uploads/contract_intelligence/* to the backend so these requests reach
# this handler.
# ---------------------------------------------------------------------------
@router.get("/contracts/{filename}")
def get_contract_file(
    filename: str,
    current_user: User = Depends(get_current_internal_user),
):
    """Return a contract attachment. Requires internal staff auth."""
    return _serve_file("contracts", filename)


@router.get("/contract_intelligence/{filename}")
def get_contract_intelligence_file(
    filename: str,
    current_user: User = Depends(get_current_internal_user),
):
    """Return a contract-intelligence document. Requires internal staff auth."""
    return _serve_file("contract_intelligence", filename)


def _serve_file(category: str, filename: str) -> FileResponse:
    filepath = _safe_filepath(category, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)
