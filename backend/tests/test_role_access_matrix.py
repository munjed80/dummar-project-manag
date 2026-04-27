from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.task import Task, TaskSourceType, TaskStatus, TaskPriority
from datetime import date
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.location import Location, LocationType, LocationStatus
from app.models.investment_property import InvestmentProperty, PropertyStatus, PropertyType


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _mk_user(db, username: str, role: UserRole):
    u = User(
        username=username,
        full_name=username,
        hashed_password=get_password_hash("testpass123"),
        role=role,
        is_active=1,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_location(db):
    loc = Location(
        name="اختبار",
        code="LOC-RBAC",
        location_type=LocationType.ISLAND,
        status=LocationStatus.ACTIVE,
        is_active=1,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _mk_contract(db, creator_id: int):
    c = Contract(
        contract_number=f"RBAC-{creator_id}",
        title="RBAC Contract",
        contractor_name="Contractor",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        total_value=1000,
        contract_type=ContractType.MAINTENANCE,
        status=ContractStatus.ACTIVE,
        created_by_id=creator_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _mk_task(db, assignee_id: int):
    t = Task(
        title="RBAC Task",
        description="desc",
        source_type=TaskSourceType.INTERNAL,
        status=TaskStatus.ASSIGNED,
        priority=TaskPriority.MEDIUM,
        assigned_to_id=assignee_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_director_full_access_endpoints(client, db, director_token):
    r_users = client.get("/users/", headers=_auth(director_token))
    assert r_users.status_code == 200

    r_contracts = client.get("/contracts/", headers=_auth(director_token))
    assert r_contracts.status_code == 200

    r_locations = client.get("/locations/list", headers=_auth(director_token))
    assert r_locations.status_code == 200


def test_property_manager_can_access_property_module(client, db):
    _mk_property = InvestmentProperty(
        property_type=PropertyType.BUILDING,
        address="العنوان",
        status=PropertyStatus.AVAILABLE,
    )
    db.add(_mk_property)
    db.commit()

    _mk_user(db, "pm_role", UserRole.PROPERTY_MANAGER)
    token = client.post("/auth/login", json={"username": "pm_role", "password": "testpass123"}).json()["access_token"]

    r = client.get("/investment-properties/", headers=_auth(token))
    assert r.status_code == 200


def test_investment_manager_can_access_investment_contracts(client, db):
    _mk_user(db, "im_role", UserRole.INVESTMENT_MANAGER)
    token = client.post("/auth/login", json={"username": "im_role", "password": "testpass123"}).json()["access_token"]

    r = client.get("/investment-contracts/", headers=_auth(token))
    assert r.status_code == 200


def test_contracts_manager_can_access_operational_contracts(client, db):
    _mk_user(db, "cm_role", UserRole.CONTRACTS_MANAGER)
    token = client.post("/auth/login", json={"username": "cm_role", "password": "testpass123"}).json()["access_token"]

    r = client.get("/contracts/", headers=_auth(token))
    assert r.status_code == 200


def test_field_and_contractor_only_see_assigned_tasks(client, db):
    field = _mk_user(db, "field_only_assigned", UserRole.FIELD_TEAM)
    contractor = _mk_user(db, "contractor_only_assigned", UserRole.CONTRACTOR_USER)
    stranger = _mk_user(db, "stranger", UserRole.FIELD_TEAM)

    _mk_task(db, assignee_id=field.id)
    _mk_task(db, assignee_id=contractor.id)
    _mk_task(db, assignee_id=stranger.id)

    ft = client.post("/auth/login", json={"username": field.username, "password": "testpass123"}).json()["access_token"]
    ct = client.post("/auth/login", json={"username": contractor.username, "password": "testpass123"}).json()["access_token"]

    r_ft = client.get("/tasks/", headers=_auth(ft))
    ids_ft = {item["assigned_to_id"] for item in r_ft.json()["items"]}
    assert r_ft.status_code == 200
    assert ids_ft == {field.id}

    r_ct = client.get("/tasks/", headers=_auth(ct))
    ids_ct = {item["assigned_to_id"] for item in r_ct.json()["items"]}
    assert r_ct.status_code == 200
    assert ids_ct == {contractor.id}


def test_field_and_contractor_cannot_access_users_contracts_locations_management(client, db):
    field = _mk_user(db, "field_lockdown", UserRole.FIELD_TEAM)
    contractor = _mk_user(db, "contractor_lockdown", UserRole.CONTRACTOR_USER)
    loc = _mk_location(db)

    ft = client.post("/auth/login", json={"username": field.username, "password": "testpass123"}).json()["access_token"]
    ct = client.post("/auth/login", json={"username": contractor.username, "password": "testpass123"}).json()["access_token"]

    for token in (ft, ct):
        assert client.get("/users/", headers=_auth(token)).status_code == 403
        assert client.post("/locations/", headers=_auth(token), json={
            "name": "x",
            "code": "LOCK-1",
            "location_type": "island",
            "status": "active",
            "is_active": 1,
        }).status_code == 403
        # Operational contracts list is restricted; field/contractor should not
        # get any global visibility.
        r_contracts = client.get("/contracts/", headers=_auth(token))
        assert r_contracts.status_code == 200
        assert r_contracts.json()["items"] == []

    # Direct mutation endpoint stays protected too.
    assert client.put(f"/locations/{loc.id}", headers=_auth(ft), json={"name": "y"}).status_code == 403
