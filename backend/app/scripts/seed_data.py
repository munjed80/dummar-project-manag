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
        {"username": "director", "password": "password123", "full_name": "Project Director", "role": UserRole.PROJECT_DIRECTOR, "email": "director@dummar.gov.sy"},
        {"username": "contracts_mgr", "password": "password123", "full_name": "Contracts Manager", "role": UserRole.CONTRACTS_MANAGER, "email": "contracts@dummar.gov.sy"},
        {"username": "engineer", "password": "password123", "full_name": "Engineer Supervisor", "role": UserRole.ENGINEER_SUPERVISOR, "email": "engineer@dummar.gov.sy"},
        {"username": "complaints_off", "password": "password123", "full_name": "Complaints Officer", "role": UserRole.COMPLAINTS_OFFICER, "email": "complaints@dummar.gov.sy"},
        {"username": "area_sup", "password": "password123", "full_name": "Area Supervisor", "role": UserRole.AREA_SUPERVISOR, "email": "area@dummar.gov.sy"},
        {"username": "field_user", "password": "password123", "full_name": "Field Team Member", "role": UserRole.FIELD_TEAM, "email": "field@dummar.gov.sy"},
        {"username": "contractor", "password": "password123", "full_name": "Contractor User", "role": UserRole.CONTRACTOR_USER, "email": "contractor@dummar.gov.sy"},
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
    print("Seeding areas (Dummar islands)...")
    areas_data = [
        {"name": "Island A", "name_ar": "الجزيرة أ", "code": "ISL-A", "description": "Northern residential zone"},
        {"name": "Island B", "name_ar": "الجزيرة ب", "code": "ISL-B", "description": "Commercial and mixed-use area"},
        {"name": "Island C", "name_ar": "الجزيرة ج", "code": "ISL-C", "description": "Southern residential development"},
        {"name": "Island D", "name_ar": "الجزيرة د", "code": "ISL-D", "description": "Green spaces and parks"},
        {"name": "Island E", "name_ar": "الجزيرة هـ", "code": "ISL-E", "description": "Educational facilities zone"},
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
        {"area_id": areas[0].id, "name": "Tower 1", "name_ar": "البرج 1", "building_number": "A-001", "floors": 12},
        {"area_id": areas[0].id, "name": "Tower 2", "name_ar": "البرج 2", "building_number": "A-002", "floors": 15},
        {"area_id": areas[1].id, "name": "Commercial Complex", "name_ar": "المجمع التجاري", "building_number": "B-001", "floors": 8},
        {"area_id": areas[2].id, "name": "Residential Block 1", "name_ar": "الكتلة السكنية 1", "building_number": "C-001", "floors": 10},
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
            "full_name": "Ahmed Hassan",
            "phone": "+963911234567",
            "complaint_type": ComplaintType.ROADS,
            "description": "There is a large pothole on the main street causing traffic issues",
            "location_text": "Main Street, near Tower 1",
            "area_id": areas[0].id if areas else None,
            "status": ComplaintStatus.NEW,
            "priority": ComplaintPriority.HIGH,
        },
        {
            "tracking_number": "CMP00000002",
            "full_name": "Fatima Al-Mansour",
            "phone": "+963912345678",
            "complaint_type": ComplaintType.LIGHTING,
            "description": "Street lights not working in the evening",
            "location_text": "Park Avenue, Island B",
            "area_id": areas[1].id if len(areas) > 1 else None,
            "status": ComplaintStatus.UNDER_REVIEW,
            "priority": ComplaintPriority.MEDIUM,
            "assigned_to_id": users[0].id if users else None,
        },
        {
            "tracking_number": "CMP00000003",
            "full_name": "Mohammed Khalil",
            "phone": "+963913456789",
            "complaint_type": ComplaintType.CLEANING,
            "description": "Garbage collection has been delayed for several days",
            "location_text": "Residential Block 1",
            "area_id": areas[2].id if len(areas) > 2 else None,
            "status": ComplaintStatus.ASSIGNED,
            "priority": ComplaintPriority.URGENT,
            "assigned_to_id": users[0].id if users else None,
        },
        {
            "tracking_number": "CMP00000004",
            "full_name": "Layla Ibrahim",
            "phone": "+963914567890",
            "complaint_type": ComplaintType.WATER,
            "description": "Water pressure is very low in the building",
            "location_text": "Tower 2, Floor 8",
            "area_id": areas[0].id if areas else None,
            "status": ComplaintStatus.IN_PROGRESS,
            "priority": ComplaintPriority.HIGH,
        },
        {
            "tracking_number": "CMP00000005",
            "full_name": "Youssef Adnan",
            "phone": "+963915678901",
            "complaint_type": ComplaintType.INFRASTRUCTURE,
            "description": "Sidewalk is cracked and dangerous for pedestrians",
            "location_text": "Commercial Complex entrance",
            "area_id": areas[1].id if len(areas) > 1 else None,
            "status": ComplaintStatus.RESOLVED,
            "priority": ComplaintPriority.MEDIUM,
            "resolved_at": datetime.utcnow() - timedelta(days=2),
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
            "title": "Repair pothole on Main Street",
            "description": "Fill and repair the large pothole reported by citizen",
            "source_type": TaskSourceType.COMPLAINT,
            "complaint_id": complaints[0].id if complaints else None,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[0].id if areas else None,
            "status": TaskStatus.ASSIGNED,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=3),
        },
        {
            "title": "Replace street light bulbs",
            "description": "Replace non-functional street lights on Park Avenue",
            "source_type": TaskSourceType.INTERNAL,
            "assigned_to_id": users[0].id if users else None,
            "area_id": areas[1].id if len(areas) > 1 else None,
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.MEDIUM,
            "due_date": date.today() + timedelta(days=5),
        },
        {
            "title": "Coordinate garbage collection",
            "description": "Arrange immediate garbage collection for residential area",
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
            "title": "Inspect water pump system",
            "description": "Check water pressure system in Tower 2",
            "source_type": TaskSourceType.INTERNAL,
            "area_id": areas[0].id if areas else None,
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.HIGH,
            "due_date": date.today() + timedelta(days=2),
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
            "title": "Road Infrastructure Development Phase 1",
            "contractor_name": "Damascus Construction Co.",
            "contractor_contact": "+963211234567",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("5000000.00"),
            "start_date": date(2024, 1, 15),
            "end_date": date(2024, 12, 31),
            "execution_duration_days": 350,
            "status": ContractStatus.ACTIVE,
            "scope_description": "Construction and paving of main roads connecting all islands",
            "related_areas": "Island A, Island B, Island C",
            "created_by_id": users[0].id,
            "approved_by_id": users[0].id,
            "approved_at": datetime.utcnow() - timedelta(days=30),
        },
        {
            "contract_number": "CNT-2024-002",
            "title": "Electrical Systems Maintenance",
            "contractor_name": "Syrian Electrical Services",
            "contractor_contact": "+963212345678",
            "contract_type": ContractType.MAINTENANCE,
            "contract_value": Decimal("850000.00"),
            "start_date": date(2024, 3, 1),
            "end_date": date(2025, 2, 28),
            "execution_duration_days": 365,
            "status": ContractStatus.ACTIVE,
            "scope_description": "Ongoing maintenance of street lighting and electrical infrastructure",
            "related_areas": "All Islands",
            "created_by_id": users[0].id,
            "approved_by_id": users[0].id,
            "approved_at": datetime.utcnow() - timedelta(days=20),
        },
        {
            "contract_number": "CNT-2024-003",
            "title": "Landscaping and Green Spaces",
            "contractor_name": "Green Damascus LLC",
            "contractor_contact": "+963213456789",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("1200000.00"),
            "start_date": date(2024, 4, 1),
            "end_date": date(2024, 10, 31),
            "execution_duration_days": 213,
            "status": ContractStatus.APPROVED,
            "scope_description": "Development of parks and green spaces in Island D",
            "related_areas": "Island D",
            "created_by_id": users[0].id,
            "approved_by_id": users[0].id,
            "approved_at": datetime.utcnow() - timedelta(days=5),
        },
        {
            "contract_number": "CNT-2024-004",
            "title": "Water Supply System Upgrade",
            "contractor_name": "Aqua Systems Syria",
            "contractor_contact": "+963214567890",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("3500000.00"),
            "start_date": date(2024, 6, 1),
            "end_date": date(2025, 5, 31),
            "execution_duration_days": 365,
            "status": ContractStatus.UNDER_REVIEW,
            "scope_description": "Upgrade and expansion of water distribution network",
            "related_areas": "All Islands",
            "created_by_id": users[0].id,
        },
        {
            "contract_number": "CNT-2024-005",
            "title": "Educational Facilities Construction",
            "contractor_name": "National Builders Group",
            "contractor_contact": "+963215678901",
            "contract_type": ContractType.CONSTRUCTION,
            "contract_value": Decimal("8000000.00"),
            "start_date": date(2024, 7, 1),
            "end_date": date(2025, 12, 31),
            "execution_duration_days": 548,
            "status": ContractStatus.DRAFT,
            "scope_description": "Construction of schools and educational facilities in Island E",
            "related_areas": "Island E",
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
