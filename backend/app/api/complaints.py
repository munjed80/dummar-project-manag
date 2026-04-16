from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import random
import string
from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintActivity, ComplaintStatus
from app.models.user import User, UserRole
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
    ComplaintTrackRequest,
    ComplaintActivityResponse,
)
from app.api.deps import get_current_user, require_role
from app.services.audit import write_audit_log
from app.schemas.file_utils import serialize_file_list

router = APIRouter(prefix="/complaints", tags=["complaints"])

# Roles allowed to manage complaints
_complaint_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.COMPLAINTS_OFFICER,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.AREA_SUPERVISOR,
)


def generate_tracking_number(db: Session) -> str:
    while True:
        tracking_number = "CMP" + "".join(random.choices(string.digits, k=8))
        existing = db.query(Complaint).filter(Complaint.tracking_number == tracking_number).first()
        if not existing:
            return tracking_number


@router.post("/", response_model=ComplaintResponse)
def create_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    tracking_number = generate_tracking_number(db)
    
    db_complaint = Complaint(
        tracking_number=tracking_number,
        full_name=complaint.full_name,
        phone=complaint.phone,
        complaint_type=complaint.complaint_type,
        description=complaint.description,
        location_text=complaint.location_text,
        area_id=complaint.area_id,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        images=serialize_file_list(complaint.images),
        status=ComplaintStatus.NEW,
    )
    
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    
    activity = ComplaintActivity(
        complaint_id=db_complaint.id,
        action="created",
        description="Complaint submitted by citizen",
    )
    db.add(activity)
    db.commit()
    
    return db_complaint


@router.post("/track", response_model=ComplaintResponse)
def track_complaint(track_data: ComplaintTrackRequest, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(
        Complaint.tracking_number == track_data.tracking_number,
        Complaint.phone == track_data.phone
    ).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found or phone number does not match",
        )
    
    return complaint


@router.get("/", response_model=List[ComplaintResponse])
def list_complaints(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[ComplaintStatus] = None,
    area_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Complaint)
    
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    
    if area_id:
        query = query.filter(Complaint.area_id == area_id)
    
    complaints = query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return complaints


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.put("/{complaint_id}", response_model=ComplaintResponse)
def update_complaint(
    complaint_id: int,
    complaint_update: ComplaintUpdate,
    current_user: User = Depends(_complaint_managers),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    old_status = complaint.status
    
    update_data = complaint_update.model_dump(exclude_unset=True)

    # Serialize file list fields to JSON for DB storage
    if "images" in update_data and update_data["images"] is not None:
        update_data["images"] = serialize_file_list(update_data["images"])

    for field, value in update_data.items():
        setattr(complaint, field, value)
    
    if complaint_update.status == ComplaintStatus.RESOLVED:
        complaint.resolved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(complaint)
    
    if complaint_update.status and old_status != complaint_update.status:
        activity = ComplaintActivity(
            complaint_id=complaint.id,
            user_id=current_user.id,
            action="status_changed",
            description=f"Status changed from {old_status.value} to {complaint_update.status.value}",
            old_value=old_status.value,
            new_value=complaint_update.status.value,
        )
        db.add(activity)
        db.commit()
    
    write_audit_log(db, action="complaint_update", entity_type="complaint", entity_id=complaint.id, user_id=current_user.id, description=f"Complaint {complaint.tracking_number} updated")
    
    return complaint


@router.get("/{complaint_id}/activities", response_model=List[ComplaintActivityResponse])
def get_complaint_activities(
    complaint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activities = db.query(ComplaintActivity).filter(
        ComplaintActivity.complaint_id == complaint_id
    ).order_by(ComplaintActivity.created_at.desc()).all()
    
    return activities
