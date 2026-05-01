# CLAUDE.md — Agent Instructions for Dummar Project Management

## Purpose
This file instructs the Claude/Copilot coding agent on how to behave in this repository.

## Project Overview
Dummar Project Management is a full-stack application:
- **Frontend**: React + TypeScript + Vite (root `src/`)
- **Backend**: Python FastAPI + SQLAlchemy + Alembic (root `backend/`)
- **Infrastructure**: Docker Compose, Nginx (nginx.conf / nginx-ssl.conf)

## Key Commands

### Backend
```bash
cd backend
python -m pytest tests/ -q          # Run all backend tests (currently 526)
alembic upgrade head                 # Apply migrations
uvicorn app.main:app --reload        # Start dev server
```

### Frontend
```bash
npm install                          # Install dependencies
npm run dev                          # Start Vite dev server
npm run build                        # Production build
npm run lint                         # ESLint
```

### Docker
```bash
docker compose up --build            # Build and start all services
docker compose logs -f backend       # Tail backend logs
```

## Coding Conventions

### Backend
- Models live in `backend/app/models/`
- API routers live in `backend/app/api/`
- Schemas (Pydantic) live in `backend/app/schemas/`
- Services live in `backend/app/services/`
- Migrations in `backend/alembic/versions/` — sequential numbered prefix (e.g. `018_...`)
- RBAC via `backend/app/core/permissions.py` — always add new `ResourceType`/`Action` entries there
- Use `track_execution()` from `app/services/execution_log.py` for auditable actions
- PostgreSQL enums: add new values via `ALTER TYPE ... ADD VALUE` in migration
- Soft-delete pattern: `is_active = False` (never hard-delete business records)

### Frontend
- Pages in `src/pages/`, shared components in `src/components/`
- API calls through `src/services/api.ts`
- Auth state from `useAuth` hook (`src/hooks/useAuth.ts`)
- Tailwind CSS for styling; theme tokens in `theme.json`

### General
- Do **not** commit secrets or credentials
- Follow existing file naming conventions (snake_case backend, PascalCase frontend components)
- Update `PROJECT_CONTINUITY.md` after every completed task

## After Every Task
Update `PROJECT_CONTINUITY.md` with:
1. What was done
2. Files changed
3. Commands run
4. Results / test counts
5. Current project state
6. Recommended next step
