# Production Deployment Guide

دليل نشر منصة إدارة مشروع دمّر في بيئة الإنتاج

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [PostgreSQL / PostGIS Setup](#postgresql--postgis-setup)
4. [Environment Variables](#environment-variables)
5. [Backend Setup](#backend-setup)
6. [Database Migrations](#database-migrations)
7. [Seed Data Strategy](#seed-data-strategy)
8. [Frontend Build & Serve](#frontend-build--serve)
9. [SMTP Email Configuration](#smtp-email-configuration)
10. [CORS Configuration](#cors-configuration)
11. [File Upload / Storage](#file-upload--storage)
12. [Tesseract OCR Setup (Contract Intelligence)](#tesseract-ocr-setup-contract-intelligence)
13. [Arabic PDF Export](#arabic-pdf-export)
14. [Security Checklist](#security-checklist)
15. [CI/CD Pipeline](#cicd-pipeline)
16. [Rollback & Migration Caution](#rollback--migration-caution)
17. [Monitoring & Observability](#monitoring--observability)
18. [Audit Trail](#audit-trail)
19. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Component       | Minimum Version | Notes                                      |
|-----------------|-----------------|---------------------------------------------|
| Python          | 3.12+           | Required for backend                        |
| Node.js         | 20+             | Required for frontend build (Vite 8 + Tailwind 4) |
| PostgreSQL      | 15+             | Primary database                            |
| PostGIS         | 3.3+            | Extension for spatial/GIS data              |
| nginx (or similar) | latest      | Reverse proxy for production serving        |
| Docker (optional) | 20+           | For containerized deployment                |

---

## Quick Start (Docker)

The fastest way to deploy uses Docker Compose:

```bash
# 1. Clone the repository
git clone <repo-url> /var/www/dummar
cd /var/www/dummar

# 2. Create a production .env file (critical: change defaults!)
cat > .env <<EOF
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
CORS_ORIGINS=https://dummar.example.com
SMTP_ENABLED=false
LOG_LEVEL=info
ACCESS_TOKEN_EXPIRE_MINUTES=480
EOF

# 3. Build and start
docker compose up -d

# 4. Run migrations
docker compose exec backend alembic upgrade head

# 5. Load initial seed data (first deployment only)
docker compose exec backend python -m app.scripts.seed_data

# 6. Verify health
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/health/ready

# 7. IMPORTANT: Change default passwords immediately!
```

The `docker-compose.yml` includes:
- Health checks for both PostgreSQL and backend
- Automatic restart on failure
- Environment variable overrides via `.env` file
- Persistent volumes for database and uploads
- Non-root container user for backend

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

# ── Logging ──
LOG_LEVEL=info  # debug, info, warning, error

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
pip install gunicorn
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
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --timeout 120
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
  --bind 127.0.0.1:8000 \
  --access-logfile - \
  --error-logfile - \
  --timeout 120
Restart=always
RestartSec=5

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
- `003_add_task_coordinates.py` — Task lat/lng columns for GIS
- `004_add_area_boundary_data.py` — Area boundary polygon data
- `005_add_audit_log_indexes.py` — Performance indexes on audit_logs

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

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

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
        proxy_read_timeout 120s;
    }

    # File uploads
    location /uploads/ {
        alias /var/www/dummar/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # PWA service worker — no caching
    location /sw.js {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
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

### Verifying SMTP after configuration

```bash
# 1. Test SMTP connection (requires internal staff auth)
curl -H "Authorization: Bearer <TOKEN>" https://api.dummar.example.com/health/smtp

# 2. Check SMTP in detailed health
curl https://api.dummar.example.com/health/detailed

# 3. Send a real test email (requires auth + SMTP_ENABLED=true)
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"to_email": "admin@your-domain.com"}' \
  https://api.dummar.example.com/health/smtp/test-send

# 4. Watch logs for email send results
journalctl -u dummar-api -f | grep -i email
```

### SMTP Production Verification Checklist

Before considering SMTP fully operational in production, verify all of the following:

- [ ] `SMTP_ENABLED=true` in environment
- [ ] `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` are configured
- [ ] `GET /health/smtp` returns `status: "ok"` with acceptable latency
- [ ] `GET /health/detailed` shows SMTP status as `"ok"` (not `"error"` or `"disabled"`)
- [ ] `POST /health/smtp/test-send` successfully delivers an email to a test mailbox
- [ ] Check spam/junk folder if test email is not in inbox
- [ ] Trigger a real workflow that sends email:
  - Change a complaint status → verify email reaches complaints officer
  - Assign a task → verify email reaches assigned user
  - Approve a contract → verify email reaches contracts managers
- [ ] Confirm emails are rendered correctly (Arabic RTL, proper formatting)
- [ ] Confirm duplicate suppression works (repeat same action within 5 min, verify only 1 email sent)
- [ ] Review application logs for any SMTP errors: `journalctl -u dummar-api | grep -i smtp`
- [ ] Verify that SMTP failures do NOT block core operations (temporarily misconfigure SMTP and confirm complaints/tasks/contracts still work)

### Disable email

Set `SMTP_ENABLED=false` (default). The system will continue to create in-app notifications but skip email sending.

### Fail-safe behavior

- Email failures **never** block core operations
- All failures are logged with full stack traces
- If SMTP credentials are missing, the system logs an error and continues
- **Deduplication**: Same email (same recipient + subject) is suppressed within a 5-minute window to prevent noisy duplicate notifications
- **TLS handling**: Port 587 uses STARTTLS, port 465 uses direct SSL — automatic based on configured port
- **Timeout**: All SMTP connections timeout after 30 seconds
- **Return value**: `send_email()` returns `True`/`False` for programmatic verification

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

## Tesseract OCR Setup (Contract Intelligence)

The Contract Intelligence module includes OCR capabilities for processing scanned contract documents. The system supports two engines:

### Engine Architecture

| Engine | Description | Requirements |
|--------|-------------|-------------|
| **BasicTextExtractor** | Extracts text from PDFs (text layer), TXT, CSV files | Always available |
| **TesseractEngine** | Full OCR for scanned images (JPG, PNG, TIFF, BMP) and image-only PDFs | `tesseract-ocr` binary + `pytesseract` Python package |

The system **automatically detects** which engine is available at startup and falls back gracefully.

### Docker Deployment (Recommended)

The Dockerfile already installs Tesseract with Arabic and English language support:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    poppler-utils
```

**No additional configuration is needed** for Docker deployments.

### Bare Metal / VM Deployment

```bash
# Ubuntu/Debian
sudo apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng poppler-utils

# Verify installation
tesseract --version
tesseract --list-langs  # Should include: ara, eng

# Python package (already in requirements.txt)
pip install pytesseract
```

### Production Verification Steps

1. **Check OCR status via API** (requires contracts_manager or project_director auth):
   ```bash
   curl -H "Authorization: Bearer <token>" \
     https://your-domain/api/contract-intelligence/ocr-status
   ```
   Expected response when Tesseract is available:
   ```json
   {
     "engine": "tesseract",
     "tesseract_available": true,
     "supported_formats": {
       "always": ["pdf (text-layer)", "txt", "csv"],
       "with_tesseract": ["jpg", "jpeg", "png", "tiff", "tif", "bmp"],
       "with_pdf2image": ["pdf (scanned/image-only)"]
     }
   }
   ```

2. **Check health in admin UI**: The Intelligence Reports page shows OCR engine status with a ✅/❌ indicator.

3. **Verify inside Docker container**:
   ```bash
   docker exec -it <backend-container> tesseract --version
   docker exec -it <backend-container> python -c "from app.services.ocr_service import get_ocr_status; print(get_ocr_status())"
   ```

### Graceful Fallback Behavior

- If Tesseract is **not installed**, the system uses BasicTextExtractor
- Text-based documents (PDF with text layer, TXT, CSV) are always processed correctly
- Image uploads will return a clear warning message but will not crash
- CI tests pass without Tesseract installed (tests handle `is_tesseract_available()` check)
- The frontend OCR status indicator shows "❌ غير متوفر" (Not available) clearly

### Troubleshooting OCR

| Issue | Solution |
|-------|---------|
| `tesseract_available: false` in Docker | Rebuild image: `docker-compose build --no-cache backend` |
| Arabic text not recognized | Verify `tesseract-ocr-ara` is installed: `tesseract --list-langs` |
| Image-only PDFs not OCR'd | Install `poppler-utils` for `pdf2image` support |
| Low OCR confidence | Check scan quality — 300 DPI minimum recommended |
| Memory issues with large PDFs | Increase `GUNICORN_TIMEOUT` and container memory limits |

### Tesseract Production Verification Checklist

Before considering OCR fully operational in production, verify all of the following:

- [ ] `GET /contract-intelligence/ocr-status` returns `"engine": "tesseract"` and `"tesseract_available": true`
- [ ] `tesseract_languages` list includes `ara` and `eng`
- [ ] Backend startup logs show `Tesseract OCR: tesseract X.X.X` (check via `docker compose logs backend | grep Tesseract`)
- [ ] Upload a test Arabic scanned image (JPG/PNG) — verify text extraction succeeds
- [ ] Upload a test text-layer PDF — verify text extraction succeeds
- [ ] Verify fallback: stop Tesseract (`docker exec backend apt-get remove tesseract-ocr`) → confirm text extraction still works for PDFs/TXT via BasicTextExtractor → reinstall
- [ ] `GET /health/ready` returns 200 regardless of Tesseract availability

---

## Arabic PDF Export

PDF export for contract intelligence reports now uses **DejaVu Sans** TTF font with **arabic-reshaper** and **python-bidi** for proper Arabic rendering.

### How it works

1. **Font**: DejaVu Sans (`fonts-dejavu-core` package) is installed in the Docker image and registered with reportlab as a TTF font
2. **Text shaping**: `arabic-reshaper` joins Arabic letters correctly (isolated → connected forms)
3. **Bidi**: `python-bidi` handles right-to-left text ordering for mixed Arabic/English content
4. **Fallback**: If DejaVu Sans or bidi packages are not available, the system falls back to Helvetica (English-only rendering)

### Verification

```bash
# 1. Check font availability in Docker
docker exec <backend-container> ls /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

# 2. Check Python packages
docker exec <backend-container> python -c "import arabic_reshaper; from bidi.algorithm import get_display; print('OK')"

# 3. Export a PDF report (requires contracts_manager or project_director auth)
curl -H "Authorization: Bearer <token>" \
  https://your-domain/api/contract-intelligence/reports/export/pdf -o report.pdf

# 4. Export a single document record
curl -H "Authorization: Bearer <token>" \
  https://your-domain/api/contract-intelligence/documents/1/export/pdf -o document_1.pdf

# 5. Open the PDF and verify Arabic text is correctly shaped and readable
```

### Troubleshooting

| Issue | Solution |
|-------|---------|
| Arabic text shows as boxes/tofu | Verify `fonts-dejavu-core` is installed in Docker image |
| Arabic letters not joined | Verify `arabic-reshaper` is installed: `pip list \| grep arabic` |
| Text direction wrong | Verify `python-bidi` is installed: `pip list \| grep bidi` |
| PDF export fails | Check backend logs: `docker compose logs backend \| grep PDF` |

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
- [ ] **Review audit logs** — check `/audit-logs/` regularly for suspicious activity

---

## CI/CD Pipeline

The project includes a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) that runs on push and pull request:

### Backend job
- Installs Python 3.12
- Installs dependencies from `backend/requirements.txt`
- Runs `pytest` with SQLite in-memory (no PostgreSQL needed)

### Frontend job
- Installs Node.js 20 (required for Vite 8 + Tailwind CSS 4)
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

## Monitoring & Observability

### Health Endpoints

| Endpoint            | Auth Required | Purpose                                         |
|---------------------|---------------|--------------------------------------------------|
| `GET /health`       | No            | Basic liveness probe (returns `{"status":"healthy"}`) |
| `GET /health/detailed` | No         | Checks DB + SMTP connectivity with latency      |
| `GET /health/ready` | No            | Readiness probe — returns 503 if DB unreachable  |
| `GET /health/smtp`  | Yes (staff)   | Tests SMTP connection + authentication           |
| `GET /metrics`      | No            | Uptime, request counts, version info             |

### Structured Request Logging

All API requests are logged with structured key=value format:

```
method=GET path="/complaints/" status=200 duration_ms=12.3 client=192.168.1.1
```

- Health check paths (`/health`, `/health/detailed`, `/docs`) are excluded to reduce noise
- 4xx and 5xx responses are logged at WARNING level
- Audit events are logged at INFO level with action details

### Log locations (systemd setup)

```bash
# Application logs (structured format)
journalctl -u dummar-api -f

# Filter by component
journalctl -u dummar-api | grep "dummar.audit"      # Audit events
journalctl -u dummar-api | grep "dummar.requests"    # Request logs
journalctl -u dummar-api | grep "email"              # Email send results

# nginx logs
/var/log/nginx/access.log
/var/log/nginx/error.log
```

### Setting up external monitoring

```bash
# Example: Simple cron-based health check with alerting
*/5 * * * * curl -sf http://localhost:8000/health/ready || echo "ALERT: Dummar API not ready" | mail -s "Dummar Health Alert" admin@example.com

# Example: Prometheus-compatible scraping (metrics endpoint)
curl http://localhost:8000/metrics
# Returns: {"uptime_seconds": 3600.5, "total_requests": 1234, "error_requests": 2, "version": "1.0.0"}
```

### Key things to monitor

- API response times (from request logs)
- Error rate (5xx responses — logged at WARNING level)
- Database connectivity (via `/health/ready`)
- SMTP connectivity (via `/health/detailed`)
- Disk space (especially upload directory)
- Email delivery failures (check application logs for "Failed to send email")
- Audit log for unusual activity (`/audit-logs/` endpoint)
- Application uptime (`/metrics` endpoint)

### Log level configuration

Set `LOG_LEVEL` environment variable:
- `debug` — verbose output, useful for development
- `info` — normal production level (default)
- `warning` — only warnings and errors
- `error` — errors only

---

## Audit Trail

The platform maintains a comprehensive audit trail for operational accountability.

### Audited events

| Action                     | Entity Type | Description                           |
|----------------------------|-------------|---------------------------------------|
| `login`                    | user        | User authentication (with IP/UA)      |
| `user_create`              | user        | New user created (includes role)       |
| `user_update`              | user        | User profile/role updated (with diff)  |
| `user_deactivate`          | user        | User account deactivated               |
| `complaint_update`         | complaint   | Complaint modified                     |
| `complaint_status_change`  | complaint   | Status transition (old → new)          |
| `complaint_assignment`     | complaint   | Assignment changed (officer → officer) |
| `task_create`              | task        | Task created                           |
| `task_update`              | task        | Task modified                          |
| `task_status_change`       | task        | Status transition                      |
| `task_assignment`          | task        | Assignment changed                     |
| `task_delete`              | task        | Task deleted                           |
| `contract_create`          | contract    | Contract created                       |
| `contract_update`          | contract    | Contract modified                      |
| `contract_approve`         | contract    | Contract approved                      |
| `contract_activate`        | contract    | Contract activated                     |
| `contract_suspend`         | contract    | Contract suspended                     |
| `contract_cancel`          | contract    | Contract cancelled                     |
| `contract_delete`          | contract    | Contract deleted                       |

### Reviewing audit logs

```bash
# Via API (requires project_director auth)
curl -H "Authorization: Bearer <TOKEN>" \
  "https://api.dummar.example.com/audit-logs/?limit=50&entity_type=user"

# Filter options: action, entity_type, user_id
# Pagination: skip, limit (max 200)
```

### Each audit record includes:
- **user_id** — who performed the action
- **action** — what was done
- **entity_type** + **entity_id** — which record was affected
- **description** — human-readable summary
- **ip_address** — source IP of the request
- **user_agent** — browser/client info
- **created_at** — timestamp

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
journalctl -u dummar-api -n 50 --no-pager

# Common issues:
# 1. DATABASE_URL incorrect → check connection string
# 2. SECRET_KEY not set → add to .env
# 3. Port 8000 already in use → check with: ss -tlnp | grep 8000
# 4. Python dependencies missing → pip install -r requirements.txt
```

### Database connection fails

```bash
# Test connection
psql postgresql://dummar:<password>@localhost:5432/dummar_db -c "SELECT 1"

# Check readiness endpoint
curl http://localhost:8000/health/ready
```

### Emails not sending

```bash
# 1. Check if SMTP is enabled
curl http://localhost:8000/health/detailed | python3 -m json.tool

# 2. Test SMTP connection (requires auth)
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/health/smtp

# 3. Check logs for send failures
journalctl -u dummar-api | grep -i "email\|smtp" | tail -20

# Common issues:
# - SMTP_ENABLED=false (default — must explicitly enable)
# - SMTP credentials incorrect
# - Firewall blocking outbound port 587/465
# - TLS/SSL certificate issues
```

### Frontend build fails

```bash
# Ensure Node.js 20+
node --version

# Clean install
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## Docker Deployment (Primary)

The recommended production deployment uses `docker-compose.yml` with three services: **db** (PostgreSQL), **backend** (FastAPI), and **nginx** (reverse proxy):

```bash
# 1. Clone and configure
git clone <repo-url> /var/www/dummar
cd /var/www/dummar

# 2. Create production .env
cat > .env <<EOF
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
CORS_ORIGINS=https://dummar.example.com
SMTP_ENABLED=false
LOG_LEVEL=info
GUNICORN_WORKERS=4
EOF

# 3. Build frontend (dist/ directory)
npm install
VITE_API_BASE_URL=/api npm run build

# 4. Build and start all services
docker compose up -d --build

# 5. Load seed data (first deployment only)
docker compose exec backend python -m app.scripts.seed_data

# 6. Verify
curl http://localhost/api/health/ready
curl http://localhost/api/health/detailed

# 7. View logs
docker compose logs -f backend
```

**The `docker-compose.yml` includes:**
- PostgreSQL with PostGIS (persistent volume)
- Backend with auto-migration on startup (entrypoint.sh)
- nginx reverse proxy with rate limiting (API, auth, uploads), security headers, gzip, SPA routing
- Health checks for all services
- Automatic restart on failure
- Non-root container user for backend
- Memory limits per service (db: 512M, backend: 1G, nginx: 128M)
- Tesseract OCR with Arabic support (verified at startup)
- Arabic PDF export with DejaVu Sans font

**Important Docker notes:**
- Backend entrypoint auto-runs `alembic upgrade head` on every start
- nginx serves frontend from `dist/` and proxies API to backend
- Override environment variables via `.env` file
- Use Docker secrets or external secret management for sensitive values
- `GUNICORN_WORKERS` configures backend concurrency (default 4)

---

## Load / Performance Testing

A lightweight load testing tool is included for verifying system performance.

### Running load tests

```bash
cd backend

# Against local Docker deployment
python -m tests.load_test --base-url http://localhost:8000

# Against production (behind nginx)
python -m tests.load_test --base-url https://api.dummar.example.com --username admin --password <password>

# With more concurrency and report output
python -m tests.load_test --base-url http://localhost:8000 --concurrency 20 --requests-per-endpoint 100 --report-file results.json
```

### What it tests

| Endpoint | Auth | Purpose |
|---|---|---|
| GET /health | No | Liveness probe latency |
| GET /health/ready | No | Readiness probe latency |
| GET /metrics | No | Metrics endpoint latency |
| POST /auth/login | No | Authentication throughput |
| GET /complaints/ | Yes | Main data listing |
| GET /tasks/ | Yes | Task listing |
| GET /contracts/ | Yes | Contract listing |
| GET /dashboard/stats | Yes | Dashboard aggregation |

### Output

The tool outputs a table with avg/p95/min/max response times, error counts, and requests-per-second for each endpoint. Optionally writes a JSON report for tracking over time.

### Key performance expectations

- Health/metrics endpoints: < 10ms average
- Login: < 100ms average
- List endpoints: < 200ms average (with < 1000 records)
- Dashboard stats: < 300ms average (aggregation queries)

If any endpoint exceeds 500ms average, investigate database query performance and consider adding indexes.
