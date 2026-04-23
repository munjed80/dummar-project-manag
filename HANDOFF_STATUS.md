# حالة التسليم
# HANDOFF_STATUS.md

## آخر تحديث: 2026-04-23T15:22

---

## الدفعة الحالية: 2026-04-23T15:22 — Final Secret Rotation, Credential Hardening, Production-Safe Env Setup

**Scope:** Finalization pass on top of the 2026-04-23T11:58 Pre-Deployment Hardening Batch. Closes residual documentation drift and an operator-ergonomics gap. No code-path changes to the security primitives themselves — those were already correct.

### الملفات المُعدّلة في هذه الدفعة:

| الملف | التغيير |
|---|---|
| `IMPLEMENTATION_SUMMARY.md` | Removed literal dangerous defaults (`password123`, `dummar_password`, `dummar-secret-key-change-in-production-32chars-min`) from the "Default Login" section and the "Backend (.env)" example. Replaced with safe pointers to `backend/.env.example`, the `openssl rand -base64 32` generation commands, and the real `/tmp/seed_credentials.txt` retrieval/deletion guidance. Rewrote "Security Notes" section to reflect the actually hardened state (bcrypt, JWT, RBAC, `${VAR:?}` enforcement, random per-user seed passwords, auth-gated uploads/docs/metrics, 127.0.0.1 backend binding). |
| `README.md` | Path drift fix: `/app/seed_credentials.txt` and `backend/seed_credentials.txt` → `/tmp/seed_credentials.txt` (matches the actual default in `seed_data.py`). |
| `PRODUCTION_DEPLOYMENT_GUIDE.md` | Same path drift fix in Quick Start, Seed Data Strategy, and Go-Live Checklist sections. |
| `deploy.sh` | Added an always-on end-of-deploy reminder: after post-deployment verification, the script `exec`s `test -f /tmp/seed_credentials.txt` (path overridable via `SEED_CREDENTIALS_FILE`) inside the backend container. If the file exists, it prints the exact `cat` and `rm` commands and warns the operator to distribute and delete. This surfaces credentials even when `--seed` was NOT passed in the current run. |
| `PROJECT_REVIEW_AND_PROGRESS.md` | Added the new "Before Current Batch" and "After Current Batch" entries per the workflow contract. |
| `HANDOFF_STATUS.md` | This update. |

### ✅ مكتمل ومُتحقق منه (Done — verified):

| Goal | Status | Evidence |
|---|---|---|
| A) Strong production secrets are generated/applied correctly | **Done (already)** | `docker-compose.yml` enforces `${SECRET_KEY:?}` / `${DB_PASSWORD:?}`. `deploy.sh` generates `openssl rand -base64 32` values into a fresh `.env` on first run and refuses legacy literal values. Docs no longer contradict this. |
| B) Seeded users no longer rely on `password123` | **Done (already)** | `seed_users()` uses `secrets.token_urlsafe(18)` (~144 bits) per new user by default; `password123` is opt-in only via `SEED_DEFAULT_PASSWORDS=1` env or `--force-default-passwords` CLI. Verified via test run (279 passed). |
| C) Seed credentials file flow works | **Done — verified this batch** | `seed_data.py` writes `/tmp/seed_credentials.txt` with `os.open(..., O_WRONLY|O_CREAT|O_TRUNC, 0o600)` + `os.fchmod(0o600)`, and raises (no stdout fallback) on failure. Docs now point to the correct path. `deploy.sh` surfaces retrieve+delete commands on every run if the file exists. |
| D) Env/examples/fallbacks are materially safer | **Done (already)** | `backend/.env.example` has no literal secret values; `docker-compose.yml` has no fallback secrets; `IMPLEMENTATION_SUMMARY.md` cleaned of its leftover literal defaults this batch. |
| E) Deployment/operator guidance is updated honestly | **Done — this batch** | `deploy.sh` prints retrieval/deletion commands every run (not only after `--seed`); docs reflect real paths; operator steps are explicit. |
| F) Frontend build passes | **Verified** | `npm run build` → `✓ built in 936ms`, dist produced. |
| G) Backend tests pass | **Verified** | `python -m pytest tests/ -q` → **279 passed**. |
| H) `PROJECT_REVIEW_AND_PROGRESS.md` and `HANDOFF_STATUS.md` updated | **Done** | New batch entries with real verification evidence, not promises. |

### ⚠️ Partial / Out-of-scope (honestly stated):

| Item | Status | Why |
|---|---|---|
| Rotating the `.env` secrets in this repo | **N/A by design** | The repo must never contain real secrets. Rotation happens per deployment via `./deploy.sh` (`openssl rand -base64 32`) into a gitignored `.env`. This is the only correct answer for a public repo. |
| Frontend Dockerfile | **Partial** | Out of scope for this batch. Node 20+ on host is still required and documented. |
| Dependency CVE pass (`python-jose==3.3.0`, `passlib==1.7.4`, yanked `email-validator==2.1.0`) | **Not done** | Explicitly out of scope; flagged since the previous batch. Recommend a separate batch. |
| Container content-scanning (ClamAV) on uploads | **Not done** | Out of scope. |
| Real `/metrics` counters | **Not done** | Placeholders only; at least auth-gated now. |
| `backend/tests/load_test.py` CLI `--password` default is `password123` | **Kept** | Intentional: load-test tool, not seeded credential; overridable via `--password=...`. |

### 🚫 Blocked: none.

### الفجوات المتبقية قبل النشر الحقيقي:

1. **Frontend remains a host-built artifact.** Node 20+ on host, `npm run build` must run before `docker compose up`.
2. **Aging tokens/hashing libs.** `python-jose==3.3.0`, `passlib==1.7.4`, yanked `email-validator==2.1.0`. Recommend a dependency-upgrade batch.
3. **No virus scanning** on uploaded files.
4. **`/metrics` counters are placeholders** — not real request totals.

### الخطوة التالية الموصى بها قبل النشر الحقيقي على VPS:

1. Provision a fresh Ubuntu 22.04+ VPS, install Docker + Compose v2 + Node 20+ + Certbot.
2. Clone the repo; run `./deploy.sh --seed --domain=<your.domain>`. `deploy.sh` will auto-generate a `.env` with strong random secrets and surface `/tmp/seed_credentials.txt` retrieval/deletion commands at the end.
3. Copy the credentials from `/tmp/seed_credentials.txt` (inside the backend container), distribute via a secure channel, and delete:
   ```bash
   docker compose exec backend cat /tmp/seed_credentials.txt
   docker compose exec backend rm  /tmp/seed_credentials.txt
   ```
4. Force every seeded user to rotate their password on first login.
5. Run `./ssl-setup.sh <your.domain> --auto` to enable HTTPS.
6. Apply the fail2ban + daily `pg_dump` snippets from `PRODUCTION_DEPLOYMENT_GUIDE.md`.
7. Schedule a follow-up batch: frontend Dockerfile, dependency CVE pass, real `/metrics` counters, optional ClamAV on uploads.

---

## الدفعة السابقة: 2026-04-23T11:58 — Pre-Deployment Hardening Batch (Security, Secrets, Uploads, Docs, Health, Logs)

**Scope:** Strict pre-deployment hardening before real VPS deployment. NOT a feature batch.

### الملفات المُعدّلة في هذه الدفعة:

| الملف | التغيير |
|---|---|
| `docker-compose.yml` | A) Backend port now bound to `${BACKEND_BIND:-127.0.0.1}:8000:8000` (was `8000:8000` on all interfaces). B) `DB_PASSWORD` and `SECRET_KEY` use `${VAR:?}` — stack refuses to start if unset. H) `json-file` log rotation (10m × 5) added to db, backend, nginx. New env vars surfaced: `ENVIRONMENT`, `ENABLE_API_DOCS`, `BACKEND_BIND`. |
| `backend/.env.example` | B) Removed insecure literal defaults (`dummar_password`, `dummar-secret-key-...`). Now contains placeholders, generation hints, and the new `ENVIRONMENT`/`ENABLE_API_DOCS` knobs. |
| `backend/app/core/config.py` | E) Added `ENVIRONMENT` and `ENABLE_API_DOCS` settings + `is_production()` and `docs_enabled()` helpers. |
| `backend/app/main.py` | D) Removed unauthenticated `app.mount("/uploads", StaticFiles)` mount. E) `/docs`, `/redoc`, `/openapi.json` URLs are `None` unless `docs_enabled()`. G) `/metrics` now requires `get_current_internal_user`. Logs env + docs status at startup. |
| `backend/app/api/uploads.py` | D) Added `PUBLIC_CATEGORIES` / `SENSITIVE_CATEGORIES` split. New auth-gated GET handlers `/uploads/contracts/{filename}` and `/uploads/contract_intelligence/{filename}` with `_safe_filepath()` traversal defense. |
| `backend/app/api/health.py` | G) `/health/detailed` now requires `get_current_internal_user`. `/health`, `/health/ready` remain public for orchestrator probes. |
| `backend/app/scripts/seed_data.py` | C) `seed_users()` now generates `secrets.token_urlsafe(18)` per user by default and writes them to `seed_credentials.txt` (chmod 600). Legacy `password123` is opt-in via `SEED_DEFAULT_PASSWORDS=1` env or `--force-default-passwords` CLI flag. |
| `backend/entrypoint.sh` | F) `alembic upgrade head` failure is now FATAL (`exit 1`) — container exits non-zero, Docker restarts it; API never serves an inconsistent schema. |
| `nginx.conf` | D) Sensitive uploads (`contracts`, `contract_intelligence`) now proxied to backend (auth required). Public uploads still served as static. G) Updated comments to reflect that `/health/detailed` and `/metrics` now require backend auth. |
| `nginx-ssl.conf` | Same as nginx.conf for the SSL variant. |
| `deploy.sh` | B) Hardened `.env` validation: refuses to launch if `DB_PASSWORD` or `SECRET_KEY` is missing OR uses the legacy default values. New auto-generated `.env` includes `ENVIRONMENT`, `ENABLE_API_DOCS`, `BACKEND_BIND`. C) Seed-data step now describes random-password mode and how to retrieve `seed_credentials.txt`. |
| `backend/tests/test_api.py` | Updated `TestHealthEndpoints` and `TestMonitoringEndpoints` to reflect new auth requirements on `/health/detailed` and `/metrics`. Added 2 new tests asserting unauthenticated access returns 401/403. |
| `README.md` | I) Rewrote Prerequisites table to reflect real Docker-path requirements (Node on host, no host PG/nginx/Python). Removed the "default password123 for everyone" table; added security-posture summary. Updated env-var section. |
| `PRODUCTION_DEPLOYMENT_GUIDE.md` | I) Rewrote Prerequisites and Quick Start sections. Updated File Upload section with public/private split. Rewrote Seed Data Strategy with random-password mode. Replaced Security Checklist with built-in/operator split. Added fail2ban + daily pg_dump backup snippets. |
| `PROJECT_REVIEW_AND_PROGRESS.md` | Added "Before Current Batch" entry (per workflow rules) and this batch's "After" summary. |
| `HANDOFF_STATUS.md` | This update. |

### ✅ مكتمل ومُتحقق منه (Done — verified):

| Goal | Status | Evidence |
|---|---|---|
| A) Backend not publicly exposed | **Done** | `docker-compose.yml: ports: "${BACKEND_BIND:-127.0.0.1}:8000:8000"` |
| B) Unsafe secret fallbacks removed | **Done** | `${DB_PASSWORD:?...}` and `${SECRET_KEY:?...}`; deploy.sh refuses legacy defaults; `backend/.env.example` cleaned |
| C) Seed account hardening | **Done** | `seed_users` generates random per-user passwords by default; credentials file (chmod 600); legacy mode opt-in only |
| D) Sensitive uploads gated | **Done** | StaticFiles mount removed from main.py; nginx proxies `/uploads/(contracts\|contract_intelligence)/*` to backend; backend handlers require `get_current_internal_user`; path-traversal defense in `_safe_filepath()` |
| E) /docs disabled in prod | **Done** | `docs_url=None` etc. when `ENVIRONMENT=production` and `ENABLE_API_DOCS=false`. Both flags surfaced in compose + .env.example + docs |
| F) Migration failure fatal | **Done** | `entrypoint.sh`: `if ! alembic upgrade head; then exit 1; fi` |
| G) Health/metrics protected | **Done** | `/health/detailed` and `/metrics` now require `get_current_internal_user`; `/health` and `/health/ready` remain public for probes |
| H) Docker log rotation | **Done** | `logging: { driver: json-file, options: { max-size: "10m", max-file: "5" } }` on all 3 services |
| I) Docs/scripts aligned | **Done** | README + PRODUCTION_DEPLOYMENT_GUIDE rewritten for the real Docker path; deploy.sh validates env |
| J) fail2ban + backup guidance | **Done** | Added concrete jail config and `cron.daily` pg_dump snippet (with 14-day retention + restore command) to PRODUCTION_DEPLOYMENT_GUIDE |
| Frontend build | **Verified** | `npm run build` → `✓ built in 1.90s`, dist produced |
| Backend tests | **Verified** | `python -m pytest tests/ -q` → **279 passed** |

### ⚠️ Partial / Out-of-scope (honestly stated):

| Item | Status | Why |
|---|---|---|
| Frontend Dockerfile (eliminate Node-on-host requirement) | **Partial** | Out of scope for this batch. Frontend is still built on the host and bind-mounted into nginx. Documented as a host requirement in README + guide. |
| Dependency CVE pass (`python-jose 3.3.0`, `passlib 1.7.4`, yanked `email-validator 2.1.0`) | **Not done** | Out of scope (was flagged in the previous review). Recommended next batch. |
| Container content-scanning (e.g. ClamAV) on uploads | **Not done** | Out of scope; no virus scanning on uploads today. |
| Real /metrics counters (currently always zero) | **Not done** | Out of scope; counters are placeholders in `_Metrics`. They are now at least auth-gated so they don't mislead anonymous callers. |

### 🚫 Blocked: none.

### الفجوات المتبقية قبل النشر الحقيقي:

1. **Frontend remains a host-built artifact.** Until a frontend Dockerfile exists, Node 20+ on the host is mandatory and forgetting `npm run build` will result in nginx serving an empty directory.
2. **Aging dependencies.** `python-jose==3.3.0`, `passlib==1.7.4`, and the yanked `email-validator==2.1.0` should be reviewed/upgraded.
3. **No virus scanning** on uploaded files (especially the public anonymous `/uploads/public` endpoint).
4. **`/metrics` counters are placeholders** — they don't reflect real request totals. Replace with a real instrument (e.g. middleware-level counters or `prometheus_fastapi_instrumentator`) when monitoring is set up.

### الخطوة التالية الموصى بها قبل النشر الحقيقي على VPS:

1. Provision a fresh Ubuntu 22.04+ VPS, install Docker, Compose v2, Node 20+, Certbot.
2. Clone the repo, run `./deploy.sh --seed --domain=<your.domain>`.
3. Retrieve `/app/seed_credentials.txt` from the backend container, distribute, then delete it.
4. Run `./ssl-setup.sh <your.domain> --auto` to enable HTTPS.
5. Apply the fail2ban + pg_dump snippets from PRODUCTION_DEPLOYMENT_GUIDE.
6. Schedule a follow-up batch for: frontend Dockerfile, dependency upgrade pass, real metrics, and (optionally) ClamAV on uploads.

---

## الدفعة السابقة: 2026-04-18T00:11 — Advanced Location Operations Batch (Boundary Editor, Geo Dashboard, Contract-Location UI, Notifications, Haversine)

### الملفات المُعدّلة/الجديدة في هذه الدفعة:
| الملف | التغيير |
|---|---|
| `backend/app/services/location_service.py` | تحسين: Haversine بدل Euclidean + fuzzy text matching + Arabic normalization |
| `backend/app/services/notification_service.py` | إضافة: notify_location_event() لإشعارات المواقع |
| `backend/app/models/notification.py` | إضافة: LOCATION_ALERT notification type |
| `backend/app/api/locations.py` | إضافة: geo-dashboard endpoint + contract locations by contract + إشعارات location |
| `src/pages/ContractDetailsPage.tsx` | إضافة: قسم المواقع المرتبطة + ربط/فك ربط من واجهة العقد |
| `src/components/LocationFormDialog.tsx` | إضافة: محرر حدود المنطقة (boundary polygon editor) |
| `src/pages/GeoDashboardPage.tsx` | جديد: لوحة بيانات جغرافية مع خريطة + نقاط ساخنة + إحصائيات |
| `src/components/Layout.tsx` | إضافة: رابط لوحة جغرافية في القائمة |
| `src/App.tsx` | إضافة: route /locations/geo-dashboard |
| `src/services/api.ts` | إضافة: getContractLocations, linkContractToLocation, unlinkContractFromLocation, getGeoDashboard |
| `backend/tests/test_locations.py` | إضافة: 20 اختبار جديد (Haversine, fuzzy, geo-dashboard, contract-locations, notifications, boundary) |
| `PROJECT_REVIEW_AND_PROGRESS.md` | تحديث: سجل الدفعة |
| `HANDOFF_STATUS.md` | هذا التحديث |

---

## الحالة الحقيقية المُتحقق منها

### ✅ مكتمل ومُتحقق منه:

**نموذج البيانات الموحّد للمواقع:**
- ✅ جدول `locations` مع تسلسل هرمي (parent_id FK ذاتي المرجع)
- ✅ أنواع المواقع: island, sector, block, building, tower, street, service_point, other
- ✅ حقول: name, code, location_type, parent_id, status, description, latitude, longitude, boundary_path, metadata_json, is_active
- ✅ منع الحلقات الدائرية في التسلسل الهرمي
- ✅ التحقق من تفرد code

**ربط المواقع بالعمليات:**
- ✅ Complaint.location_id — FK مباشر للمواقع (nullable للتوافقية)
- ✅ Task.location_id — FK مباشر للمواقع (nullable للتوافقية)
- ✅ ContractLocation — جدول ربط many-to-many للعقود والمواقع
- ✅ الحفاظ على area_id الحالي للتوافقية

**واجهة API شاملة (23 endpoint):**
- ✅ POST /locations/ — إنشاء موقع
- ✅ GET /locations/list — قائمة مع بحث وفلاتر متعددة
- ✅ GET /locations/tree — عرض شجري كامل مع عدّادات
- ✅ GET /locations/detail/{id} — ملف الموقع التشغيلي
- ✅ GET /locations/detail/{id}/complaints — شكاوى الموقع
- ✅ GET /locations/detail/{id}/tasks — مهام الموقع
- ✅ GET /locations/detail/{id}/contracts — عقود الموقع
- ✅ GET /locations/detail/{id}/activity — النشاط الأخير
- ✅ GET /locations/detail/{id}/map-data — بيانات الخريطة
- ✅ PUT /locations/{id} — تحديث موقع
- ✅ DELETE /locations/{id} — حذف ناعم (director فقط)
- ✅ GET /locations/stats/all — إحصائيات تشغيلية
- ✅ GET /locations/reports/summary — تقرير إداري
- ✅ GET /locations/reports/export/csv — تصدير CSV
- ✅ POST /locations/contracts/link — ربط عقد بموقع
- ✅ DELETE /locations/contracts/link — فك ربط
- ✅ GET /locations/contracts/{contract_id}/locations — مواقع العقد (NEW)
- ✅ GET /locations/geo-dashboard — لوحة البيانات الجغرافية (NEW)
- ✅ الحفاظ على endpoints القديمة (areas, buildings, streets)

**هجرة البيانات (Area → Location):**
- ✅ سكريبت هجرة آمن وقابل للتكرار
- ✅ Areas → Islands, Buildings → Buildings (مع parent), Streets → Streets
- ✅ Backfill: Complaint.location_id من area_id
- ✅ Backfill: Task.location_id من area_id
- ✅ غير مدمّر — الجداول القديمة تبقى كما هي

**ربط الموقع التلقائي (Auto-assign — Enhanced):**
- ✅ عند إنشاء شكوى: explicit location_id → area_id mapping → Haversine proximity → fuzzy text
- ✅ عند إنشاء مهمة: نفس المنطق
- ✅ Haversine formula للمسافة الدقيقة (بدل Euclidean)
- ✅ Fuzzy text matching: Arabic normalization + trigram similarity
- ✅ إذا كانت الثقة منخفضة → لا يتم التعيين (يبقى فارغاً)
- ✅ يمكن التجاوز اليدوي دائماً

**واجهة المستخدم:**
- ✅ LocationsListPage — عرض شجري + عرض جدول + بحث + فلاتر + بطاقات ملخص + زر إضافة
- ✅ LocationDetailPage — ملف تشغيلي + أزرار تعديل/إضافة فرعي + خريطة تفاعلية
- ✅ LocationReportsPage — نقاط ساخنة + كثافة الشكاوى + تأخيرات + تغطية عقدية + تصدير CSV
- ✅ LocationFormDialog — نموذج شامل: اسم، رمز، نوع، أب، حالة، وصف، إحداثيات، بيانات إضافية، محرر حدود المضلع

**لوحة البيانات الجغرافية (Geo Dashboard):**
- ✅ صفحة GeoDashboardPage مع خريطة تشغيلية شاملة
- ✅ بطاقات ملخص: إجمالي المواقع + حسب النوع + نقاط ساخنة
- ✅ خريطة تفاعلية: مواقع + شكاوى + مهام على خريطة واحدة
- ✅ تبويبات: نقاط ساخنة | حسب الحالة | جميع المواقع
- ✅ رابط في القائمة الجانبية

**ربط العقود بالمواقع من واجهة العقد:**
- ✅ قسم المواقع المرتبطة في ContractDetailsPage
- ✅ ربط موقع جديد عبر نافذة اختيار
- ✅ فك ربط موقع
- ✅ عرض نوع ورمز كل موقع مرتبط
- ✅ API: GET /locations/contracts/{contract_id}/locations

**إشعارات المواقع:**
- ✅ NotificationType.LOCATION_ALERT جديد
- ✅ إشعار عند إنشاء موقع جديد
- ✅ إشعار عند ربط عقد بموقع
- ✅ يُرسل لـ project_director, area_supervisor, engineer_supervisor

**محرر حدود المنطقة (Boundary Polygon Editor):**
- ✅ إضافة نقاط مضلع بإحداثيات يدوية
- ✅ عرض النقاط المضافة مع ترقيم
- ✅ حذف نقاط فردية أو مسح جميعها
- ✅ حفظ كـ boundary_path JSON
- ✅ عرض في خريطة map-data

**خريطة تفاعلية على صفحة الموقع:**
- ✅ عرض نقطة الموقع
- ✅ عرض المواقع الفرعية بإحداثيات
- ✅ عرض الشكاوى والمهام المرتبطة
- ✅ ألوان مميزة حسب نوع الكيان

**تصدير CSV:**
- ✅ endpoint مع دعم فلاتر النوع والحالة
- ✅ ترويسات عربية + BOM لدعم Excel
- ✅ زر تنزيل في صفحة التقارير

**الجودة والأمان:**
- ✅ RBAC: internal staff only, citizen ممنوع, director فقط للحذف
- ✅ تسجيل التدقيق على جميع عمليات الموقع
- ✅ واجهة RTL عربية أولاً
- ✅ كود إنجليزي
- ✅ بيانات حقيقية من الخلفية، بدون بيانات وهمية
- ✅ 277 اختبار ناجح
- ✅ بناء الواجهة ناجح

### الاختبارات:
| مجموعة | العدد | الحالة |
|---|---|---|
| API + E2E | 121 | ✅ ناجح |
| Contract Intelligence | 86 | ✅ ناجح |
| Locations | 70 | ✅ ناجح |
| **المجموع** | **277** | **✅ ناجح** |

### الفجوات المتبقية:
- [ ] تشغيل سكريبت الهجرة على قاعدة بيانات الإنتاج (يتطلب وصول للخادم)
- [ ] تصدير CSV مع إحصائيات الفروع (حالياً: فقط الموقع المباشر)
- [ ] اكتشاف النقاط الساخنة التلقائي مع إشعارات (حالياً: فقط عند إنشاء/ربط)

### الدفعة التالية المُوصى بها:
1. خريطة رسم المضلع التفاعلية (draw on map بدل إدخال يدوي)
2. WebSocket للإشعارات الفورية
3. تصدير PDF للوحة الجغرافية
4. تحسين الأداء: تخزين مؤقت لإحصائيات المواقع
5. تكامل خرائط Google/OSM للعناوين

---

## ما قبل هذه الدفعة (2026-04-17T23:28 — Location Enhancement Batch):
- ✅ Migration script, auto-assign, CSV export, map-data
- ✅ LocationFormDialog, delete locations
- ✅ 257 tests passing
- ✅ Frontend build clean

## ما قبل ذلك (2026-04-17T22:59 — Locations Operational Geography Engine):
- ✅ Unified Location model with hierarchy
- ✅ 19 API endpoints
- ✅ LocationsListPage, LocationDetailPage, LocationReportsPage
- ✅ 244 tests passing
- ✅ Frontend build clean

---

## خطوات النشر الفعلي على VPS:

```bash
# 1. Clone the repository on VPS
git clone <repo-url> /var/www/dummar
cd /var/www/dummar

# 2. First deployment with seed data
./deploy.sh --seed --domain=dummar.example.com

# 3. Change all default passwords immediately!
docker compose exec backend python -c "
from app.scripts.seed_data import check_default_passwords
from app.core.database import SessionLocal
db = SessionLocal()
check_default_passwords(db)
"

# 4. Set up SSL (requires domain DNS pointing to server)
sudo apt install -y certbot
sudo ./ssl-setup.sh dummar.example.com --auto

# 5. Verify deployment
curl https://dummar.example.com/api/health/ready
curl https://dummar.example.com/api/health/detailed

# 6. Run load test
cd backend && python -m tests.load_test --base-url https://dummar.example.com
```

---

## الدفعة السابقة: 2026-04-17T13:27 — Intelligence Export, Filters, Extraction & Production Readiness

### الملفات المُعدّلة/الجديدة في هذه الدفعة:
| الملف | التغيير |
|---|---|
| `backend/app/services/ocr_service.py` | إضافة TesseractEngine + is_tesseract_available() + get_ocr_status() |
| `backend/app/api/contract_intelligence.py` | إضافة Excel import + reports API + OCR status + notifications |
| `backend/app/services/notification_service.py` | إضافة notify_intelligence_processing_complete() |
| `backend/app/models/notification.py` | إضافة INTELLIGENCE_PROCESSING type |
| `backend/requirements.txt` | إضافة openpyxl==3.1.5, pytesseract==0.3.13 |
| `backend/Dockerfile` | إضافة tesseract-ocr, tesseract-ocr-ara, poppler-utils |
| `backend/tests/test_contract_intelligence.py` | 18 اختبار جديد |
| `src/pages/IntelligenceReportsPage.tsx` | **جديد** — صفحة تقارير ذكاء العقود RTL |
| `src/pages/BulkImportPage.tsx` | تحديث لدعم Excel تلقائياً |
| `src/pages/ContractIntelligencePage.tsx` | إضافة رابط التقارير |
| `src/services/api.ts` | 5 دوال API جديدة |
| `src/App.tsx` | إضافة مسار التقارير |
| `PROJECT_REVIEW_AND_PROGRESS.md` | تحديث سجل الدفعات |
| `HANDOFF_STATUS.md` | هذا التحديث |

---

## الحالة الحقيقية المُتحقق منها

### ✅ مكتمل ومُتحقق منه:

**A) Tesseract OCR Support:**
- ✅ TesseractEngine كلاس كامل يدعم JPG/PNG/TIFF/BMP + PDF ممسوح ضوئياً
- ✅ is_tesseract_available() يكشف Python package + system binary مع caching
- ✅ Auto-selection: إذا Tesseract متوفر يُستخدم تلقائياً، وإلا BasicTextExtractor
- ✅ get_ocr_status() API يعرض المحرك الحالي والقدرات
- ✅ Dockerfile مُحدّث مع tesseract-ocr + tesseract-ocr-ara + poppler-utils
- ✅ Engine swappable عبر set_ocr_engine()
- ✅ Graceful fallback مع رسائل واضحة عند عدم توفر Tesseract

**B) Excel Import:**
- ✅ POST /contract-intelligence/bulk-import/preview-excel — معاينة ملف Excel
- ✅ POST /contract-intelligence/bulk-import/execute-excel — تنفيذ استيراد Excel
- ✅ يدعم عناوين أعمدة عربية وإنجليزية (نفس _COL_MAP مع CSV)
- ✅ يعالج تواريخ Excel تلقائياً (datetime → string)
- ✅ نفس flow المعاينة/التحقق/التنفيذ مع CSV
- ✅ حد 500 صف + حد 20MB
- ✅ Frontend BulkImportPage يكشف .xlsx تلقائياً ويستخدم API المناسب

**C) Processing-Completion Notifications:**
- ✅ notify_intelligence_processing_complete() يدعم 6 أحداث
- ✅ إشعار عند: اكتمال OCR، استخراج جاهز للمراجعة، تكرارات محتملة، مخاطر مرتفعة/حرجة
- ✅ إشعار عند: اكتمال استيراد جماعي (CSV/Excel/scan)، فشل استيراد كبير
- ✅ يُرسل لـ contracts_manager + project_director فقط
- ✅ NotificationType.INTELLIGENCE_PROCESSING نوع جديد
- ✅ Exception-safe: فشل الإشعار لا يكسر أي workflow

**D) Intelligence Reports:**
- ✅ GET /contract-intelligence/reports — 12 قسم بيانات حقيقية:
  1. total_documents + status_breakdown
  2. import_sources (upload/bulk_scan/spreadsheet)
  3. classification_distribution
  4. risk_by_severity + risk_by_type
  5. risks_resolved vs risks_unresolved
  6. duplicates (total/pending/confirmed_same/confirmed_different)
  7. ocr_confidence (high/medium/low/average)
  8. review_queue_size
  9. batch_results (آخر 20 دفعة مع تفاصيل)
  10. contracts_digitized
  11. ocr_engine status
- ✅ IntelligenceReportsPage: صفحة RTL عربية مع:
  - بطاقات إحصائية (5 مؤشرات رئيسية)
  - رسوم بيانية شريطية (pipeline/sources/classification/risks)
  - جدول نتائج الاستيراد الجماعي
  - معلومات جودة OCR + حالة المحرك

**E) Operational Trust:**
- ✅ RBAC: contracts_manager + project_director لجميع الميزات الجديدة
- ✅ Audit logging: يبقى سليماً (bulk_import_excel event مُضاف)
- ✅ لا توجد placeholders مزيفة
- ✅ Code في English، UI عربي RTL

### المقاييس:
- **اختبارات الخلفية:** 178 ناجح (160 سابق + 18 جديد)
- **بناء الواجهة:** ناجح
- **ملفات مُعدّلة:** 13
- **نقاط نهاية API جديدة:** 4 (preview-excel, execute-excel, reports, ocr-status)

### ⚠️ جزئي:
- **Tesseract في CI:** Binary غير متوفر في بيئة الاختبار — المحرك يكتشف ذلك ويعود لـ BasicTextExtractor. في Docker production يعمل بالكامل.
- **pdf2image:** اختيارية لـ PDFs ممسوحة ضوئياً — تعمل إذا ثُبّتت (pip install pdf2image + apt-get install poppler-utils). مُضافة في Dockerfile.

---

## الدفعة التالية المُقترحة:
1. تصدير بيانات الذكاء (CSV/PDF export)
2. تحسين دقة استخراج الحقول بأنماط إضافية
3. تحسين تقارير الذكاء بمخططات زمنية (contracts digitized over time)
4. إضافة filters/search في صفحة التقارير
5. نشر فعلي على خادم إنتاج — اختبار Tesseract OCR الحقيقي
6. تكامل مع أنظمة خارجية (إن وُجدت)

---

## الدفعة السابقة: 2026-04-17T09:30 — Contract Intelligence Center

### الملفات المُعدّلة/الجديدة في هذه الدفعة:
| الملف | التغيير |
|---|---|
| `backend/Dockerfile` | Entrypoint script, improved healthcheck (/health/ready, 30s start_period) |
| `backend/entrypoint.sh` | **جديد** — DB wait + auto-migration + gunicorn startup |
| `docker-compose.yml` | Added nginx service, DB_HOST/DB_PORT, GUNICORN_WORKERS/TIMEOUT |
| `nginx.conf` | **جديد** — Reverse proxy with rate limiting, security headers, SPA routing |
| `backend/app/api/health.py` | Added POST /health/smtp/test-send endpoint |
| `backend/tests/test_e2e.py` | **جديد** — 43 E2E integration tests |
| `backend/tests/load_test.py` | موجود من دفعة سابقة — lightweight load testing script |
| `PRODUCTION_DEPLOYMENT_GUIDE.md` | SMTP verification, load testing, nginx docs |
| `PROJECT_REVIEW_AND_PROGRESS.md` | Batch log entry |
| `HANDOFF_STATUS.md` | This update |

---

## الحالة الحقيقية المُتحقق منها

### ✅ مكتمل ومُتحقق منه:

**Production Deployment:**
1. Dockerfile: Python 3.12, non-root appuser, entrypoint.sh, HEALTHCHECK (uses /health/ready)
2. entrypoint.sh: waits for DB (30s), runs alembic upgrade head, starts gunicorn with configurable workers
3. docker-compose.yml: DB + backend + nginx services, env var overrides, healthchecks, restart policies
4. nginx.conf: reverse proxy with rate limiting (30r/s API, 5r/s uploads), security headers, SPA routing, PWA cache control
5. PRODUCTION_DEPLOYMENT_GUIDE.md: comprehensive with Quick Start, Monitoring, Audit, Troubleshooting, SMTP verification, load testing

**Monitoring & Observability:**
6. Structured logging with configurable LOG_LEVEL
7. Request logging middleware (structured key=value format)
8. GET /metrics — uptime, request counts, version
9. GET /health/ready — readiness probe (503 when DB unreachable)
10. GET /health/detailed — DB + SMTP connectivity check
11. GET /health/smtp — SMTP connection test (requires auth)

**SMTP & Notifications:**
12. POST /health/smtp/test-send — sends real test email (requires staff auth + SMTP enabled)
13. send_email() returns bool for programmatic verification
14. All notification failures logged with logger.exception()
15. Notification N+1 fixed (batch User.id.in_() queries)
16. Deduplication guard (5min window, thread-safe)
17. TLS fallback (port 465=SSL, 587=STARTTLS)
18. SMTP disabled by default (SMTP_ENABLED=false)

**Audit Logging (20+ event types):**
19. login, complaint_status_change, complaint_assignment, complaint_update
20. task_create, task_status_change, task_assignment, task_update, task_delete
21. user_create, user_update, user_deactivate
22. contract_create, contract_update, contract_approve, contract_activate, contract_suspend, contract_cancel, contract_delete
23. write_audit_log() — exception-safe, structured logging, IP + user_agent capture
24. GET /audit-logs/ — project_director only, with pagination + filters

**End-to-End Integration Tests (43 new):**
25. TestFullComplaintWorkflow (6): create → track → list → status progression → audit
26. TestFullTaskWorkflow (4): create → view → status → delete → audit
27. TestFullContractWorkflow (6): create → approve → activate → expiring → suspend → cancel
28. TestCitizenAccessRestrictions (7): citizen blocked from internal endpoints
29. TestRoleBasedAccessControl (9): role restrictions enforced
30. TestNotificationFlow (3): notifications created on events
31. TestUploadFlow (3): image field handling
32. TestDashboardAndReporting (5): stats accuracy verification

**Load/Performance Testing:**
33. backend/tests/load_test.py: stdlib-only load test (no external deps)
34. Tests 9 critical endpoints with configurable concurrency
35. Measures avg/p95/min/max/RPS per endpoint
36. Sequential E2E workflow throughput test
37. CLI usage: `python -m tests.load_test --base-url http://localhost:8000`

**Testing:**
38. 119 tests pass (76 existing + 43 E2E)
39. Frontend build passes
40. Arabic RTL UI preserved

### ⚠️ جزئي:
- **SMTP مع خادم حقيقي** — hardened, test-send endpoint added, but not tested with real SMTP server (CI environment limitation). POST /health/smtp/test-send ready for production verification.
- **Load testing execution** — script ready, cannot run against live server in CI. Ready for production deployment.
- **PostGIS geometry** — لا يزال غير مُستخدم (area boundaries stored as JSON text)

### ❌ غير مُنفذ:
- نشر على خادم إنتاج (requires real server)
- مراقبة خارجية (Prometheus/Grafana — not needed yet for this project stage)
- اختبار E2E في المتصفح (browser-based testing — too heavy for current stack, integration tests serve the purpose)

### ⚠️ ملاحظات مهمة:
- CI يتطلب Node.js 20+
- SMTP معطّل بالافتراض — `SMTP_ENABLED=false`
- `/audit-logs/` يتطلب project_director auth
- `/health/detailed` و `/health/ready` عام (بدون auth) — مناسب لـ load balancers
- `/health/smtp/test-send` يتطلب internal staff auth
- `/metrics` عام — لا يحتوي بيانات حساسة
- LOG_LEVEL قابل للتكوين عبر env var (debug/info/warning/error)
- `bcrypt==3.2.2` مُثبّت لتوافق `passlib==1.7.4`
- Docker backend now runs as non-root user (`appuser`)
- Entrypoint auto-runs migrations on startup
- nginx provides rate limiting, security headers, and SPA routing
- Load test script uses only Python stdlib (no locust/vegeta needed)

---

## الدفعات السابقة

### الدفعة: 2026-04-17T07:12 — Production Readiness Batch
**الملفات المعدلة:** `backend/Dockerfile`, `docker-compose.yml`, `backend/app/main.py`, `backend/app/middleware/`, `backend/app/core/config.py`, `backend/app/services/audit.py`, `backend/app/services/email_service.py`, `backend/app/services/notification_service.py`, `backend/app/api/auth.py`, `backend/app/api/complaints.py`, `backend/app/api/tasks.py`, `backend/app/api/contracts.py`, `backend/app/api/users.py`, `backend/app/api/dashboard.py`, `backend/app/api/health.py`, `backend/app/schemas/audit.py`, `backend/.env.example`, `backend/tests/test_api.py`, `PRODUCTION_DEPLOYMENT_GUIDE.md`

---

## الدفعة القادمة المُقترحة
1. نشر فعلي على خادم إنتاج — use docker-compose up with real .env
2. اختبار SMTP مع خادم حقيقي — use POST /health/smtp/test-send + trigger real workflows
3. تشغيل load test ضد الخادم الحقيقي — python -m tests.load_test --base-url https://... 
4. تقارير محسّنة (charts, advanced analytics, PDF reports)
5. اختبار E2E في المتصفح (Playwright/Cypress) إن لزم
6. تكامل مع أنظمة خارجية (إن وُجدت)
7. SSL/TLS setup with Let's Encrypt for nginx
