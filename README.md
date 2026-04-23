# Dummar Project Management Platform

منصة إدارة مشروع دمّر - دمشق

A comprehensive platform for managing the Damascus Dummar Project, combining internal project management, electronic contract management, citizen complaints intake, and field task management with location-based operations.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL with PostGIS
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4
- **Database**: PostgreSQL 15+ with PostGIS extension

## Quick Start

### Prerequisites

For VPS / production deployment via the provided `deploy.sh`:

| Tool                | Required? | Notes                                              |
|---------------------|-----------|----------------------------------------------------|
| Docker Engine 20+   | yes       | Runs db / backend / nginx                          |
| Docker Compose v2   | yes       | `docker compose` plugin (or standalone)            |
| Node.js 20+ + npm   | yes       | Frontend is built on the host (Vite 8 + Tailwind 4)|
| Certbot             | optional  | Only if you use the bundled Let's Encrypt script   |
| PostgreSQL on host  | **no**    | Runs inside the `db` container (`postgis/postgis`) |
| nginx on host       | **no**    | Runs inside the `nginx` container                  |
| Python on host      | **no**    | Backend runs inside the `backend` container        |

For local frontend development only:

| Tool                | Required? | Notes                                              |
|---------------------|-----------|----------------------------------------------------|
| Node.js 20+         | yes       | Vite dev server                                    |
| Docker              | yes       | For database + backend                             |

### 1. Start the stack

```bash
docker compose up -d
```

This starts:
- PostgreSQL with PostGIS (no external port — internal only)
- FastAPI backend on `127.0.0.1:8000` (localhost only — nginx is the public entry)
- nginx on port 80 (and 443 once SSL is set up)

> **Note:** the stack will refuse to start if `DB_PASSWORD` and `SECRET_KEY` are
> not set in `.env`. Run `./deploy.sh` once to auto-generate a safe `.env`,
> or copy values manually from `PRODUCTION_DEPLOYMENT_GUIDE.md`.

### 2. Initialize the database

Migrations run automatically when the backend container starts. To run them manually or to load seed data:

```bash
# Run migrations explicitly (already auto-run on container start)
docker compose exec backend alembic upgrade head

# Load seed data (first deployment only). Generates strong random passwords
# per account and writes them to /tmp/seed_credentials.txt inside the container.
docker compose exec backend python -m app.scripts.seed_data
docker compose exec backend cat /tmp/seed_credentials.txt   # retrieve & distribute
docker compose exec backend rm  /tmp/seed_credentials.txt   # delete after use
```

For local test/development workflows that need the legacy `password123` for every account, run with `--force-default-passwords` (NEVER use this in production):

```bash
docker compose exec backend python -m app.scripts.seed_data --force-default-passwords
```

### 3. Start the frontend (dev)

```bash
npm install
# Copy .env.example and adjust if needed
cp .env.example .env
npm run dev
```

Frontend (dev): http://localhost:5173
Backend API docs (dev only — disabled in production): http://localhost:8000/docs

### Frontend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL (no trailing slash) |

For deployment, set `VITE_API_BASE_URL` to your production backend URL before building.

### Local Backend Development (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env from .env.example
cp .env.example .env
# Edit DATABASE_URL to point to your local PostgreSQL

uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

> **Note:** `bcrypt==3.2.2` is pinned in requirements.txt for compatibility with `passlib==1.7.4`.
> Later versions of bcrypt (4.x+) remove internal APIs that passlib depends on.

## Default Login Credentials

> **Production seed mode (default):** when you run `python -m app.scripts.seed_data`,
> each seeded account gets a strong random password (24 URL-safe chars, ≈144 bits)
> written to `/tmp/seed_credentials.txt` inside the backend container (chmod 600). Distribute these via a
> secure channel and delete the file. The application logs a security warning at
> startup if any account is still using the legacy `password123`.
>
> **Test / development mode (opt-in only):** the legacy fixed password
> `password123` is used for all accounts when you pass `--force-default-passwords`
> or set `SEED_DEFAULT_PASSWORDS=1`. NEVER use this mode in production.

The seeded usernames and roles are:

| Username | Role | الاسم |
|----------|------|-------|
| director | project_director | م. أحمد الخطيب |
| contracts_mgr | contracts_manager | م. سامر القاسم |
| engineer | engineer_supervisor | م. ليلى حسن |
| complaints_off | complaints_officer | عمر المصري |
| area_sup | area_supervisor | خالد الأحمد |
| field_user | field_team | يوسف العلي |
| contractor | contractor_user | شركة البناء الحديث |
| citizen1 | citizen | مواطن — سمير الحسن |

> **Note:** The citizen account shares phone `+963911234567` with complaint CMP00000001,
> so it will show that complaint in the citizen dashboard.

## Project Structure

```
.
├── backend/
│   ├── alembic/               # Database migrations
│   ├── app/
│   │   ├── api/               # API routes (auth, complaints, contracts, tasks, locations, users, dashboard, uploads)
│   │   ├── core/              # Config, security, database
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Audit logging, PDF generation
│   │   └── scripts/           # Seed data
│   ├── Dockerfile
│   └── requirements.txt
├── src/                       # React frontend
│   ├── components/            # Layout + shadcn UI components
│   ├── pages/                 # All page components
│   ├── services/api.ts        # API client
│   └── main.tsx               # Entry point
├── docker-compose.yml
├── package.json
└── vite.config.ts
```

## Frontend Pages

### Public (No Login Required)
- `/complaints/new` - Submit new complaint (تقديم شكوى)
- `/complaints/track` - Track complaint by number + phone (تتبع الشكوى)

### Internal (Login Required)
- `/dashboard` - Dashboard with stats (لوحة التحكم)
- `/complaints` - Complaints list with filters (الشكاوى)
- `/complaints/:id` - Complaint details + activity timeline
- `/tasks` - Tasks list with filters (المهام)
- `/tasks/:id` - Task details + activity timeline
- `/contracts` - Contracts list with filters (العقود)
- `/contracts/:id` - Contract details + approval trail
- `/locations` - Areas and buildings (المواقع)

## API Endpoints

### Auth
- `POST /auth/login` - Login
- `GET /auth/me` - Current user

### Complaints
- `POST /complaints/` - Create complaint (public)
- `POST /complaints/track` - Track complaint (public)
- `GET /complaints/` - List complaints (auth)
- `GET /complaints/{id}` - Get complaint (auth)
- `PUT /complaints/{id}` - Update complaint (auth)
- `GET /complaints/{id}/activities` - Activity timeline (auth)

### Tasks
- `POST /tasks/` - Create task
- `GET /tasks/` - List tasks
- `GET /tasks/{id}` - Get task
- `PUT /tasks/{id}` - Update task
- `GET /tasks/{id}/activities` - Activity timeline

### Contracts
- `POST /contracts/` - Create contract (contracts_manager+)
- `GET /contracts/` - List contracts
- `GET /contracts/{id}` - Get contract
- `PUT /contracts/{id}` - Update contract
- `POST /contracts/{id}/approve` - Approve/change status
- `POST /contracts/{id}/generate-pdf` - Generate PDF summary
- `GET /contracts/{id}/approvals` - Approval trail
- `DELETE /contracts/{id}` - Delete draft contract

### Locations
- `GET /locations/areas` - List areas
- `GET /locations/buildings` - List buildings

### Uploads
- `POST /uploads/` - Upload file (images, PDFs, docs)

### Dashboard
- `GET /dashboard/stats` - Statistics
- `GET /dashboard/recent-activity` - Recent activity

## Environment Variables

```
DATABASE_URL=postgresql://dummar:<STRONG_PASSWORD>@db:5432/dummar_db
SECRET_KEY=<32+ random chars — generate with `openssl rand -base64 32`>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
UPLOAD_DIR=/app/uploads
ENVIRONMENT=production           # disables /docs, /redoc, /openapi.json
ENABLE_API_DOCS=false            # set true to re-enable docs (e.g. behind auth proxy)
CORS_ORIGINS=https://dummar.example.com
LOG_LEVEL=info
```

> The Docker stack will refuse to start if `DB_PASSWORD` or `SECRET_KEY`
> is missing from `.env` (see `docker-compose.yml`).

## Security Posture (Production Defaults)

- `/docs`, `/redoc`, `/openapi.json` — **disabled** in production
  (`ENVIRONMENT=production`). Set `ENABLE_API_DOCS=true` to re-enable
  (do this only behind an authenticated reverse proxy).
- `/health` and `/health/ready` — public (used by container orchestrators
  and load balancers).
- `/health/detailed`, `/health/smtp`, `/health/ocr`, `/metrics` — require
  authenticated internal staff (`get_current_internal_user`).
- `/uploads/contracts/*` and `/uploads/contract_intelligence/*` — proxied
  to the backend and require internal-staff auth (sensitive documents).
- `/uploads/complaints/*`, `/uploads/profiles/*`, `/uploads/general/*`,
  `/uploads/tasks/*` — served as static files by nginx (citizen-facing,
  random-UUID filenames; do NOT place confidential data here).
- Backend port `8000` is bound to `127.0.0.1` only — nginx is the public
  entry point. Override with `BACKEND_BIND=0.0.0.0` only behind an
  external load balancer.
- Database port is **not** published.
- Migrations are **fatal**: if `alembic upgrade head` fails the container
  exits non-zero and Docker restarts it; the API never serves traffic
  against an inconsistent schema.

## Technology Stack

### Backend
- FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL + PostGIS
- Pydantic v2, Python-JOSE (JWT), Passlib (bcrypt)
- ReportLab (PDF generation), QRCode, Pillow

### Frontend
- React 19, TypeScript, Vite 7
- Tailwind CSS v4, shadcn/ui components
- React Router v7, React Hook Form, Zod
- Phosphor Icons, date-fns, Sonner (toasts)

## License

Proprietary - Damascus Dummar Project

## Deployment

See [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md) for complete production deployment instructions covering:
- PostgreSQL/PostGIS setup
- Backend & frontend deployment
- SMTP email configuration
- CORS, security, and file upload settings
- CI/CD pipeline details
- Rollback procedures

## CI/CD

The project includes a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) that automatically:
- Runs backend tests (pytest) on Python 3.12
- Builds the frontend (npm build) on Node.js 18
- Runs on every push and pull request to `main`
