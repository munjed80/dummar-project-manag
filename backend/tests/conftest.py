"""
Shared test fixtures for backend API tests.

Runs against a real PostgreSQL instance so that tests exercise the same
DDL the production database uses (PostGIS, native ENUMs, BOOLEAN). The
schema is materialised with the actual Alembic migration chain rather
than ``Base.metadata.create_all()`` so broken migrations cannot pass
silently.

How the database is provisioned:

* ``DUMMAR_TEST_DATABASE_URL`` (or ``TEST_DATABASE_URL``) — if set, that
  PostgreSQL DSN is used as-is. Useful in CI/devcontainers that already
  have a Postgres + PostGIS service running.
* Otherwise we attempt to start a throwaway ``postgis/postgis:16-3.4-alpine``
  container via the ``docker`` CLI and stop it at the end of the test
  session. This keeps developer setup as simple as ``pytest``.

Per-test isolation is achieved by truncating every user table after the
session has migrated the schema once. This is several orders of
magnitude faster than re-running ``alembic upgrade head`` for each test.
"""

import os
import shutil
import socket
import subprocess
import time
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# Database URL resolution
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Pick an unused localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_DOCKER_CONTAINER_NAME = None  # type: ignore[assignment]


def _start_postgis_container() -> str:
    """Spin up a temporary postgis container and return its DSN.

    Raises ``RuntimeError`` if Docker is not available so the caller can
    surface a clear error to the developer.
    """
    global _DOCKER_CONTAINER_NAME

    if shutil.which("docker") is None:
        raise RuntimeError(
            "PostgreSQL is required for the test suite. Either set "
            "DUMMAR_TEST_DATABASE_URL to a running Postgres+PostGIS DSN "
            "or install Docker so the test harness can start one."
        )

    name = f"dummar_pg_test_{uuid.uuid4().hex[:8]}"
    port = _free_port()
    image = os.environ.get(
        "DUMMAR_TEST_POSTGIS_IMAGE", "postgis/postgis:16-3.4-alpine"
    )
    subprocess.run(
        [
            "docker", "run", "-d", "--rm",
            "--name", name,
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=dummar_test",
            "-p", f"{port}:5432",
            image,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    _DOCKER_CONTAINER_NAME = name

    dsn = f"postgresql://postgres:test@127.0.0.1:{port}/dummar_test"

    # Wait for the server to accept connections.
    deadline = time.time() + 60
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            engine = create_engine(dsn)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return dsn
        except Exception as exc:  # pragma: no cover - timing dependent
            last_err = exc
            time.sleep(0.5)
    raise RuntimeError(
        f"Postgres container {name} did not become ready in time: {last_err}"
    )


def _stop_postgis_container() -> None:
    if _DOCKER_CONTAINER_NAME is None:
        return
    subprocess.run(
        ["docker", "stop", _DOCKER_CONTAINER_NAME],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


_BASE_DSN = (
    os.environ.get("DUMMAR_TEST_DATABASE_URL")
    or os.environ.get("TEST_DATABASE_URL")
)
if not _BASE_DSN:
    _BASE_DSN = _start_postgis_container()


# Each pytest worker (xdist) needs its own database so they don't trash each
# other's state. Without xdist we fall back to a single shared DB.
_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "main")


def _per_worker_database_url(base_dsn: str, worker_id: str) -> str:
    """Create a worker-scoped database and return its DSN."""
    admin_engine = create_engine(base_dsn, isolation_level="AUTOCOMMIT")
    target_db = f"dummar_test_{worker_id}"
    with admin_engine.connect() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": target_db},
        ).scalar()
        if existing:
            # Drop and recreate to start from a clean slate every session.
            conn.execute(text(f'DROP DATABASE "{target_db}"'))
        conn.execute(text(f'CREATE DATABASE "{target_db}"'))
    admin_engine.dispose()

    # Replace the database segment of the DSN.
    if "/" in base_dsn:
        prefix, _ = base_dsn.rsplit("/", 1)
        return f"{prefix}/{target_db}"
    return f"{base_dsn}/{target_db}"


_DATABASE_URL = _per_worker_database_url(_BASE_DSN, _WORKER_ID)


# ── Override env vars BEFORE any app import ──
os.environ["DATABASE_URL"] = _DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["UPLOAD_DIR"] = "/tmp/test_uploads"
os.makedirs("/tmp/test_uploads", exist_ok=True)
# Force background-job tasks to run inline (no Redis broker available in CI).
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ.setdefault("CELERY_BROKER_URL", "")


# ---------------------------------------------------------------------------
# Schema bootstrap via Alembic
# ---------------------------------------------------------------------------

# Enable PostGIS first so geometry columns in migration 001 work.
_setup_engine = create_engine(_DATABASE_URL, isolation_level="AUTOCOMMIT")
with _setup_engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
_setup_engine.dispose()


def _run_alembic_upgrade(database_url: str) -> None:
    """Apply ``alembic upgrade head`` against ``database_url``.

    We invoke the Alembic Python API rather than shelling out so we don't
    depend on the alembic CLI being on PATH.
    """
    from alembic.config import Config
    from alembic import command

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(here, "alembic.ini")
    cfg = Config(cfg_path)
    cfg.set_main_option("script_location", os.path.join(here, "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


_run_alembic_upgrade(_DATABASE_URL)


from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.models.location import Area  # noqa: E402
from app.models.location import Location, LocationType, LocationStatus  # noqa: E402
from app.main import app  # noqa: E402


# Use NullPool so connections are always re-checked-out fresh — TRUNCATE
# during teardown otherwise blocks on idle pooled connections that hold
# row locks from a prior test.
engine = create_engine(_DATABASE_URL, poolclass=NullPool, future=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# Make Celery tasks open sessions against the same engine that the API
# tests use.
from app.jobs import tasks as _jobs_tasks  # noqa: E402

_jobs_tasks.set_task_session_factory(TestingSessionLocal)


# Make the central execution-log recorder (used by notifications, automation
# engine and Celery tasks) write into the same engine when callers don't
# pass an explicit `db` session.
from app.services import execution_log as _exec_log_service  # noqa: E402

_exec_log_service.set_log_session_factory(TestingSessionLocal)


# ---------------------------------------------------------------------------
# Per-test isolation: TRUNCATE all data tables after every test.
# ---------------------------------------------------------------------------

def _list_data_tables(connection) -> list[str]:
    """Return all base tables in the public schema except Alembic's own."""
    rows = connection.execute(text(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename NOT LIKE 'spatial_%'
          AND tablename NOT IN ('alembic_version', 'geography_columns',
                                'geometry_columns', 'raster_columns',
                                'raster_overviews')
        """
    ))
    return [r[0] for r in rows]


# Resolve the data-table list once — the schema is fixed for the session.
with engine.connect() as _conn:
    _DATA_TABLES = _list_data_tables(_conn)
_TRUNCATE_SQL = (
    'TRUNCATE TABLE '
    + ', '.join(f'"{t}"' for t in _DATA_TABLES)
    + ' RESTART IDENTITY CASCADE'
) if _DATA_TABLES else None


@pytest.fixture(autouse=True)
def reset_db():
    """Wipe every data row before each test so tests are fully isolated.

    Also resets the slowapi in-memory rate limiter so per-IP counters
    (`@limiter.limit("5/minute")` on POST /complaints/ etc.) don't leak
    between tests in the same file.
    """
    if _TRUNCATE_SQL is not None:
        with engine.begin() as conn:
            conn.execute(text(_TRUNCATE_SQL))
    # Best-effort limiter reset — modules are imported lazily so guard
    # against ImportError to keep this fixture robust.
    try:
        from app.api.complaints import limiter as _complaints_limiter
        _complaints_limiter.reset()
    except Exception:
        pass
    yield


def pytest_sessionfinish(session, exitstatus):  # noqa: D401
    """Stop the throwaway docker container at the end of the test session."""
    try:
        engine.dispose()
    except Exception:
        pass
    _stop_postgis_container()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
