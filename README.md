# Dummar Project Management Platform

منصة إدارة مشروع دمّر - دمشق

A comprehensive platform for managing the Damascus Dummar Project, combining internal project management, electronic contract management, citizen complaints intake, and field task management with location-based operations.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL with PostGIS
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4
- **Database**: PostgreSQL 15+ with PostGIS extension

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ and npm

### 1. Start the database and backend

```bash
docker-compose up -d
```

This starts:
- PostgreSQL with PostGIS on port 5432
- FastAPI backend on port 8000

### 2. Initialize the database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Load seed data
docker-compose exec backend python -m app.scripts.seed_data
```

### 3. Start the frontend

```bash
npm install
# Copy .env.example and adjust if needed
cp .env.example .env
npm run dev
```

Frontend: http://localhost:5173
Backend API docs: http://localhost:8000/docs

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

| Username | Password | Role | الاسم |
|----------|----------|------|-------|
| director | password123 | project_director | م. أحمد الخطيب |
| contracts_mgr | password123 | contracts_manager | م. سامر القاسم |
| engineer | password123 | engineer_supervisor | م. ليلى حسن |
| complaints_off | password123 | complaints_officer | عمر المصري |
| area_sup | password123 | area_supervisor | خالد الأحمد |
| field_user | password123 | field_team | يوسف العلي |
| contractor | password123 | contractor_user | شركة البناء الحديث |
| citizen1 | password123 | citizen | مواطن — سمير الحسن |

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
DATABASE_URL=postgresql://dummar:dummar_password@db:5432/dummar_db
SECRET_KEY=dummar-secret-key-change-in-production-32chars-min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=/app/uploads
```

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
