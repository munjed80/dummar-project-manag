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
15. [SSL/TLS Setup with Let's Encrypt](#ssltls-setup-with-lets-encrypt)
16. [CI/CD Pipeline](#cicd-pipeline)
17. [Rollback & Migration Caution](#rollback--migration-caution)
18. [Monitoring & Observability](#monitoring--observability)
19. [Audit Trail](#audit-trail)
20. [Troubleshooting](#troubleshooting)
21. [Docker Deployment (Primary)](#docker-deployment-primary)
22. [Load / Performance Testing](#load--performance-testing)
23. [VPS Deployment Checklist](#vps-deployment-checklist)

---

## Prerequisites

The recommended deployment path is **Docker Compose on a single Ubuntu VPS**. With this path, only Docker, Docker Compose v2, and Node.js need to be installed on the host. PostgreSQL/PostGIS and nginx run inside containers.

| Component | Required on host? | Where it runs | Notes |
|-----------|------------------|---------------|-------|
| Docker Engine 20+ | **yes** | host | Runs all three services |
| Docker Compose v2 | **yes** | host | `docker compose` plugin (or standalone) |
| Node.js 20+ + npm | **yes** | host | Frontend is built on the host (`npm run build` → `./dist`), then bind-mounted into the nginx container. There is no frontend Dockerfile yet. |
| Certbot | optional | host | Only needed if you use the bundled `ssl-setup.sh` (Let's Encrypt). Skip if you terminate TLS upstream. |
| `git`, `curl`, `openssl`, `dig` | yes | host | Used by `deploy.sh` and `ssl-setup.sh` |
| PostgreSQL 15 + PostGIS 3.3 | **no** | container (`postgis/postgis:15-3.3`) | Do NOT install on the host. |
| nginx | **no** | container (`nginx:alpine`) | Do NOT install host nginx — it would conflict with the container on port 80. |
| Python 3.12 | **no** | container (`python:3.12-slim`) | Backend ships with Tesseract OCR + Arabic fonts pre-installed. |

If you choose the manual (non-Docker) path described later in this guide, then PostgreSQL, Python, and nginx must be installed on the host. That path is **not** the default and is intended only for advanced operators.

---

## Quick Start (Docker)

The fastest path uses `deploy.sh`, which does pre-flight checks, generates a safe `.env` with strong random secrets if one is missing, builds the frontend, brings up the stack, and waits for health checks.

```bash
# 1. Clone the repository
git clone <repo-url> /var/www/dummar
cd /var/www/dummar

# 2. First deployment WITH seed data and your domain
./deploy.sh --seed --domain=dummar.example.com

# 3. Retrieve the generated seed credentials and distribute them securely.
docker compose exec backend cat /tmp/seed_credentials.txt
docker compose exec backend rm  /tmp/seed_credentials.txt   # delete after distribution
```

If you prefer to run Compose directly:

```bash
# 2a. Create a .env file (REQUIRED — the stack will refuse to start without
#     DB_PASSWORD and SECRET_KEY)
cat > .env <<EOF
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=https://dummar.example.com
ENVIRONMENT=production
ENABLE_API_DOCS=false
BACKEND_BIND=127.0.0.1
SMTP_ENABLED=false
LOG_LEVEL=info
EOF

# 2b. Build the frontend (required — nginx serves ./dist as a bind mount)
npm ci && npm run build

# 2c. Start the stack
docker compose up -d
```

The compose stack:

- Refuses to start if `DB_PASSWORD` or `SECRET_KEY` is missing from `.env`.
- Binds the backend to `127.0.0.1:8000` (override only with `BACKEND_BIND=0.0.0.0`).
- Does NOT publish the database port.
- Auto-runs `alembic upgrade head` on backend container start; **fails fatally** if migrations fail.
- Configures `json-file` log rotation (10 MB × 5 files) on every service.
- Disables the Swagger UI / ReDoc / OpenAPI schema unless `ENABLE_API_DOCS=true`.

After deploy, verify:

```bash
curl http://localhost/api/                       # public API root
curl http://localhost/api/health                 # public liveness
curl http://localhost/api/health/ready           # public readiness
# /api/health/detailed and /api/metrics now require an authenticated
# internal-staff JWT — they no longer return data anonymously.
```

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
docker compose exec backend python -m app.scripts.seed_data
```

This creates:
- 8 default users — each with a **strong random per-user password** (24 URL-safe chars)
- 8 project areas (Dummar zones)
- 12 buildings
- 7 sample complaints
- 5 sample tasks
- 5 sample contracts

The generated passwords are written to `/tmp/seed_credentials.txt` inside the
backend container (file permissions 600). Retrieve and distribute them through
a secure channel, then delete the file:

```bash
docker compose exec backend cat /tmp/seed_credentials.txt
docker compose exec backend rm  /tmp/seed_credentials.txt
```

If the credentials file cannot be written (e.g. permission denied), the script
**raises a RuntimeError** and exits non-zero. It never falls back to printing
the credentials to stdout, because that would leak them into container /
journald / aggregator logs. Fix the path/permissions and re-run; you can also
override the destination with `SEED_CREDENTIALS_FILE=/some/writable/path`.

### Test / development workflow only

If you need the legacy fixed `password123` for every account (e.g. to run
existing test suites or local dev fixtures), opt in explicitly:

```bash
docker compose exec backend python -m app.scripts.seed_data --force-default-passwords
# or:
SEED_DEFAULT_PASSWORDS=1 docker compose exec backend python -m app.scripts.seed_data
```

Do NOT use this mode in production. The application logs a security warning at
startup whenever any account is still using `password123`.

### Production strategy

1. **Run seed once** on first deployment to create operator users, areas, and sample data
2. **Distribute generated passwords** securely; force first-login rotation
3. **Delete `seed_credentials.txt`** from the backend container
4. **Do not re-run seed** on subsequent deployments — it is idempotent for users
   (it will only generate passwords for newly created accounts, not for existing ones)
5. New areas/buildings/users should be added through the API or admin UI

### Changing passwords later

The system logs a security warning at startup if any accounts still use the
legacy `password123`. Change passwords through:
- The `/settings` page in the UI
- Or `PUT /users/{id}` with the `password` field (requires project_director role)

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
UPLOAD_DIR=/app/uploads          # inside the backend container
                                 # backed by the named volume `backend_uploads`
                                 # also mounted read-only into nginx at /usr/share/nginx/uploads
```

### Directory structure and access policy

```
uploads/
├── complaints/             # PUBLIC — citizen complaint attachments
├── profiles/               # PUBLIC — profile photos
├── general/                # PUBLIC — generic attachments
├── tasks/                  # PUBLIC — task photos
├── contracts/              # PRIVATE — contract documents (auth required)
└── contract_intelligence/  # PRIVATE — OCR-processed contract documents (auth required)
```

**Public** categories are served by nginx as static files for performance.
Filenames are random UUIDs (`uuid4().hex`), which provides unguessability
but is **not** authorization. Do not put confidential data in these folders.

**Private** categories are NOT served as static files. nginx is configured
to proxy `/uploads/contracts/*` and `/uploads/contract_intelligence/*` to the
backend, where `app.api.uploads` enforces `get_current_internal_user` before
returning the file. Anonymous requests get 401/403.

This split is enforced in two places — change both if you adjust it:

- `backend/app/api/uploads.py` (`PUBLIC_CATEGORIES`, `SENSITIVE_CATEGORIES`)
- `nginx.conf` and `nginx-ssl.conf` (`location ~ ^/uploads/(contracts|contract_intelligence)/`)

The unauthenticated `app.mount("/uploads", StaticFiles)` mount that previously
existed in `app/main.py` has been **removed**; all file access now goes
through the explicit handlers above.

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

### Built-in production hardening (verified — no operator action required)

These are now enforced by the Docker stack and code defaults; you get them for free:

- [x] Backend bound to `127.0.0.1:8000` — nginx is the only public entry point
- [x] Database port not published
- [x] `DB_PASSWORD` and `SECRET_KEY` are required in `.env` (compose uses `${VAR:?}`)
- [x] `deploy.sh` refuses to launch with the legacy default values
- [x] `/docs`, `/redoc`, `/openapi.json` disabled when `ENVIRONMENT=production`
- [x] `/health/detailed`, `/health/smtp`, `/health/ocr`, `/metrics` require internal-staff auth
- [x] `/uploads/contracts/*` and `/uploads/contract_intelligence/*` require auth (proxied to backend)
- [x] `alembic upgrade head` failure is fatal (container exits non-zero)
- [x] Docker `json-file` log rotation (10 MB × 5) on every service
- [x] Seed accounts get strong random per-user passwords (legacy `password123` is opt-in only)
- [x] Backend container runs as non-root user `appuser`
- [x] Rate limits at both app (slowapi) and nginx (`api_limit`, `auth_limit`, `upload_limit`)

### Operator must-do before exposing publicly

- [ ] Run `./deploy.sh --seed` (or seed manually) and securely retrieve `seed_credentials.txt`
- [ ] Distribute the random passwords via a secure channel; force first-login rotation
- [ ] Delete `/tmp/seed_credentials.txt` from the backend container
- [ ] Set `CORS_ORIGINS` to ONLY your real https origin (deploy.sh does this with `--domain`)
- [ ] Enable HTTPS via `./ssl-setup.sh <domain> --auto`
- [ ] Open only ports 22, 80, 443 in `ufw`; set up `fail2ban` for SSH and `/api/auth/`
- [ ] Configure recurring `pg_dump` backups of the `db` container volume
- [ ] If SMTP is needed, test with `POST /health/smtp/test-send` before relying on notifications
- [ ] Rotate SSH keys, disable root login, disable password SSH

### Optional fail2ban (Ubuntu)

```bash
sudo apt install -y fail2ban
sudo tee /etc/fail2ban/jail.d/dummar.local <<'EOF'
[sshd]
enabled = true
maxretry = 4
bantime = 1h

# Optional: ban IPs that hammer /api/auth/login.
# Requires nginx access logs to be readable by fail2ban.
[nginx-dummar-auth]
enabled = false
filter = nginx-dummar-auth
logpath = /var/lib/docker/containers/*/*.log
maxretry = 10
findtime = 5m
bantime = 1h
EOF
sudo systemctl restart fail2ban
```

### Daily PostgreSQL backup snippet

```bash
sudo tee /etc/cron.daily/dummar-pgdump <<'EOF'
#!/bin/sh
set -e
BACKUP_DIR=/var/backups/dummar
mkdir -p "$BACKUP_DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
docker compose -f /var/www/dummar/docker-compose.yml exec -T db \
    pg_dump -U dummar dummar_db | gzip > "$BACKUP_DIR/dummar-$TS.sql.gz"
# Keep last 14 days
find "$BACKUP_DIR" -type f -name 'dummar-*.sql.gz' -mtime +14 -delete
EOF
sudo chmod +x /etc/cron.daily/dummar-pgdump
```

Restore:

```bash
gunzip -c /var/backups/dummar/dummar-<TS>.sql.gz \
  | docker compose -f /var/www/dummar/docker-compose.yml exec -T db psql -U dummar dummar_db
```

---

## SSL/TLS Setup with Let's Encrypt

The project includes ready-to-use scripts and configuration for securing the platform with HTTPS.

### Prerequisites

1. A registered domain name (e.g., `dummar.example.com`)
2. An A record pointing the domain to your server's public IP
3. Port 80 and 443 open in your firewall
4. `certbot` installed on the server

### Quick Setup (recommended — `--auto` flow)

```bash
# 1. Install certbot on the host
sudo apt update && sudo apt install -y certbot

# 2. Ensure DNS is configured (A record → your server IP)
dig +short dummar.example.com  # should show your server IP

# 3. Obtain the cert AND auto-configure nginx, docker-compose, and .env
sudo ./ssl-setup.sh dummar.example.com --auto
```

That single `--auto` command does ALL of the following for you:
- Stops nginx briefly, runs `certbot --standalone` to get the cert
- Copies `nginx-ssl.conf` → `nginx.conf` and replaces `DOMAIN_PLACEHOLDER`
- Updates `CORS_ORIGINS` in `.env` to `https://<domain>`
- Adds a daily renewal cron job (`certbot renew` at 03:00) that reloads nginx
- Restarts the nginx container with the new SSL config

The Let's Encrypt certificate volumes (`/etc/letsencrypt`, `/var/www/certbot`)
are **already mounted unconditionally** by `docker-compose.yml` — there is
nothing to uncomment. Once the cert exists at the standard path, the next
`nginx` container restart picks it up.

After this, the standard update flow is:

```bash
git pull
./deploy.sh --rebuild --domain=dummar.example.com
```

`deploy.sh` is **SSL self-healing**: when it detects a Let's Encrypt cert
exists for the domain but the on-disk `nginx.conf` is the HTTP-only repo
template (because `git pull` overwrote it), it automatically re-applies
`nginx-ssl.conf`. You will not silently lose HTTPS after a `git pull`.

> **About the cert detection (non-root deploys).** `/etc/letsencrypt/{live,archive}`
> are typically `0700 root:root`. An earlier version of the self-heal used
> a plain `[ -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]` test, which
> silently returned false when `deploy.sh` was run by an unprivileged
> deploy user (the standard pattern — only docker-socket access is
> needed). The self-heal was then skipped, `nginx.conf` stayed HTTP-only,
> nothing inside the container listened on 443, docker-proxy reset every
> connection on 443, and `curl -k -I https://localhost` failed with
> `SSL_SYSCALL` (Cloudflare in turn returned 521). The current
> implementation falls back to a tiny `docker run` against the existing
> `nginx:alpine` image — the docker daemon runs as root via the socket,
> so the cert is detected reliably regardless of who runs `deploy.sh`.

### Verifying HTTPS after a deploy

`deploy.sh` now runs an **origin TLS probe** as part of its post-deploy
verification whenever `nginx.conf` contains `listen 443 ssl`:

```bash
curl -sk -o /dev/null -w '%{http_code}' https://localhost/
```

If this returns `000` (curl could not complete the handshake) the deploy
is marked failed. This is the canonical local acceptance test — it bypasses
Cloudflare entirely and exercises the origin TLS stack directly. You can
re-run it manually at any time:

```bash
curl -k -I https://localhost          # origin TLS handshake
curl -I  http://localhost             # HTTP→HTTPS redirect (or SPA on HTTP-only)
curl -I  https://your-domain.example  # public path (through Cloudflare)
```

### Manual setup (advanced — only if `--auto` is unsuitable)

If you need to run the steps individually (e.g. webroot mode, or you
already have a cert):

```bash
sudo ./ssl-setup.sh dummar.example.com           # cert only, no auto-config
cp nginx-ssl.conf nginx.conf
sed -i 's/DOMAIN_PLACEHOLDER/dummar.example.com/g' nginx.conf
sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://dummar.example.com|' .env
docker compose up -d --build nginx
```

### Files Provided

| File | Purpose |
|------|---------|
| `ssl-setup.sh` | Automated Let's Encrypt certificate acquisition + renewal setup |
| `nginx-ssl.conf` | Production SSL nginx config (copy to `nginx.conf` after setup) |
| `nginx.conf` | Default HTTP-only config (used before SSL is set up) |

### SSL Configuration Details

The `nginx-ssl.conf` includes:
- TLS 1.2 and 1.3 only (no legacy protocols)
- Strong cipher suites (CHACHA20, AES-GCM)
- HSTS header (Strict-Transport-Security) with 2-year max-age
- OCSP stapling for faster TLS handshakes
- HTTP → HTTPS redirect on port 80
- Let's Encrypt ACME challenge path for certificate renewal
- All existing rate limiting, security headers, and proxy rules

### Certificate Renewal

The `ssl-setup.sh` script sets up automatic renewal via cron:
- Runs daily at 03:00 via `certbot renew`
- Automatically reloads nginx after renewal
- Logged to `/var/log/letsencrypt-renew.log`

To test renewal manually:
```bash
sudo certbot renew --dry-run
```

### DNS Requirements

Before running `ssl-setup.sh`, ensure your domain's DNS is configured:

| Record Type | Name | Value |
|-------------|------|-------|
| A | `dummar.example.com` | `<your-server-ip>` |

DNS propagation can take up to 48 hours. Verify with:
```bash
dig +short dummar.example.com
```

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
| `GET /health/ocr`   | Yes (staff)   | OCR engine status + Arabic text verification     |
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

The recommended production deployment uses `docker-compose.yml` with three services: **db** (PostgreSQL), **backend** (FastAPI), and **nginx** (reverse proxy).

### Automated Deployment

Use the included `deploy.sh` script for streamlined deployment:

```bash
# First-time deployment with seed data
./deploy.sh --seed

# Update existing deployment
./deploy.sh

# Force rebuild all images
./deploy.sh --rebuild
```

The script handles:
- Pre-flight checks (Docker, Compose, Node.js)
- `.env` generation with random secrets (if missing)
- Frontend build (`npm ci && npm run build`)
- Docker image build and service startup
- Health check verification
- Seed data loading (first deployment only)

### Manual Deployment

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

---

## VPS Deployment Checklist

Use this checklist when deploying to a new VPS for the first time:

### Server Preparation

- [ ] Ubuntu 22.04+ or Debian 12+ installed
- [ ] SSH access configured
- [ ] Non-root sudo user created
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] Docker and Docker Compose installed
- [ ] Node.js 20+ installed (for frontend build)
- [ ] Git installed
- [ ] Domain name registered and DNS A record pointing to server IP

### Initial Deployment

- [ ] Clone repository to `/var/www/dummar`
- [ ] Run `./deploy.sh --seed` for first deployment
- [ ] Verify `curl http://localhost/api/health/ready` returns 200
- [ ] Verify `curl http://localhost/api/health/detailed` shows healthy
- [ ] Login with default admin credentials and **change password immediately**
- [ ] Change all seed user passwords

### SSL/TLS Setup

- [ ] Install certbot: `sudo apt install certbot`
- [ ] Run `sudo ./ssl-setup.sh your-domain.com --auto`
      (does cert + nginx.conf + CORS + restart in one step; the letsencrypt
      volumes are already unconditional in docker-compose.yml)
- [ ] Verify HTTPS: `curl -I https://your-domain.com`
- [ ] On future updates use `./deploy.sh --rebuild --domain=your-domain.com` —
      it will self-heal nginx.conf back to the SSL version after `git pull`.

### SMTP Configuration (Optional)

- [ ] Set `SMTP_ENABLED=true` in `.env`
- [ ] Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- [ ] Restart backend: `docker compose restart backend`
- [ ] Verify: `GET /health/smtp` returns `"status": "ok"`
- [ ] Test email: `POST /health/smtp/test-send` with test email address
- [ ] Trigger a real workflow (complaint status change) and verify email delivery

### Post-Deployment Verification

- [ ] All health endpoints return expected status
- [ ] Login works for all roles
- [ ] Complaint creation and status flow works
- [ ] Task assignment and completion works
- [ ] Contract approval flow works
- [ ] File upload works
- [ ] Arabic RTL UI renders correctly
- [ ] OCR status shows Tesseract available: `GET /health/ocr`
- [ ] PDF export produces readable Arabic content
- [ ] Audit logs are recording actions
- [ ] Backup strategy implemented (database + uploads)
