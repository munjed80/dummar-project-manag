import sys
import os
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.location import Area, Building
from app.models.complaint import Complaint, ComplaintType, ComplaintStatus, ComplaintPriority
from app.models.task import Task, TaskStatus, TaskSourceType, TaskPriority
from app.models.contract import Contract, ContractType, ContractStatus


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


def seed_areas(db: Session):
    print("Seeding areas (Dummar zones)...")
    areas_data = [
        {"name": "Zone 66", "name_ar": "المنطقة 66", "code": "Z-66", "description": "المنطقة السكنية الرئيسية - السكن الشبابي"},
        {"name": "Zone 86", "name_ar": "المنطقة 86", "code": "Z-86", "description": "منطقة الخدمات والمرافق العامة"},
        {"name": "Dummar Al-Sharqi", "name_ar": "دمّر الشرقي", "code": "DMR-E", "description": "الحي السكني الشرقي - أبراج سكنية حديثة"},
        {"name": "Dummar Al-Gharbi", "name_ar": "دمّر الغربي", "code": "DMR-W", "description": "الحي السكني الغربي - فلل ومباني منخفضة"},
        {"name": "Al-Hameh", "name_ar": "الهامة", "code": "HMH", "description": "منطقة الهامة المجاورة - مناطق خضراء وترفيهية"},
        {"name": "Commercial Center", "name_ar": "المركز التجاري", "code": "COM", "description": "المنطقة التجارية المركزية - مجمعات تجارية"},
    ]
    
    for area_data in areas_data:
        existing = db.query(Area).filter(Area.code == area_data["code"]).first()
        if not existing:
            area = Area(**area_data)
            db.add(area)
    
    db.commit()
    print(f"✓ Created {len(areas_data)} areas")


def seed_buildings(db: Session):
    print("Seeding buildings...")
    areas = db.query(Area).all()
    if not areas:
        print("⚠ No areas found, skipping buildings")
        return
    
    buildings_data = [
        {"area_id": areas[0].id, "name": "Tower A1", "name_ar": "البرج أ1", "building_number": "66-A1", "floors": 14},
        {"area_id": areas[0].id, "name": "Tower A2", "name_ar": "البرج أ2", "building_number": "66-A2", "floors": 14},
        {"area_id": areas[0].id, "name": "Tower B1", "name_ar": "البرج ب1", "building_number": "66-B1", "floors": 12},
        {"area_id": areas[1].id, "name": "Services Building", "name_ar": "مبنى الخدمات", "building_number": "86-S1", "floors": 4},
        {"area_id": areas[2].id, "name": "East Tower 1", "name_ar": "البرج الشرقي 1", "building_number": "E-T1", "floors": 18},
        {"area_id": areas[2].id, "name": "East Tower 2", "name_ar": "البرج الشرقي 2", "building_number": "E-T2", "floors": 16},
        {"area_id": areas[3].id, "name": "Villa Block 1", "name_ar": "مجمع الفلل 1", "building_number": "W-V1", "floors": 3},
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
            "description": "حفرة كبيرة في الشارع الرئيسي بالقرب من البرج أ1 تسبب مشاكل مرورية وخطر على السيارات",
            "location_text": "الشارع الرئيسي، بالقرب من البرج أ1، المنطقة 66",
            "area_id": areas[0].id if areas else None,
            "status": ComplaintStatus.NEW,
            "priority": ComplaintPriority.HIGH,
        },
        {
            "tracking_number": "CMP00000002",
            "full_name": "فاطمة المنصور",
            "phone": "+963912345678",
            "complaint_type": ComplaintType.LIGHTING,
            "description": "إنارة الشوارع لا تعمل في المساء في منطقة الخدمات مما يسبب صعوبة في التنقل",
            "location_text": "شارع الخدمات، المنطقة 86",
            "area_id": areas[1].id if len(areas) > 1 else None,
            "status": ComplaintStatus.UNDER_REVIEW,
            "priority": ComplaintPriority.MEDIUM,
            "assigned_to_id": users[0].id if users else None,
        },
        {
            "tracking_number": "CMP00000003",
            "full_name": "محمد خليل",
            "phone": "+963913456789",
            "complaint_type": ComplaintType.CLEANING,
            "description": "تأخر جمع النفايات لعدة أيام في منطقة دمّر الشرقي مما يسبب روائح كريهة",
            "location_text": "البرج الشرقي 1، دمّر الشرقي",
            "area_id": areas[2].id if len(areas) > 2 else None,
            "status": ComplaintStatus.ASSIGNED,
            "priority": ComplaintPriority.URGENT,
            "assigned_to_id": users[0].id if users else None,
        },
        {
            "tracking_number": "CMP00000004",
            "full_name": "ليلى إبراهيم",
            "phone": "+963914567890",
            "complaint_type": ComplaintType.WATER,
            "description": "ضغط المياه ضعيف جداً في الطوابق العليا من البرج أ2",
            "location_text": "البرج أ2، الطابق 10، المنطقة 66",
            "area_id": areas[0].id if areas else None,
            "status": ComplaintStatus.IN_PROGRESS,
            "priority": ComplaintPriority.HIGH,
        },
        {
            "tracking_number": "CMP00000005",
            "full_name": "يوسف عدنان",
            "phone": "+963915678901",
            "complaint_type": ComplaintType.INFRASTRUCTURE,
            "description": "تشققات في الرصيف أمام المركز التجاري تشكل خطراً على المشاة",
            "location_text": "أمام المركز التجاري الرئيسي",
            "area_id": areas[5].id if len(areas) > 5 else None,
            "status": ComplaintStatus.RESOLVED,
            "priority": ComplaintPriority.MEDIUM,
            "resolved_at": datetime.utcnow() - timedelta(days=2),
        },
        {
            "tracking_number": "CMP00000006",
            "full_name": "سارة الحلبي",
            "phone": "+963916789012",
            "complaint_type": ComplaintType.ELECTRICITY,
            "description": "انقطاع متكرر في التيار الكهربائي في مجمع الفلل بدمّر الغربي",
            "location_text": "مجمع الفلل 1، دمّر الغربي",
            "area_id": areas[3].id if len(areas) > 3 else None,
            "status": ComplaintStatus.NEW,
            "priority": ComplaintPriority.HIGH,
        },
        {
            "tracking_number": "CMP00000007",
            "full_name": "عبد الرحمن الشامي",
            "phone": "+963917890123",
            "complaint_type": ComplaintType.WATER,
            "description": "تسرب مياه من الأنابيب الرئيسية في الشارع المؤدي للهامة",
            "location_text": "الشارع الرئيسي، الهامة",
            "area_id": areas[4].id if len(areas) > 4 else None,
            "status": ComplaintStatus.UNDER_REVIEW,
            "priority": ComplaintPriority.URGENT,
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
            "description": "ردم وإصلاح الحفرة الكبيرة المبلغ عنها من المواطن في المنطقة 66",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[0].id if complaints else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[0].id if areas else None,
            "status": TaskStatus.ASSIGNED,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=3),
        },
        {
            "title": "استبدال مصابيح الإنارة",
            "description": "استبدال مصابيح الإنارة المعطلة في شارع الخدمات بالمنطقة 86",
            "source_type": TaskSourceType.INTERNAL,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[1].id if len(areas) > 1 else None,
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.MEDIUM,
            "due_date": date.today() + timedelta(days=5),
        },
        {
            "title": "تنسيق جمع النفايات",
            "description": "ترتيب جمع فوري للنفايات في منطقة دمّر الشرقي",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[2].id if len(complaints) > 2 else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[2].id if len(areas) > 2 else None,
            "status": TaskStatus.COMPLETED,
            "priority": TaskPriority.URGENT,
            "due_date": date.today() - timedelta(days=1),
            "completed_at": datetime.utcnow() - timedelta(hours=12),
        },
        {
            "title": "فحص منظومة ضخ المياه",
            "description": "فحص نظام ضغط المياه في البرج أ2 بالمنطقة 66",
            "source_type": TaskSourceType.INTERNAL,
            "area_id": areas[0].id if areas else None,
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=2),
        },
        {
            "title": "صيانة الشبكة الكهربائية",
            "description": "فحص وصيانة الشبكة الكهربائية في مجمع الفلل بدمّر الغربي",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[5].id if len(complaints) > 5 else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[3].id if len(areas) > 3 else None,
            "status": TaskStatus.ASSIGNED,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=4),
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
            "related_areas": "المنطقة 66، المنطقة 86، دمّر الشرقي",
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
            "scope_description": "تطوير الحدائق والمساحات الخضراء في منطقة الهامة",
            "related_areas": "الهامة",
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
            "scope_description": "إنشاء مدارس ومرافق تعليمية في المركز التجاري",
            "related_areas": "المركز التجاري",
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
        
        print("\n✅ Seed data completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
