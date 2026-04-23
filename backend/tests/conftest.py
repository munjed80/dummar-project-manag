"""
Shared test fixtures for backend API tests.

Uses an in-memory SQLite database overridden via dependency injection
so that the real Postgres connection is never needed in CI.
"""

import os
import pytest
from sqlalchemy import create_engine, event, String
from sqlalchemy.orm import sessionmaker

# ── Override env vars BEFORE any app import ──
os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["UPLOAD_DIR"] = "/tmp/test_uploads"
os.makedirs("/tmp/test_uploads", exist_ok=True)

# Patch GeoAlchemy2 Geometry type to behave as plain String on SQLite
import geoalchemy2  # noqa: E402
from sqlalchemy.types import TypeDecorator, UserDefinedType  # noqa: E402


class _NullGeometry(UserDefinedType):
    """A no-op replacement for Geometry that works on SQLite."""
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # Accept and ignore any arguments the original Geometry receives
        pass

    def get_col_spec(self):
        return "TEXT"

    def bind_processor(self, dialect):
        return None

    def result_processor(self, dialect, coltype):
        return None


# Monkey-patch before models are imported
geoalchemy2.types.Geometry = _NullGeometry
geoalchemy2.Geometry = _NullGeometry

from fastapi.testclient import TestClient  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.models.location import Area  # noqa: E402
from app.models.location import Location, LocationType, LocationStatus, ContractLocation  # noqa: E402
from app.main import app  # noqa: E402


# ── In-memory SQLite engine ──
# Use StaticPool to share a single connection across all sessions
from sqlalchemy.pool import StaticPool

SQLALCHEMY_TEST_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign keys in SQLite and register GeoAlchemy2 stub functions
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
    # Register stub functions that GeoAlchemy2 may call during SELECT
    dbapi_conn.create_function("AsEWKB", 1, lambda x: x)
    dbapi_conn.create_function("ST_GeomFromEWKT", 1, lambda x: x)
    dbapi_conn.create_function("ST_GeomFromText", 2, lambda x, y: x)
    dbapi_conn.create_function("ST_AsEWKB", 1, lambda x: x)


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db():
    """Re-create all tables for every test so tests are fully isolated.

    SQLite cannot drop tables with circular foreign keys (e.g. Project↔Contract)
    while PRAGMA foreign_keys=ON, so we toggle it off for the teardown only.
    """
    Base.metadata.create_all(bind=engine)
    yield
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(bind=conn)
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")


@pytest.fixture()
def db():
    """Provide a DB session scoped to a single test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """Provide a TestClient that talks to the overridden app."""
    return TestClient(app)


def _create_user(db, username: str, role: UserRole, password: str = "testpass123"):
    user = User(
        username=username,
        full_name=f"Test {username}",
        hashed_password=get_password_hash(password),
        role=role,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username: str, password: str = "testpass123"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()["access_token"]


def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def director_user(db):
    return _create_user(db, "test_director", UserRole.PROJECT_DIRECTOR)


@pytest.fixture()
def director_token(client, director_user):
    return _login(client, "test_director")


@pytest.fixture()
def field_user(db):
    return _create_user(db, "test_field", UserRole.FIELD_TEAM)


@pytest.fixture()
def field_token(client, field_user):
    return _login(client, "test_field")


@pytest.fixture()
def contractor_user(db):
    return _create_user(db, "test_contractor", UserRole.CONTRACTOR_USER)


@pytest.fixture()
def contractor_token(client, contractor_user):
    return _login(client, "test_contractor")


@pytest.fixture()
def citizen_user(db):
    return _create_user(db, "test_citizen", UserRole.CITIZEN, password="testpass123")


@pytest.fixture()
def citizen_token(client, citizen_user):
    return _login(client, "test_citizen")


@pytest.fixture()
def sample_area(db):
    area = Area(name="ISL-A", name_ar="الجزيرة أ", code="ISL-A")
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@pytest.fixture()
def sample_location(db):
    loc = Location(
        name="جزيرة 1",
        code="ISL-001",
        location_type=LocationType.ISLAND,
        status=LocationStatus.ACTIVE,
        description="الجزيرة الأولى",
        is_active=1,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@pytest.fixture()
def sample_location_tree(db):
    """Create a 3-level hierarchy: island -> sector -> building."""
    island = Location(
        name="جزيرة 5",
        code="ISL-005",
        location_type=LocationType.ISLAND,
        status=LocationStatus.ACTIVE,
        is_active=1,
    )
    db.add(island)
    db.commit()
    db.refresh(island)

    sector = Location(
        name="قطاع أ",
        code="SEC-005-A",
        location_type=LocationType.SECTOR,
        parent_id=island.id,
        status=LocationStatus.ACTIVE,
        is_active=1,
    )
    db.add(sector)
    db.commit()
    db.refresh(sector)

    building = Location(
        name="مبنى 1",
        code="BLD-005-A-01",
        location_type=LocationType.BUILDING,
        parent_id=sector.id,
        status=LocationStatus.ACTIVE,
        is_active=1,
    )
    db.add(building)
    db.commit()
    db.refresh(building)

    return {"island": island, "sector": sector, "building": building}
