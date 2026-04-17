# Production Deployment Guide

دليل نشر منصة إدارة مشروع دمّر في بيئة الإنتاج

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [PostgreSQL / PostGIS Setup](#postgresql--postgis-setup)
3. [Environment Variables](#environment-variables)
4. [Backend Setup](#backend-setup)
5. [Database Migrations](#database-migrations)
6. [Seed Data Strategy](#seed-data-strategy)
7. [Frontend Build & Serve](#frontend-build--serve)
8. [SMTP Email Configuration](#smtp-email-configuration)
9. [CORS Configuration](#cors-configuration)
10. [File Upload / Storage](#file-upload--storage)
11. [Security Checklist](#security-checklist)
12. [CI/CD Pipeline](#cicd-pipeline)
13. [Rollback & Migration Caution](#rollback--migration-caution)
14. [Monitoring & Logging](#monitoring--logging)

---

## Prerequisites

| Component       | Minimum Version | Notes                                      |
|-----------------|-----------------|---------------------------------------------|
| Python          | 3.12+           | Required for backend                        |
| Node.js         | 18+             | Required for frontend build                 |
| PostgreSQL      | 15+             | Primary database                            |
| PostGIS         | 3.3+            | Extension for spatial/GIS data              |
| nginx (or similar) | latest      | Reverse proxy for production serving        |

---

## PostgreSQL / PostGIS Setup

### 1. Install PostgreSQL with PostGIS

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-15-postgis-3

# Or use Docker
docker run -d \
  --name dummar-db \
  -e POSTGRES_USER=dummar \
  -e POSTGRES_PASSWORD=<STRONG_PASSWORD> \
  -e POSTGRES_DB=dummar_db \
  -p 5432:5432 \
  postgis/postgis:15-3.3
```

### 2. Create database and enable PostGIS

```sql
CREATE DATABASE dummar_db;
\c dummar_db
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 3. Create a dedicated user

```sql
CREATE USER dummar WITH PASSWORD '<STRONG_PASSWORD>';
GRANT ALL PRIVILEGES ON DATABASE dummar_db TO dummar;
ALTER DATABASE dummar_db OWNER TO dummar;
```

---

## Environment Variables

Create a `.env` file in the `backend/` directory (never commit this file):

```bash
# ── Database ──
DATABASE_URL=postgresql://dummar:<PASSWORD>@localhost:5432/dummar_db

# ── Security ──
SECRET_KEY=<RANDOM_64_CHAR_STRING>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# ── File uploads ──
UPLOAD_DIR=/var/www/dummar/uploads

# ── CORS ──
CORS_ORIGINS=https://dummar.example.com

# ── SMTP (optional — set SMTP_ENABLED=true to activate email) ──
SMTP_ENABLED=false
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@dummar.gov.sy
SMTP_PASSWORD=<SMTP_PASSWORD>
SMTP_FROM_EMAIL=noreply@dummar.gov.sy
```

**Important:**
- `SECRET_KEY` must be a strong random string (at least 32 characters). Generate with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- Never use default passwords in production.
- `DATABASE_URL` must point to your production PostgreSQL.

For the frontend, create a `.env` file at the project root:

```bash
VITE_API_BASE_URL=https://api.dummar.example.com
```

---

## Backend Setup

### 1. Clone the repository

```bash
git clone <repo-url> /var/www/dummar
cd /var/www/dummar/backend
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `bcrypt==3.2.2` is pinned for `passlib==1.7.4` compatibility. Do not upgrade bcrypt without testing.

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with production values
```

### 5. Start the backend

For production, use Gunicorn with Uvicorn workers:

```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/dummar/access.log \
  --error-logfile /var/log/dummar/error.log
```

### 6. Create a systemd service (recommended)

```ini
# /etc/systemd/system/dummar-api.service
[Unit]
Description=Dummar Project API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/dummar/backend
Environment="PATH=/var/www/dummar/backend/venv/bin"
EnvironmentFile=/var/www/dummar/backend/.env
ExecStart=/var/www/dummar/backend/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable dummar-api
sudo systemctl start dummar-api
```

---

## Database Migrations

Alembic is used for database schema management.

### Run migrations

```bash
cd /var/www/dummar/backend
source venv/bin/activate
alembic upgrade head
```

### Check current migration version

```bash
alembic current
```

### Migration files

- `001_initial.py` — Core tables (users, areas, buildings, complaints, tasks, contracts, audit)
- `002_add_notifications.py` — Notifications table

### Creating new migrations

```bash
alembic revision --autogenerate -m "description of change"
alembic upgrade head
```

**Caution:** Always review auto-generated migrations before running in production. Test on a staging database first.

---

## Seed Data Strategy

### Initial seed (first deployment only)

```bash
cd /var/www/dummar/backend
python -m app.scripts.seed_data
```

This creates:
- 8 default users (with insecure default passwords — **change immediately**)
- 8 project areas (Dummar zones)
- 12 buildings
- 7 sample complaints
- 5 sample tasks
- 5 sample contracts

### Production strategy

1. **Run seed once** on first deployment to create admin users and areas
2. **Immediately change all passwords** via the UI or direct DB update
3. **Do not re-run seed** on subsequent deployments — it's idempotent for users but will duplicate other data
4. New areas/buildings should be added through the API or admin interface

### Changing default passwords

The system warns at startup if any accounts still use the default seed password (`password123`). Change passwords through:
- The `/settings` page in the UI
- Or direct API call: `PUT /users/{id}` with `password` field (requires project_director role)

---

## Frontend Build & Serve

### 1. Build the frontend

```bash
cd /var/www/dummar
npm install
VITE_API_BASE_URL=https://api.dummar.example.com npm run build
```

This produces a `dist/` directory with static files.

### 2. Serve with nginx

```nginx
# /etc/nginx/sites-available/dummar
server {
    listen 443 ssl http2;
    server_name dummar.example.com;

    ssl_certificate /etc/letsencrypt/live/dummar.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dummar.example.com/privkey.pem;

    # Frontend (SPA)
    root /var/www/dummar/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # File uploads
    location /uploads/ {
        alias /var/www/dummar/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

server {
    listen 80;
    server_name dummar.example.com;
    return 301 https://$server_name$request_uri;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dummar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## SMTP Email Configuration

Email notifications are optional and controlled by environment variables.

### Enable email

Set these variables in `.env`:

```bash
SMTP_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@dummar.gov.sy
SMTP_PASSWORD=<SMTP_PASSWORD>
SMTP_FROM_EMAIL=noreply@dummar.gov.sy
```

### Email notifications are sent for:

| Event                    | Recipients                              |
|--------------------------|-----------------------------------------|
| Complaint status change  | Assigned officer + complaints officers + project director |
| Task assignment          | Assigned user                           |
| Contract status change   | Contracts managers + project director   |

### Disable email

Set `SMTP_ENABLED=false` (default). The system will continue to create in-app notifications but skip email sending.

### Fail-safe behavior

- Email failures **never** block core operations
- All failures are logged with full stack traces
- If SMTP credentials are missing, the system logs an error and continues
- **Deduplication**: Same email (same recipient + subject) is suppressed within a 5-minute window to prevent noisy duplicate notifications
- **TLS handling**: Port 587 uses STARTTLS, port 465 uses direct SSL — automatic based on configured port
- **Timeout**: All SMTP connections timeout after 30 seconds

---

## CORS Configuration

CORS origins are read from the `CORS_ORIGINS` environment variable (comma-separated):

```bash
# Development
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Production
CORS_ORIGINS=https://dummar.example.com
```

**Important:** Do not use wildcard (`*`) in production. Only allow your frontend domain.

---

## File Upload / Storage

### Configuration

```bash
UPLOAD_DIR=/var/www/dummar/uploads
```

### Directory structure

```
uploads/
├── complaints/    # Citizen complaint attachments
├── tasks/         # Task before/after photos
├── contracts/     # Contract documents
└── general/       # Other uploads
```

### Considerations

- **Storage:** Ensure sufficient disk space. Consider mounting a separate volume.
- **Permissions:** The backend process needs write access to `UPLOAD_DIR`.
- **Backup:** Include `UPLOAD_DIR` in your backup strategy.
- **Allowed files:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.pdf` — max 10MB per file.
- **Public uploads:** The `/uploads/public` endpoint is rate-limited (10/min) and only accepts complaint images.
- **Serving files:** Serve via nginx `alias` for better performance (see nginx config above).

---

## Security Checklist

- [ ] **Change all seed passwords** before going live
- [ ] **Generate a strong `SECRET_KEY`** (at least 32 characters, random)
- [ ] **Configure `CORS_ORIGINS`** to only allow your production frontend domain
- [ ] **Enable HTTPS** with a valid SSL certificate (Let's Encrypt recommended)
- [ ] **Set `ACCESS_TOKEN_EXPIRE_MINUTES`** to a reasonable value (e.g., 480 = 8 hours)
- [ ] **Restrict database access** — only allow connections from the API server
- [ ] **Enable PostgreSQL SSL** for encrypted database connections
- [ ] **Review file upload limits** — current max is 10MB per file
- [ ] **Set up firewall** — only expose ports 80, 443 publicly
- [ ] **Run as non-root** — use a dedicated system user (e.g., `www-data`)
- [ ] **Back up database** — set up automated PostgreSQL backups (pg_dump)
- [ ] **Monitor logs** — set up log rotation and alerting

---

## CI/CD Pipeline

The project includes a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) that runs on push and pull request:

### Backend job
- Installs Python 3.12
- Installs dependencies from `backend/requirements.txt`
- Runs `pytest` with SQLite in-memory (no PostgreSQL needed)

### Frontend job
- Installs Node.js 18
- Runs `npm install` and `npm run build`

### Pipeline behavior
- Both jobs run in parallel
- CI fails if any test fails or if the frontend build fails
- Dependency caching is enabled for faster runs

### Running tests locally

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v

# Frontend
npm install
npm run build
```

---

## Rollback & Migration Caution

### Database migration rollback

```bash
# Downgrade one revision
alembic downgrade -1

# Downgrade to a specific revision
alembic downgrade <revision_id>

# Check history
alembic history
```

### Important warnings

1. **Always back up the database** before running migrations in production
2. **Test migrations** on a staging environment first
3. Some migrations may be **irreversible** (e.g., dropping columns with data)
4. If a migration fails mid-way, the database may be in an inconsistent state — restore from backup
5. **Do not** modify migration files after they have been applied to production

### Application rollback

1. Stop the backend service
2. Deploy the previous version of the code
3. Downgrade migrations if needed: `alembic downgrade -1`
4. Restart the backend service

---

## Monitoring & Logging

### Log locations (systemd setup)

```bash
# Application logs
journalctl -u dummar-api -f

# Gunicorn access/error logs
/var/log/dummar/access.log
/var/log/dummar/error.log

# nginx logs
/var/log/nginx/access.log
/var/log/nginx/error.log
```

### Health check endpoint

```bash
curl https://api.dummar.example.com/health
# Expected: {"status": "healthy"}
```

### Key things to monitor

- API response times
- Error rate (5xx responses)
- Database connection pool
- Disk space (especially upload directory)
- Email delivery failures (check application logs)
- SMTP connectivity

---

## Docker Deployment (Alternative)

For Docker-based deployment, use the included `docker-compose.yml` as a starting point:

```bash
# Build and start
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Load seed data
docker-compose exec backend python -m app.scripts.seed_data
```

**For production Docker deployment:**
- Override environment variables with production values
- Use Docker secrets or external secret management for sensitive values
- Mount persistent volumes for database and uploads
- Configure a reverse proxy (nginx/Traefik) in front of the containers
