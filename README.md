# Dummar Project Management Platform

A comprehensive production-grade platform for managing the Damascus Dummar Project, combining internal project management, electronic contract management, citizen complaints intake, and field task management with location-based operations.

## Architecture

This is a monorepo containing:
- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL with PostGIS
- **Frontend**: React + TypeScript + Tailwind CSS (Spark Template)
- **Database**: PostgreSQL 15+ with PostGIS extension

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ and npm (for frontend development)
- Python 3.11+ (for backend development outside Docker)

### Initial Setup

1. **Clone and navigate to project**
```bash
cd /workspaces/spark-template
```

2. **Start the database and backend with Docker**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL with PostGIS on port 5432
- FastAPI backend on port 8000

3. **Initialize the database**
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Load seed data
docker-compose exec backend python -m app.scripts.seed_data
```

4. **Start the frontend (development)**
```bash
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Project Structure

```
.
├── backend/                    # FastAPI backend
│   ├── alembic/               # Database migrations
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   ├── auth.py
│   │   │   ├── complaints.py
│   │   │   ├── contracts.py
│   │   │   ├── tasks.py
│   │   │   ├── locations.py
│   │   │   ├── users.py
│   │   │   └── dashboard.py
│   │   ├── core/              # Core configuration
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── repositories/      # Data access layer
│   │   ├── scripts/           # Utility scripts
│   │   └── main.py            # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── src/                       # React frontend
│   ├── components/
│   ├── pages/
│   ├── services/              # API client
│   ├── hooks/
│   └── lib/
├── docker-compose.yml
└── README.md
```

## API Documentation

Once the backend is running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Default Users (Seed Data)

| Username | Password | Role |
|----------|----------|------|
| director | password123 | project_director |
| contracts_mgr | password123 | contracts_manager |
| engineer | password123 | engineer_supervisor |
| complaints_off | password123 | complaints_officer |
| area_sup | password123 | area_supervisor |
| field_user | password123 | field_team |
| contractor | password123 | contractor_user |

Public citizen portal requires no login.

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://dummar:dummar_password@db:5432/dummar_db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Frontend
Frontend connects to backend at `http://localhost:8000` by default.

## Development

### Backend Development
```bash
# Enter backend container
docker-compose exec backend bash

# Run tests (when implemented)
pytest

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Frontend Development
```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Features Implemented (Phase 1)

### Authentication & Authorization
- ✅ JWT-based authentication
- ✅ Role-based access control (8 user types)
- ✅ Protected API routes
- ✅ Audit logging for critical actions

### Location Management
- ✅ Area/Island model with PostGIS geometry support
- ✅ Building/Tower model
- ✅ Street/Zone model
- ✅ Seed data for sample Dummar islands

### Citizen Complaints
- ✅ Public complaint submission
- ✅ Tracking number generation
- ✅ Status tracking by tracking number + phone
- ✅ Image upload support
- ✅ Internal classification and assignment
- ✅ Status workflow (new → under_review → assigned → in_progress → resolved → rejected)

### Field Tasks
- ✅ Create tasks from complaints or directly
- ✅ Assignment to team/user
- ✅ Before/after photo upload
- ✅ Status tracking
- ✅ Activity timeline
- ✅ Link to complaints and/or contracts

### Contract Management
- ✅ Full CRUD operations
- ✅ Approval workflow with audit trail
- ✅ Status management (draft → under_review → approved → active → completed)
- ✅ Document upload
- ✅ QR code generation for verification
- ✅ PDF summary generation (basic)

### Dashboard
- ✅ Real-time statistics (complaints, tasks, contracts by status)
- ✅ Recent activity feeds
- ✅ Charts and metrics
- ✅ Map widget placeholder

### Reports
- ✅ Complaints summary with filters
- ✅ Tasks summary with filters
- ✅ Contracts summary with filters
- ✅ Export structure (CSV basic implementation)

## Frontend Pages

### Public Portal
- `/complaints/new` - Submit new complaint
- `/complaints/track` - Track complaint by number + phone

### Internal Portal (Authentication Required)
- `/login` - Login page
- `/dashboard` - Director dashboard
- `/complaints` - Complaints list
- `/complaints/:id` - Complaint details
- `/tasks` - Tasks list
- `/tasks/:id` - Task details
- `/contracts` - Contracts list
- `/contracts/:id` - Contract details
- `/locations` - Areas/Islands management
- `/users` - User management
- `/reports` - Reports page
- `/settings` - Settings

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **PostgreSQL** - Primary database
- **PostGIS** - Geospatial extension
- **Pydantic** - Data validation
- **Python-JOSE** - JWT tokens
- **Passlib** - Password hashing

### Frontend
- **React 19** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Shadcn UI** - Component library
- **React Hook Form** - Form handling
- **Zod** - Schema validation
- **Framer Motion** - Animations
- **Phosphor Icons** - Icon set

## Next Steps (Phase 2)

1. **Map Integration**
   - Integrate Leaflet/MapBox for interactive maps
   - Import real Dummar boundary data
   - Display complaints/tasks on map with clustering
   - Location picker for complaint submission

2. **Advanced Features**
   - Real-time notifications (WebSocket)
   - Email notifications for status changes
   - Advanced PDF reports with charts
   - Excel export for all reports
   - Batch operations (assign multiple tasks)

3. **Mobile App**
   - React Native app for field teams
   - Offline support for photo capture
   - GPS-based location tagging

4. **Analytics**
   - Performance metrics dashboard
   - Contractor performance tracking
   - Area-based heatmaps
   - Trend analysis

5. **Integration**
   - SMS gateway for citizen notifications
   - Government ID verification
   - Document scanning/OCR
   - Payment gateway for fees (if needed)

## Production Deployment

### Backend
```bash
# Build production image
docker build -t dummar-backend ./backend

# Run with production settings
docker run -e DATABASE_URL=... -e SECRET_KEY=... dummar-backend
```

### Frontend
```bash
# Build static assets
npm run build

# Serve with any static hosting (Nginx, Vercel, etc.)
```

### Database
- Use managed PostgreSQL (AWS RDS, Azure, etc.)
- Enable PostGIS extension
- Configure backups
- Set up replication for high availability

## License

Proprietary - Damascus Dummar Project

## Support

For technical support or questions, contact the development team.
