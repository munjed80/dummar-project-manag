from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timezone
from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.models.user import User, UserRole
from app.schemas.app_setting import SettingItem, SettingsBulkUpdate
from app.api.deps import require_role, get_current_internal_user
from app.services.audit import write_audit_log

router = APIRouter(prefix="/settings", tags=["settings"])

_settings_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
)


def _seed_default_settings(db: Session):
    """Seed default settings if none exist."""
    existing_count = db.query(AppSetting).count()
    if existing_count > 0:
        return
    
    defaults = [
        SettingItem(key="project.name_ar", value="مشروع دمّر", value_type="string", category="project", description="اسم المشروع بالعربية"),
        SettingItem(key="project.name_en", value="Dummar Project", value_type="string", category="project", description="Project name in English"),
        SettingItem(key="organization.name_ar", value="محافظة دمشق", value_type="string", category="organization", description="اسم الجهة"),
        SettingItem(key="organization.region", value="دمشق - منطقة دمر", value_type="string", category="organization", description="المنطقة الجغرافية"),
        SettingItem(key="defaults.task_priority", value="medium", value_type="string", category="defaults", description="أولوية المهام الافتراضية"),
        SettingItem(key="defaults.task_due_days", value="7", value_type="number", category="defaults", description="عدد الأيام الافتراضي لاستحقاق المهام"),
        SettingItem(key="defaults.complaint_auto_assign", value="false", value_type="boolean", category="defaults", description="تعيين الشكاوى تلقائياً"),
    ]
    
    for item in defaults:
        db_setting = AppSetting(
            key=item.key,
            value=item.value,
            value_type=item.value_type,
            category=item.category,
            description=item.description,
        )
        db.add(db_setting)
    
    db.commit()


@router.get("/", response_model=Dict[str, List[SettingItem]])
def get_settings(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    _seed_default_settings(db)
    
    all_settings = db.query(AppSetting).order_by(AppSetting.category, AppSetting.key).all()
    
    grouped: Dict[str, List[SettingItem]] = defaultdict(list)
    for s in all_settings:
        grouped[s.category].append(
            SettingItem(
                key=s.key,
                value=s.value,
                value_type=s.value_type,
                category=s.category,
                description=s.description,
            )
        )
    
    return dict(grouped)


@router.put("/", response_model=Dict[str, str])
def update_settings(
    bulk: SettingsBulkUpdate,
    request: Request,
    current_user: User = Depends(_settings_managers),
    db: Session = Depends(get_db)
):
    for item in bulk.items:
        existing = db.query(AppSetting).filter(AppSetting.key == item.key).first()
        if existing:
            existing.value = item.value
            existing.value_type = item.value_type
            existing.category = item.category
            existing.description = item.description
            existing.updated_by_id = current_user.id
            existing.updated_at = datetime.now(timezone.utc)
        else:
            new_setting = AppSetting(
                key=item.key,
                value=item.value,
                value_type=item.value_type,
                category=item.category,
                description=item.description,
                updated_by_id=current_user.id,
            )
            db.add(new_setting)
    
    db.commit()
    
    write_audit_log(
        db, action="settings_update", entity_type="settings",
        entity_id=0, user_id=current_user.id,
        description=f"Updated {len(bulk.items)} settings",
        request=request,
    )
    
    return {"message": "Settings updated successfully"}
