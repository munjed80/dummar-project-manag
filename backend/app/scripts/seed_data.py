import sys
import os
import logging
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal

import json

from app.core.database import SessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.models.location import Area, Building
from app.models.complaint import Complaint, ComplaintType, ComplaintStatus, ComplaintPriority
from app.models.task import Task, TaskStatus, TaskSourceType, TaskPriority
from app.models.contract import Contract, ContractType, ContractStatus

logger = logging.getLogger(__name__)

# Default insecure passwords used in seed data
_SEED_DEFAULT_PASSWORD = "password123"


def seed_users(db: Session):
    print("Seeding users...")
    users_data = [
        {"username": "director", "password": "password123", "full_name": "م. أحمد الخطيب", "role": UserRole.PROJECT_DIRECTOR, "email": "director@dummar.gov.sy", "phone": "+963112345001"},
        {"username": "contracts_mgr", "password": "password123", "full_name": "م. سامر القاسم", "role": UserRole.CONTRACTS_MANAGER, "email": "contracts@dummar.gov.sy", "phone": "+963112345002"},
        {"username": "engineer", "password": "password123", "full_name": "م. ليلى حسن", "role": UserRole.ENGINEER_SUPERVISOR, "email": "engineer@dummar.gov.sy", "phone": "+963112345003"},
        {"username": "complaints_off", "password": "password123", "full_name": "عمر المصري", "role": UserRole.COMPLAINTS_OFFICER, "email": "complaints@dummar.gov.sy", "phone": "+963112345004"},
        {"username": "area_sup", "password": "password123", "full_name": "خالد الأحمد", "role": UserRole.AREA_SUPERVISOR, "email": "area@dummar.gov.sy", "phone": "+963112345005"},
        {"username": "field_user", "password": "password123", "full_name": "يوسف العلي", "role": UserRole.FIELD_TEAM, "email": "field@dummar.gov.sy", "phone": "+963112345006"},
        {"username": "contractor", "password": "password123", "full_name": "شركة البناء الحديث", "role": UserRole.CONTRACTOR_USER, "email": "contractor@dummar.gov.sy", "phone": "+963112345007"},
        {"username": "citizen1", "password": "password123", "full_name": "مواطن — سمير الحسن", "role": UserRole.CITIZEN, "email": "citizen1@dummar.gov.sy", "phone": "+963911234567"},
    ]
    
    for user_data in users_data:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing:
            password = user_data.pop("password")
            user = User(
                **user_data,
                hashed_password=get_password_hash(password),
                is_active=1
            )
            db.add(user)
    
    db.commit()
    print(f"✓ Created {len(users_data)} users")
    print("⚠️  WARNING: All seed accounts use the default insecure password.")
    print("⚠️  Change all passwords before deploying to production!")


def check_default_passwords(db: Session):
    """Check if any accounts still use the insecure seed password."""
    users = db.query(User).all()
    insecure = [u.username for u in users if verify_password(_SEED_DEFAULT_PASSWORD, u.hashed_password)]
    if insecure:
        msg = (
            f"⚠️  SECURITY WARNING: {len(insecure)} account(s) still use the insecure "
            f"default seed password: {', '.join(insecure)}. "
            "Change these passwords before deploying to production!"
        )
        print(msg)
        logger.warning(msg)
    return insecure


def seed_areas(db: Session):
    print("Seeding areas (Dummar project zones)...")

    # Boundary polygons for map display (list of [lat, lng] pairs)
    _BOUNDARIES = {
        "ISL-1": {
            "boundary": [[33.5380, 36.2185], [33.5380, 36.2210], [33.5365, 36.2210], [33.5365, 36.2185]],
            "color": "#3B82F6",
        },
        "ISL-2": {
            "boundary": [[33.5365, 36.2185], [33.5365, 36.2210], [33.5350, 36.2210], [33.5350, 36.2185]],
            "color": "#8B5CF6",
        },
        "SEC-N": {
            "boundary": [[33.5390, 36.2165], [33.5390, 36.2195], [33.5375, 36.2195], [33.5375, 36.2165]],
            "color": "#10B981",
        },
        "SEC-S": {
            "boundary": [[33.5350, 36.2215], [33.5350, 36.2240], [33.5335, 36.2240], [33.5335, 36.2215]],
            "color": "#F59E0B",
        },
        "CCZ": {
            "boundary": [[33.5360, 36.2180], [33.5360, 36.2200], [33.5350, 36.2200], [33.5350, 36.2180]],
            "color": "#EF4444",
        },
        "SRV": {
            "boundary": [[33.5345, 36.2205], [33.5345, 36.2225], [33.5335, 36.2225], [33.5335, 36.2205]],
            "color": "#06B6D4",
        },
        "GRN": {
            "boundary": [[33.5395, 36.2195], [33.5395, 36.2220], [33.5385, 36.2220], [33.5385, 36.2195]],
            "color": "#22C55E",
        },
        "ADM": {
            "boundary": [[33.5340, 36.2170], [33.5340, 36.2190], [33.5330, 36.2190], [33.5330, 36.2170]],
            "color": "#6366F1",
        },
    }

    areas_data = [
        {"name": "Island 1", "name_ar": "الجزيرة 1", "code": "ISL-1", "description": "الجزيرة السكنية الأولى - بلوكات سكنية متعددة الطوابق"},
        {"name": "Island 2", "name_ar": "الجزيرة 2", "code": "ISL-2", "description": "الجزيرة السكنية الثانية - وحدات سكنية عائلية"},
        {"name": "North Sector", "name_ar": "القطاع الشمالي", "code": "SEC-N", "description": "القطاع الشمالي - أبراج سكنية حديثة ومرافق مجتمعية"},
        {"name": "South Sector", "name_ar": "القطاع الجنوبي", "code": "SEC-S", "description": "القطاع الجنوبي - مباني سكنية ومساحات مفتوحة"},
        {"name": "Central Commercial Zone", "name_ar": "المنطقة التجارية المركزية", "code": "CCZ", "description": "المنطقة التجارية المركزية - مجمعات تجارية ومكاتب"},
        {"name": "Services Zone", "name_ar": "المنطقة الخدمية", "code": "SRV", "description": "المنطقة الخدمية - مدارس ومراكز صحية ومرافق عامة"},
        {"name": "Green Belt", "name_ar": "الحزام الأخضر", "code": "GRN", "description": "الحزام الأخضر - حدائق ومتنزهات ومسارات مشاة"},
        {"name": "Administrative Zone", "name_ar": "المنطقة الإدارية", "code": "ADM", "description": "المنطقة الإدارية - مقر إدارة المشروع والمباني الحكومية"},
    ]
    
    for area_data in areas_data:
        code = area_data["code"]
        boundary_info = _BOUNDARIES.get(code, {})
        existing = db.query(Area).filter(Area.code == code).first()
        if not existing:
            area = Area(
                **area_data,
                boundary_polygon=json.dumps(boundary_info.get("boundary")) if boundary_info.get("boundary") else None,
                color=boundary_info.get("color"),
            )
            db.add(area)
        elif not existing.boundary_polygon and boundary_info.get("boundary"):
            # Backfill boundary data on existing areas
            existing.boundary_polygon = json.dumps(boundary_info["boundary"])
            existing.color = boundary_info.get("color")
    
    db.commit()
    print(f"✓ Created/updated {len(areas_data)} areas with boundary data")


def seed_buildings(db: Session):
    print("Seeding buildings...")
    areas = db.query(Area).all()
    if not areas:
        print("⚠ No areas found, skipping buildings")
        return
    
    buildings_data = [
        # Island 1 - residential blocks
        {"area_id": areas[0].id, "name": "Block A1", "name_ar": "البلوك A1", "building_number": "ISL1-A1", "floors": 14},
        {"area_id": areas[0].id, "name": "Block A2", "name_ar": "البلوك A2", "building_number": "ISL1-A2", "floors": 14},
        {"area_id": areas[0].id, "name": "Block B1", "name_ar": "البلوك B1", "building_number": "ISL1-B1", "floors": 12},
        # Island 2 - residential blocks
        {"area_id": areas[1].id, "name": "Block C1", "name_ar": "البلوك C1", "building_number": "ISL2-C1", "floors": 10},
        {"area_id": areas[1].id, "name": "Block C2", "name_ar": "البلوك C2", "building_number": "ISL2-C2", "floors": 10},
        # North Sector - towers
        {"area_id": areas[2].id, "name": "North Tower 1", "name_ar": "البرج الشمالي 1", "building_number": "SECN-T1", "floors": 18},
        {"area_id": areas[2].id, "name": "North Residential Complex", "name_ar": "المجمع السكني الشمالي", "building_number": "SECN-R1", "floors": 8},
        # South Sector - tower
        {"area_id": areas[3].id, "name": "South Tower 1", "name_ar": "البرج الجنوبي 1", "building_number": "SECS-T1", "floors": 16},
        # Central Commercial Zone
        {"area_id": areas[4].id, "name": "Main Commercial Complex", "name_ar": "المجمع التجاري الرئيسي", "building_number": "CCZ-MC1", "floors": 6},
        # Services Zone
        {"area_id": areas[5].id, "name": "Central Services Building", "name_ar": "مبنى الخدمات المركزي", "building_number": "SRV-CS1", "floors": 4},
        {"area_id": areas[5].id, "name": "Primary School", "name_ar": "المدرسة الابتدائية", "building_number": "SRV-SCH1", "floors": 3},
        # Administrative Zone
        {"area_id": areas[7].id, "name": "Administrative HQ", "name_ar": "المقر الإداري", "building_number": "ADM-HQ1", "floors": 5},
    ]
    
    for building_data in buildings_data:
        building = Building(**building_data)
        db.add(building)
    
    db.commit()
    print(f"✓ Created {len(buildings_data)} buildings")


def seed_complaints(db: Session):
    print("Seeding complaints...")
    areas = db.query(Area).all()
    users = db.query(User).filter(User.role == UserRole.COMPLAINTS_OFFICER).all()
    
    complaints_data = [
        {
            "tracking_number": "CMP00000001",
            "full_name": "أحمد حسن الدمشقي",
            "phone": "+963911234567",
            "complaint_type": ComplaintType.ROADS,
            "description": "حفرة كبيرة في الشارع الرئيسي بالقرب من البلوك A1 تسبب مشاكل مرورية وخطر على السيارات",
            "location_text": "الشارع الرئيسي، بالقرب من البلوك A1، الجزيرة 1",
            "area_id": areas[0].id if areas else None,
            "status": ComplaintStatus.NEW,
            "priority": ComplaintPriority.HIGH,
            "latitude": 33.5372,
            "longitude": 36.2198,
        },
        {
            "tracking_number": "CMP00000002",
            "full_name": "فاطمة المنصور",
            "phone": "+963912345678",
            "complaint_type": ComplaintType.LIGHTING,
            "description": "إنارة الشوارع لا تعمل في المساء في المنطقة الخدمية مما يسبب صعوبة في التنقل",
            "location_text": "شارع الخدمات، المنطقة الخدمية",
            "area_id": areas[5].id if len(areas) > 5 else None,
            "status": ComplaintStatus.UNDER_REVIEW,
            "priority": ComplaintPriority.MEDIUM,
            "assigned_to_id": users[0].id if users else None,
            "latitude": 33.5340,
            "longitude": 36.2215,
        },
        {
            "tracking_number": "CMP00000003",
            "full_name": "محمد خليل",
            "phone": "+963913456789",
            "complaint_type": ComplaintType.CLEANING,
            "description": "تأخر جمع النفايات لعدة أيام في القطاع الشمالي مما يسبب روائح كريهة",
            "location_text": "البرج الشمالي 1، القطاع الشمالي",
            "area_id": areas[2].id if len(areas) > 2 else None,
            "status": ComplaintStatus.ASSIGNED,
            "priority": ComplaintPriority.URGENT,
            "assigned_to_id": users[0].id if users else None,
            "latitude": 33.5385,
            "longitude": 36.2180,
        },
        {
            "tracking_number": "CMP00000004",
            "full_name": "ليلى إبراهيم",
            "phone": "+963914567890",
            "complaint_type": ComplaintType.WATER,
            "description": "ضغط المياه ضعيف جداً في الطوابق العليا من البلوك A2 في الجزيرة 1",
            "location_text": "البلوك A2، الطابق 10، الجزيرة 1",
            "area_id": areas[0].id if areas else None,
            "status": ComplaintStatus.IN_PROGRESS,
            "priority": ComplaintPriority.HIGH,
            "latitude": 33.5368,
            "longitude": 36.2205,
        },
        {
            "tracking_number": "CMP00000005",
            "full_name": "يوسف عدنان",
            "phone": "+963915678901",
            "complaint_type": ComplaintType.INFRASTRUCTURE,
            "description": "تشققات في الرصيف أمام المجمع التجاري الرئيسي تشكل خطراً على المشاة",
            "location_text": "أمام المجمع التجاري الرئيسي، المنطقة التجارية المركزية",
            "area_id": areas[4].id if len(areas) > 4 else None,
            "status": ComplaintStatus.RESOLVED,
            "priority": ComplaintPriority.MEDIUM,
            "resolved_at": datetime.utcnow() - timedelta(days=2),
            "latitude": 33.5355,
            "longitude": 36.2190,
        },
        {
            "tracking_number": "CMP00000006",
            "full_name": "سارة الحلبي",
            "phone": "+963916789012",
            "complaint_type": ComplaintType.ELECTRICITY,
            "description": "انقطاع متكرر في التيار الكهربائي في البرج الجنوبي 1 بالقطاع الجنوبي",
            "location_text": "البرج الجنوبي 1، القطاع الجنوبي",
            "area_id": areas[3].id if len(areas) > 3 else None,
            "status": ComplaintStatus.NEW,
            "priority": ComplaintPriority.HIGH,
            "latitude": 33.5348,
            "longitude": 36.2225,
        },
        {
            "tracking_number": "CMP00000007",
            "full_name": "عبد الرحمن الشامي",
            "phone": "+963917890123",
            "complaint_type": ComplaintType.WATER,
            "description": "تسرب مياه من الأنابيب الرئيسية في مسار الحزام الأخضر",
            "location_text": "المسار الرئيسي، الحزام الأخضر",
            "area_id": areas[6].id if len(areas) > 6 else None,
            "status": ComplaintStatus.UNDER_REVIEW,
            "priority": ComplaintPriority.URGENT,
            "latitude": 33.5395,
            "longitude": 36.2170,
        },
    ]
    
    for complaint_data in complaints_data:
        existing = db.query(Complaint).filter(Complaint.tracking_number == complaint_data["tracking_number"]).first()
        if not existing:
            complaint = Complaint(**complaint_data)
            db.add(complaint)
    
    db.commit()
    print(f"✓ Created {len(complaints_data)} complaints")


def seed_tasks(db: Session):
    print("Seeding tasks...")
    areas = db.query(Area).all()
    users = db.query(User).filter(User.role == UserRole.FIELD_TEAM).all()
    complaints = db.query(Complaint).all()
    
    tasks_data = [
        {
            "title": "إصلاح الحفرة في الشارع الرئيسي",
            "description": "ردم وإصلاح الحفرة الكبيرة المبلغ عنها من المواطن بالقرب من البلوك A1 في الجزيرة 1",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[0].id if complaints else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[0].id if areas else None,
            "status": TaskStatus.ASSIGNED,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=3),
            "latitude": 33.5374,
            "longitude": 36.2196,
        },
        {
            "title": "استبدال مصابيح الإنارة",
            "description": "استبدال مصابيح الإنارة المعطلة في شارع الخدمات بالمنطقة الخدمية",
            "source_type": TaskSourceType.INTERNAL,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[5].id if len(areas) > 5 else None,
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.MEDIUM,
            "due_date": date.today() + timedelta(days=5),
            "latitude": 33.5342,
            "longitude": 36.2218,
        },
        {
            "title": "تنسيق جمع النفايات",
            "description": "ترتيب جمع فوري للنفايات في القطاع الشمالي بالقرب من البرج الشمالي 1",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[2].id if len(complaints) > 2 else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[2].id if len(areas) > 2 else None,
            "status": TaskStatus.COMPLETED,
            "priority": TaskPriority.URGENT,
            "due_date": date.today() - timedelta(days=1),
            "completed_at": datetime.utcnow() - timedelta(hours=12),
            "latitude": 33.5388,
            "longitude": 36.2178,
        },
        {
            "title": "فحص منظومة ضخ المياه",
            "description": "فحص نظام ضغط المياه في البلوك A2 بالجزيرة 1",
            "source_type": TaskSourceType.INTERNAL,
            "area_id": areas[0].id if areas else None,
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=2),
            "latitude": 33.5370,
            "longitude": 36.2203,
        },
        {
            "title": "صيانة الشبكة الكهربائية",
            "description": "فحص وصيانة الشبكة الكهربائية في البرج الجنوبي 1 بالقطاع الجنوبي",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[5].id if len(complaints) > 5 else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[3].id if len(areas) > 3 else None,
            "status": TaskStatus.ASSIGNED,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=4),
            "latitude": 33.5346,
            "longitude": 36.2228,
        },
    ]
    
    for task_data in tasks_data:
        task = Task(**task_data)
        db.add(task)
    
    db.commit()
    print(f"✓ Created {len(tasks_data)} tasks")


def seed_contracts(db: Session):
    print("Seeding contracts...")
    users = db.query(User).filter(User.role.in_([UserRole.PROJECT_DIRECTOR, UserRole.CONTRACTS_MANAGER])).all()
    if not users:
        print("⚠ No users found for contracts")
        return
    
    contracts_data = [
        {
            "contract_number": "CNT-2024-001",
            "title": "تطوير البنية التحتية للطرق - المرحلة الأولى",
            "contractor_name": "شركة دمشق للإنشاءات",
            "contractor_contact": "+963211234567",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("5000000.00"),
            "start_date": date(2024, 1, 15),
            "end_date": date(2024, 12, 31),
            "execution_duration_days": 350,
            "status": ContractStatus.ACTIVE,
            "scope_description": "إنشاء وتعبيد الطرق الرئيسية الرابطة بين جميع مناطق مشروع دمّر",
            "related_areas": "الجزيرة 1، الجزيرة 2، القطاع الشمالي",
            "created_by_id": users[0].id,
            "approved_by_id": users[0].id,
            "approved_at": datetime.utcnow() - timedelta(days=30),
        },
        {
            "contract_number": "CNT-2024-002",
            "title": "صيانة الأنظمة الكهربائية",
            "contractor_name": "الشركة السورية للخدمات الكهربائية",
            "contractor_contact": "+963212345678",
            "contract_type": ContractType.MAINTENANCE,
            "contract_value": Decimal("850000.00"),
            "start_date": date(2024, 3, 1),
            "end_date": date(2025, 2, 28),
            "execution_duration_days": 365,
            "status": ContractStatus.ACTIVE,
            "scope_description": "الصيانة المستمرة لإنارة الشوارع والبنية التحتية الكهربائية في جميع المناطق",
            "related_areas": "جميع المناطق",
            "created_by_id": users[0].id,
            "approved_by_id": users[0].id,
            "approved_at": datetime.utcnow() - timedelta(days=20),
        },
        {
            "contract_number": "CNT-2024-003",
            "title": "تنسيق المساحات الخضراء والحدائق",
            "contractor_name": "شركة دمشق الخضراء",
            "contractor_contact": "+963213456789",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("1200000.00"),
            "start_date": date(2024, 4, 1),
            "end_date": date(2024, 10, 31),
            "execution_duration_days": 213,
            "status": ContractStatus.APPROVED,
            "scope_description": "تطوير الحدائق والمساحات الخضراء في الحزام الأخضر",
            "related_areas": "الحزام الأخضر",
            "created_by_id": users[0].id,
            "approved_by_id": users[0].id,
            "approved_at": datetime.utcnow() - timedelta(days=5),
        },
        {
            "contract_number": "CNT-2024-004",
            "title": "تحديث شبكة المياه",
            "contractor_name": "شركة أكوا سيستمز سوريا",
            "contractor_contact": "+963214567890",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("3500000.00"),
            "start_date": date(2024, 6, 1),
            "end_date": date(2025, 5, 31),
            "execution_duration_days": 365,
            "status": ContractStatus.UNDER_REVIEW,
            "scope_description": "تحديث وتوسيع شبكة توزيع المياه في جميع المناطق",
            "related_areas": "جميع المناطق",
            "created_by_id": users[0].id,
        },
        {
            "contract_number": "CNT-2024-005",
            "title": "إنشاء المرافق التعليمية",
            "contractor_name": "مجموعة البناؤون الوطنيون",
            "contractor_contact": "+963215678901",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("8000000.00"),
            "start_date": date(2024, 7, 1),
            "end_date": date(2025, 12, 31),
            "execution_duration_days": 548,
            "status": ContractStatus.DRAFT,
            "scope_description": "إنشاء مدارس ومرافق تعليمية في المنطقة الخدمية",
            "related_areas": "المنطقة الخدمية",
            "created_by_id": users[0].id,
        },
    ]
    
    for contract_data in contracts_data:
        existing = db.query(Contract).filter(Contract.contract_number == contract_data["contract_number"]).first()
        if not existing:
            contract = Contract(**contract_data)
            db.add(contract)
    
    db.commit()
    print(f"✓ Created {len(contracts_data)} contracts")


def main():
    print("Starting seed data process...")
    db = SessionLocal()
    
    try:
        seed_users(db)
        seed_areas(db)
        seed_buildings(db)
        seed_complaints(db)
        seed_tasks(db)
        seed_contracts(db)

        # Check for insecure default passwords
        check_default_passwords(db)
        
        print("\n✅ Seed data completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
