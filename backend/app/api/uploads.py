import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"}
ALLOWED_CATEGORIES = {"general", "contracts", "complaints", "tasks", "profiles"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Extensions allowed for public (anonymous) complaint attachments
_PUBLIC_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf"}


@router.post("/public")
async def upload_public_file(
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
