# مراجعة المشروع وتقدم العمل
# PROJECT_REVIEW_AND_PROGRESS.md

## نظرة عامة على المشروع
**الاسم:** منصة إدارة مشروع دمّر  
**الغرض:** نظام إدارة شكاوى، مهام، وعقود لمشروع دمّر السكني في دمشق  
**المرحلة الحالية:** المرحلة السادسة - الجغرافيا التشغيلية للمواقع  
**آخر تحديث:** 2026-04-17

---

## سجل الدفعات (Batch Log)

### الدفعة: 2026-04-17T23:28 — Location Enhancement Batch (CRUD, Migration, Auto-assign, Map, CSV)

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T23:28
- **فهم النظام الحالي:**
  - 244 اختبار ناجح (121 API+E2E + 86 contract intelligence + 37 locations), بناء الواجهة ناجح
  - Unified Location model exists with parent-child hierarchy (island, sector, block, building, tower, street, service_point, other)
  - Location CRUD API fully functional (19 endpoints)
  - Frontend has LocationsListPage (tree+table), LocationDetailPage (dossier), LocationReportsPage
  - Complaints/Tasks have location_id FK (nullable), but no auto-assignment logic
  - Legacy Area/Building/Street tables still exist for backward compatibility
  - No Area→Location migration path yet
  - No frontend create/edit forms for locations (only backend API)
  - No interactive map on location detail page
  - No CSV export for location reports
- **أهداف الدفعة:**
  1. Area → Location migration script (safe, repeatable)
  2. Location CRUD forms (create/edit UI with all fields)
  3. Auto-location assignment for complaints/tasks (infer from coordinates/hierarchy)
  4. Interactive Leaflet map on location detail page
  5. CSV export for location reports
- **الملفات المتوقع تعديلها:**
  - `backend/app/scripts/migrate_areas_to_locations.py` (new)
  - `backend/app/api/locations.py` (add CSV export, auto-assign endpoint)
  - `backend/app/schemas/location.py` (add auto-assign schema)
  - `backend/app/schemas/complaint.py` (add location_id)
  - `backend/app/schemas/task.py` (add location_id)
  - `backend/app/api/complaints.py` (auto-assign on create)
  - `backend/app/api/tasks.py` (auto-assign on create)
  - `src/pages/LocationsListPage.tsx` (add create button/dialog)
  - `src/pages/LocationDetailPage.tsx` (add map, edit button)
  - `src/pages/LocationReportsPage.tsx` (add CSV export)
  - `src/services/api.ts` (add new API methods)
  - `backend/tests/test_locations.py` (new tests)
- **المخاطر:**
  - Migration must not destroy existing area data
  - Auto-assignment must not silently force wrong locations
  - Leaflet map must use real data from backend

---

### الدفعة: 2026-04-17T22:59 — Locations Operational Geography Engine

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T22:59
- **فهم النظام الحالي:**
  - 207 اختبار ناجح (121 API+E2E + 86 contract intelligence)، بناء الواجهة ناجح
  - Location model has separate Area/Building/Street tables with basic CRUD
  - Complaints and Tasks link to areas via area_id FK
  - Contracts use free-text related_areas field
  - Frontend has a basic LocationsListPage showing area cards with building tables
  - No unified location hierarchy, no location detail page, no location-based stats/reports
- **أهداف الدفعة:**
  1. Add unified Location model with parent-child hierarchy (island, sector, block, building, tower, street, service_point, other)
  2. Add location_id FK on complaints and tasks for structured location linking
  3. Add ContractLocation many-to-many link table for contract coverage tracking
  4. Build comprehensive Locations API: CRUD, tree view, detail dossier, stats, reports, search/filters
  5. Build LocationsListPage with tree view + table view, search, filters, operational indicators
  6. Build LocationDetailPage with dossier (complaints, tasks, contracts, activity timeline, indicators)
  7. Build LocationReportsPage with hotspots, delays, complaint density, contract coverage
  8. Maintain backward compatibility with existing Area/Building/Street endpoints
  9. Add audit logging for all location operations
  10. Write comprehensive backend tests (37 new tests)
- **الملفات المتأثرة:**
  - backend/app/models/location.py — unified Location model + ContractLocation
  - backend/app/models/complaint.py — add location_id FK
  - backend/app/models/task.py — add location_id FK
  - backend/app/models/contract.py — add location_links relationship
  - backend/app/models/__init__.py — export new models
  - backend/app/schemas/location.py — comprehensive schemas
  - backend/app/api/locations.py — full operational geography API
  - backend/alembic/versions/007_add_locations_hierarchy.py — migration
  - backend/tests/conftest.py — add location fixtures
  - backend/tests/test_locations.py — 37 new tests
  - src/services/api.ts — add 12 new location API methods
  - src/pages/LocationsListPage.tsx — complete rewrite with tree view + table
  - src/pages/LocationDetailPage.tsx — new location dossier page
  - src/pages/LocationReportsPage.tsx — new location reports page
  - src/App.tsx — add new routes
  - package.json — @radix-ui/react-progress dependency
- **مخاطر/عوائق:**
  - Must keep existing Area/Building/Street endpoints for backward compatibility
  - SQLite test environment needs careful handling of enums and JSON

**بعد الإنتهاء:**
- **الحالة:** ✅ Done
- **الاختبارات:** 244 passed (121 API+E2E + 86 contract intelligence + 37 new locations)
- **البناء:** Frontend build passes clean
- **التغييرات المنجزة:**
  A) ✅ Location model strengthened: Unified `Location` table with hierarchy support
     - LocationType enum: island, sector, block, building, tower, street, service_point, other
     - LocationStatus enum: active, inactive, under_construction, demolished
     - Fields: name, code, location_type, parent_id (self-referential FK), status, description, latitude, longitude, boundary_path, metadata_json, is_active
     - Parent-child relationships with SQLAlchemy self-referential relationship
  B) ✅ Locations central to operations:
     - Complaint.location_id FK added (nullable for backward compatibility)
     - Task.location_id FK added (nullable for backward compatibility)
     - ContractLocation many-to-many link table for contract coverage
     - Existing area_id kept on complaints/tasks for backward compatibility
  C) ✅ Serious locations UI:
     - Tree view with expandable hierarchy, operational counters per node
     - Table/list view with search and filters (type, status, parent)
     - Summary cards showing total locations, active, open complaints, delayed tasks, hotspots
  D) ✅ Location detail page (dossier):
     - Core location info with breadcrumb navigation
     - Parent/child hierarchy display
     - Active complaints tab with table
     - Active tasks tab with table
     - Related contracts tab with table
     - Recent activity timeline (complaints + tasks merged and sorted)
     - Operational summary indicators (7 cards)
  E) ✅ Filtering and search:
     - Location type filter
     - Active/inactive filter
     - Parent-based filter (root or specific parent)
     - Keyword search (name, code, description)
     - has_open_complaints, has_active_tasks, has_contract_coverage operational filters
  F) ✅ Operational indicators:
     - Complaint count (total + open)
     - Task count (total + open)
     - Delayed task count
     - Contract count (total + active)
     - Hotspot flag (≥5 open complaints)
  G) ✅ Reports by location:
     - LocationReportsPage with management-level intelligence
     - Hotspot locations (most open complaints)
     - Highest complaint density (with progress bars)
     - Most delayed locations
     - Contract coverage overview
     - Distribution by location type
  H) ✅ Trust and quality:
     - RBAC enforced (internal staff only, citizen excluded)
     - Director-only for deletion
     - Audit logging on create, update, delete, contract link/unlink
     - Arabic-first RTL UI
     - Code in English
     - All data from real backend queries, no placeholders
     - Circular parent reference prevention
     - Code uniqueness validation
- **التحقق:**
  1. ✅ Frontend build passes
  2. ✅ Backend tests pass (244/244)
  3. ✅ Location hierarchy works (tree view, parent-child, breadcrumb, prevent circular)
  4. ✅ Complaints/tasks/contracts meaningfully linked via location_id and ContractLocation
  5. ✅ Location detail page uses real backend data
  6. ✅ Filters/search work correctly
  7. ✅ Operational indicators/reports work as intended
  8. ✅ PROJECT_REVIEW_AND_PROGRESS.md and HANDOFF_STATUS.md updated

---

### الدفعة: 2026-04-17T21:45 — UI/UX Improvements, Load Test Enhancement, Deploy Hardening, OCR Verification

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T21:45
- **فهم النظام الحالي:**
  - 207 اختبار ناجح، بناء الواجهة ناجح
  - Previous batch completed: VPS deployment scripts, SSL/TLS setup, SMTP verification path, OCR health endpoint
  - Dashboard shows raw English status keys (new, under_review, etc.) instead of Arabic labels
  - Login page displays hardcoded default credentials (security concern for production)
  - Settings page lacks system health visibility for admins
  - Load test covers 7 core endpoints but not contract intelligence
  - deploy.sh says Node.js 18+ but project requires Node.js 20+
- **أهداف الدفعة:**
  1. UI/UX: Arabic status labels + progress bars on Dashboard
  2. UI/UX: Remove hardcoded credentials from Login page
  3. UI/UX: Add system health panel to Settings page for admins
  4. UI/UX: Quick navigation buttons on Dashboard
  5. Load test: Add contract intelligence endpoints
  6. Deploy: Fix Node.js version requirement + SSL hint
  7. OCR: Verify Tesseract Arabic OCR with pytesseract + Pillow
- **الملفات المتوقع تعديلها:**
  - src/pages/DashboardPage.tsx
  - src/pages/LoginPage.tsx
  - src/pages/SettingsPage.tsx
  - backend/tests/load_test.py
  - deploy.sh
  - PROJECT_REVIEW_AND_PROGRESS.md
  - HANDOFF_STATUS.md

**بعد الانتهاء:**
- **الحالة:** ✅ مكتمل
- **الاختبارات:** 207 ناجح (لا تغيير)
- **بناء الواجهة:** ناجح
- **الملفات المُعدّلة فعلياً:**
  - `src/pages/DashboardPage.tsx` — Arabic status labels, progress bars, quick navigation buttons, spinner loading state
  - `src/pages/LoginPage.tsx` — Removed hardcoded credentials, added help toggle, input placeholders, autocomplete attributes, empty field validation
  - `src/pages/SettingsPage.tsx` — System health panel for project_director/contracts_manager (DB, SMTP, overall status)
  - `backend/tests/load_test.py` — Added 3 contract intelligence endpoints (documents, reports, risks)
  - `deploy.sh` — Fixed Node.js version check (20+), added SSL setup hint
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — full update
- **القرارات الهندسية:**
  - Login page shows "contact admin" help instead of exposing default passwords
  - Dashboard uses color-coded progress bars matching status semantics
  - Settings health panel fetches /health/detailed only for admin roles (no unnecessary API calls)
  - Load test contract intelligence endpoints may return 403 for non-contracts_manager users (expected)
- **نتائج التحقق:**
  - Arabic OCR with Tesseract: 5/5 key tokens extracted from generated contract image
  - Frontend build: clean, no errors
  - Backend tests: 207 pass
  - Dashboard now shows Arabic labels instead of English keys
  - Login page no longer exposes credentials
  - Settings page shows system health for admin roles

---

### الدفعة: 2026-04-17T21:21 — Real VPS Deployment, SSL/TLS, SMTP Verification, OCR Verification & Production Polish

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T21:21
- **فهم النظام الحالي:**
  - 205 اختبار ناجح (76 API + 43 E2E + 86 contract intelligence)، بناء الواجهة ناجح
  - Docker deployment stack exists (db + backend + nginx) with memory limits, health checks, restart policies
  - Dockerfile has Tesseract, Arabic fonts, non-root user, healthcheck
  - entrypoint.sh has DB wait, auto-migration, OCR/font verification
  - nginx.conf has rate limiting, gzip, SPA routing, but HTTP only (no SSL)
  - SMTP path hardened but never tested with real SMTP server
  - OCR path implemented with TesseractEngine but Arabic scanned files not tested in current environment
  - Production deployment guide exists but lacks SSL/TLS setup, deployment scripts, and some operational details
  - No certbot/Let's Encrypt integration
  - No deployment automation scripts
- **أهداف الدفعة:**
  1. Real VPS deployment readiness — improve Dockerfile, docker-compose, entrypoint, nginx, add deploy script
  2. SSL/TLS setup path with Let's Encrypt — certbot script, nginx SSL config, domain docs
  3. Real SMTP verification path — startup visibility, production test procedure, env docs
  4. Real Arabic scanned OCR verification — test Tesseract in runtime with Arabic text
  5. Final production-oriented verification and documentation polish
- **الملفات المتوقع تعديلها:**
  - docker-compose.yml (SSL support, certbot)
  - nginx.conf (SSL config)
  - backend/Dockerfile (improvements)
  - backend/entrypoint.sh (SMTP startup check)
  - backend/app/api/health.py (OCR verification endpoint)
  - deploy.sh (new — deployment automation)
  - ssl-setup.sh (new — Let's Encrypt setup)
  - nginx-ssl.conf (new — SSL nginx config)
  - PRODUCTION_DEPLOYMENT_GUIDE.md (SSL, SMTP, deployment improvements)
  - PROJECT_REVIEW_AND_PROGRESS.md (batch log)
  - HANDOFF_STATUS.md (update)
- **المخاطر/العوائق:**
  - Cannot issue real SSL certificate without real domain/DNS
  - Cannot test real SMTP without live SMTP server
  - Tesseract binary available in this environment for verification
  - Full deployment can only be verified in a real VPS environment
  - Docker compose up cannot run in this CI environment

**بعد الانتهاء:**
- **الحالة:** ✅ مكتمل (مع عناصر جزئية موثقة بوضوح)
- **الاختبارات:** 207 ناجح (205 سابق + 2 جديد)
- **بناء الواجهة:** ناجح
- **الملفات المُعدّلة فعلياً:**
  - `deploy.sh` — **جديد** — automated VPS deployment script with pre-flight checks, frontend build, Docker compose, health verification, seed data
  - `ssl-setup.sh` — **جديد** — Let's Encrypt certificate acquisition with DNS validation, auto-renewal cron, Docker integration
  - `nginx-ssl.conf` — **جديد** — production SSL nginx config with TLS 1.2+1.3, HSTS, OCSP stapling, ACME challenge
  - `docker-compose.yml` — added port 443, letsencrypt volume comments for SSL
  - `backend/entrypoint.sh` — added SMTP configuration check at startup
  - `backend/app/api/health.py` — added GET /health/ocr endpoint with Arabic text verification
  - `backend/tests/test_api.py` — 2 new tests (OCR health auth, OCR health status)
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` — SSL/TLS section, VPS deployment checklist, deploy.sh docs, health endpoints table updated
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log with before/after
  - `HANDOFF_STATUS.md` — full update
- **القرارات الهندسية:**
  - deploy.sh generates .env with random secrets if missing (safer than default passwords)
  - SSL nginx config uses DOMAIN_PLACEHOLDER for easy sed replacement
  - Let's Encrypt cert symlinked to ./certs/ for Docker volume stability
  - OCR health endpoint tests Arabic text processing inline (no external files needed)
  - SMTP startup check in entrypoint is informational (never blocks startup)
  - Port 443 exposed in docker-compose by default (harmless without SSL cert)
- **نتائج التحقق:**
  - Arabic OCR: Tesseract 5.3.4 with ara+eng languages verified. 5/6 Arabic tokens correctly extracted from generated contract image. Text file processing 100% accurate.
  - SMTP: Startup check implemented, production test path documented with exact endpoints and flow
  - SSL/TLS: Complete setup path implemented (cannot issue cert without real domain)
  - Deployment: deploy.sh tested for syntax/logic, cannot run Docker compose in CI
  - Tests: 207 pass, frontend builds cleanly
- **الفجوات المتبقية:**
  - SSL/TLS: Cannot issue real certificate (requires real domain + DNS) — Partial
  - SMTP: Cannot test with real SMTP server (requires live SMTP credentials) — Partial
  - Docker compose: Cannot run full stack in CI environment — Partial
  - Real scanned document OCR: Verified with generated image, not with real scanned paper document — Partial

---

### الدفعة: 2026-04-17T14:08 — Arabic PDF Export, Deployment Hardening & Tesseract Verification

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T14:08
- **فهم النظام الحالي:**
  - 201 اختبار ناجح (76 API + 43 E2E + 82 contract intelligence)، بناء الواجهة ناجح
  - Contract Intelligence Center مكتمل مع full pipeline, reports, CSV/PDF export, filters, time-series
  - PDF export exists but uses Helvetica font — Arabic text does not render correctly
  - DejaVu Sans TTF font available on system and supports Arabic glyphs
  - arabic-reshaper + python-bidi needed for proper Arabic text shaping in reportlab
  - Docker deployment stack exists (db + backend + nginx) but needs hardening
  - Tesseract integration works in Docker but is not verified in CI
  - Production deployment guide exists but needs improvement for operator handoff
- **أهداف الدفعة:**
  1. Proper Arabic PDF export with real TTF font (DejaVu Sans) + arabic-reshaper + python-bidi
  2. Production deployment hardening (Dockerfile fonts, docker-compose improvements, deployment guide)
  3. Real Tesseract OCR verification path in production stack
  4. Optional individual document/record export endpoint
  5. Preserve RBAC, audit logging, and test quality
- **الملفات المتوقع تعديلها:**
  - backend/app/api/contract_intelligence.py (Arabic PDF rendering rewrite, individual export)
  - backend/requirements.txt (add arabic-reshaper, python-bidi)
  - backend/Dockerfile (add fonts-dejavu-core for Arabic PDF)
  - docker-compose.yml (deployment hardening)
  - nginx.conf (improvements)
  - backend/entrypoint.sh (improvements)
  - backend/tests/test_contract_intelligence.py (new tests)
  - PRODUCTION_DEPLOYMENT_GUIDE.md (Tesseract + deployment improvements)
  - PROJECT_REVIEW_AND_PROGRESS.md (batch log)
  - HANDOFF_STATUS.md (update)
- **المخاطر/العوائق:**
  - DejaVu Sans supports Arabic glyphs but reportlab needs arabic-reshaper for proper letter joining
  - python-bidi needed for correct right-to-left display order
  - Tesseract binary not available in CI — tests must handle gracefully
  - Full OCR verification only possible inside Docker container

**بعد الانتهاء:**
- **الحالة:** ✅ مكتمل بالكامل
- **الاختبارات:** 205 ناجح (201 سابق + 4 جديد)
- **بناء الواجهة:** ناجح
- **الملفات المُعدّلة فعلياً:**
  - `backend/app/api/contract_intelligence.py` — Arabic PDF export rewrite (DejaVu Sans + arabic-reshaper + python-bidi), individual document PDF export endpoint
  - `backend/requirements.txt` — added arabic-reshaper==3.0.0, python-bidi==0.6.7
  - `backend/Dockerfile` — added fonts-dejavu-core package
  - `docker-compose.yml` — added memory limits for all services
  - `nginx.conf` — added gzip, auth rate limiting, upload rate limiting with extended timeout, client_max_body_size 20M
  - `backend/entrypoint.sh` — added Tesseract + Arabic font verification at startup
  - `backend/tests/test_contract_intelligence.py` — 4 new tests (Arabic PDF, individual doc export, 404, RBAC)
  - `src/services/api.ts` — added downloadDocumentPdf() method
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` — added Arabic PDF section, Tesseract verification checklist, updated Docker features
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — full update
- **القرارات الهندسية:**
  - DejaVu Sans chosen over Noto/Amiri because it's available in Debian default package (fonts-dejavu-core), supports Arabic glyphs, and has matching Bold variant
  - arabic-reshaper used for proper Arabic letter joining (isolated→connected forms) since reportlab doesn't do this natively
  - python-bidi used for correct RTL display order in PDF (drawString is LTR by default)
  - Font registration uses graceful fallback: if DejaVu Sans not found, Helvetica is used (English-only but still valid PDF)
  - Individual document export includes: metadata, extracted fields, classification, summary, risks, duplicates
  - nginx auth_limit (10r/s) added separately from api_limit (30r/s) for login endpoint protection
  - Upload timeout extended to 300s for contract intelligence bulk imports
  - Memory limits: db 512M, backend 1G, nginx 128M — conservative for small VPS
- **الفجوات المتبقية:**
  - Tesseract binary not available in CI (only in Docker) — tests detect and handle gracefully
  - Full OCR verification with real scanned documents only possible in Docker deployment
  - No SSL/TLS (Let's Encrypt) setup — requires real domain and server

---

### الدفعة: 2026-04-17T13:27 — Intelligence Export, Filters, Extraction & Production Readiness

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T13:27
- **فهم النظام الحالي:**
  - 178 اختبار ناجح (76 API + 43 E2E + 59 contract intelligence)، بناء الواجهة ناجح
  - Contract Intelligence Center مكتمل مع: OCR (basic + Tesseract), extraction, classification, summary, risk, duplicates, CSV/Excel import, reports API, notifications
  - Reports page shows 12 data sections with charts and tables
  - Tesseract integration works in Docker but not available in CI
  - No export capability (CSV/PDF) for intelligence reports
  - No filters/search in intelligence reports page
  - Extraction patterns cover basic cases but not edge cases (mixed Arabic/English, OCR noise)
- **أهداف الدفعة:**
  1. Data export from intelligence reports (CSV + PDF)
  2. Filters/search improvements in reports page
  3. Production-ready Tesseract verification path
  4. Extraction pattern refinement for edge cases
  5. Optional time-series reporting
- **الملفات المتوقع تعديلها:**
  - backend/app/api/contract_intelligence.py (export endpoints, filter params)
  - backend/app/services/extraction_service.py (pattern refinement)
  - backend/app/services/ocr_service.py (health indicator improvements)
  - backend/tests/test_contract_intelligence.py (new tests)
  - src/pages/IntelligenceReportsPage.tsx (filters, export, time-series)
  - src/services/api.ts (new API methods)
  - backend/Dockerfile (production verification)
  - PRODUCTION_DEPLOYMENT_GUIDE.md (Tesseract docs)
- **المخاطر/العوائق:**
  - reportlab already in requirements.txt — can use for PDF export
  - Tesseract binary not available in CI — tests must handle gracefully
  - Time-series requires created_at data aggregation — may be limited with test data

**بعد الانتهاء:**
- **الحالة:** ✅ مكتمل بالكامل
- **الاختبارات:** 201 ناجح (178 سابق + 23 جديد)
- **بناء الواجهة:** ناجح
- **الملفات المُعدّلة فعلياً:**
  - `backend/app/api/contract_intelligence.py` — 10 filter params, CSV/PDF export, time-series
  - `backend/app/services/extraction_service.py` — OCR noise cleanup, edge case patterns
  - `backend/app/services/ocr_service.py` — enhanced get_ocr_status()
  - `backend/tests/test_contract_intelligence.py` — 23 new tests
  - `src/pages/IntelligenceReportsPage.tsx` — filters, exports, time-series
  - `src/services/api.ts` — 3 API methods (getIntelligenceReports params, CSV, PDF)
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` — Tesseract OCR section
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — full update
- **القرارات الهندسية:**
  - Used sql_func.substr for SQLite-compatible date aggregation (vs cast to Date which fails in SQLite)
  - PDF export uses Helvetica font (Arabic display limitation noted as Partial)
  - Filters applied via intermediate filtered_ids list for clean SQL composition
  - _clean_ocr_noise() applied before all field extraction for consistent behavior
- **الفجوات المتبقية:**
  - PDF export doesn't render Arabic text natively (requires custom TTF font registration)
  - Tesseract binary not available in CI — tests use is_tesseract_available() detection

---

### الدفعة: 2026-04-17T12:34 — Contract Intelligence Operational Completion

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T12:34
- **فهم النظام الحالي:**
  - 160 اختبار ناجح (76 API + 43 E2E + 41 contract intelligence)، بناء الواجهة ناجح
  - مركز ذكاء العقود موجود مع: OCR (نصوص PDF فقط)، استخراج حقول، تصنيف، ملخص، مخاطر، تكرارات، CSV import
  - OCR للصور غير متوفر (يحتاج Tesseract)
  - لا يوجد دعم Excel (.xlsx)
  - لا توجد إشعارات لاكتمال المعالجة
  - لا توجد تقارير/رسوم بيانية لذكاء العقود
- **أهداف الدفعة:**
  1. دعم Tesseract OCR الحقيقي مع كشف تلقائي للتوفر
  2. استيراد Excel (.xlsx) عبر openpyxl
  3. إشعارات اكتمال المعالجة (OCR/استيراد/مراجعة/مخاطر)
  4. تقارير ورسوم بيانية ذكاء العقود
- **الملفات المتوقع تعديلها:**
  - backend/app/services/ocr_service.py (Tesseract engine)
  - backend/app/api/contract_intelligence.py (Excel import + reports API)
  - backend/app/services/notification_service.py (intelligence notifications)
  - backend/app/models/notification.py (new notification type)
  - backend/app/schemas/contract_intelligence.py (report schemas)
  - backend/requirements.txt (openpyxl, pytesseract)
  - backend/Dockerfile (tesseract-ocr package)
  - backend/tests/test_contract_intelligence.py (new tests)
  - src/pages/IntelligenceReportsPage.tsx (new)
  - src/services/api.ts (new API methods)
  - src/App.tsx (new route)
  - src/components/Layout.tsx (nav link)
- **المخاطر/العوائق:**
  - Tesseract binary may not be available in CI — implement graceful fallback
  - openpyxl is a new dependency

**بعد الانتهاء:**
- **الطابع الزمني:** 2026-04-17T13:30
- **النتيجة: Done**
- **الاختبارات:** 178 اختبار ناجح (160 سابق + 18 جديد)
- **بناء الواجهة:** ناجح
- **التفاصيل:**
  - ✅ **Tesseract OCR:** TesseractEngine مع كشف تلقائي (is_tesseract_available)، يدعم صور + PDF ممسوح ضوئياً، fallback سلس إلى BasicTextExtractor
  - ✅ **OCR Status API:** GET /contract-intelligence/ocr-status — يعرض المحرك الحالي وحالة Tesseract
  - ✅ **Dockerfile:** إضافة tesseract-ocr + tesseract-ocr-ara + poppler-utils
  - ✅ **Excel Import:** preview-excel + execute-excel عبر openpyxl، يدعم عناوين أعمدة عربية/إنجليزية
  - ✅ **Notifications:** 6 أنواع إشعارات ذكاء (ocr_complete, extraction_review_ready, duplicate_review_needed, risk_review_needed, batch_import_complete, batch_import_failed)
  - ✅ **Intelligence Reports API:** GET /contract-intelligence/reports — 12 قسم بيانات حقيقية
  - ✅ **IntelligenceReportsPage:** صفحة تقارير RTL عربية مع رسوم بيانية وجداول وبطاقات
  - ✅ **RBAC:** contracts_manager + project_director فقط لجميع الميزات الجديدة
  - ✅ **Audit logging:** يبقى سليماً لجميع العمليات
  - ✅ **18 اختبار جديد** تغطي: Tesseract detection, Excel preview/execute/Arabic headers, notifications, reports, RBAC
- **الملفات المُعدّلة:**
  - `backend/app/services/ocr_service.py` — TesseractEngine, is_tesseract_available(), get_ocr_status()
  - `backend/app/api/contract_intelligence.py` — Excel import endpoints, reports endpoint, OCR status, notifications
  - `backend/app/services/notification_service.py` — notify_intelligence_processing_complete()
  - `backend/app/models/notification.py` — INTELLIGENCE_PROCESSING type
  - `backend/requirements.txt` — openpyxl==3.1.5, pytesseract==0.3.13
  - `backend/Dockerfile` — tesseract-ocr, tesseract-ocr-ara, poppler-utils
  - `backend/tests/test_contract_intelligence.py` — 18 new tests
  - `src/pages/IntelligenceReportsPage.tsx` — new
  - `src/pages/BulkImportPage.tsx` — Excel auto-detection
  - `src/pages/ContractIntelligencePage.tsx` — reports quick link
  - `src/services/api.ts` — 5 new API methods
  - `src/App.tsx` — reports route
- **ملاحظات جزئية:**
  - Tesseract OCR binary غير متوفر في بيئة CI — المحرك يُكتشف تلقائياً ويعود لـ BasicTextExtractor
  - pdf2image (لـ PDFs ممسوحة ضوئياً) اختيارية — تعمل إذا ثُبّتت

---

### الدفعة: 2026-04-17T09:30 — Contract Intelligence Center

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T09:30
- **فهم النظام الحالي:**
  - 119 اختبار ناجح (76 API + 43 E2E)، بناء الواجهة ناجح
  - منصة كاملة: شكاوى، مهام، عقود، GIS، PWA، RBAC، إشعارات، health checks، audit logging، deployment configs
  - العقود تدعم: إنشاء، مراجعة، موافقة، تفعيل، تعليق، إلغاء، حذف، PDF، QR
  - لا يوجد OCR أو استخراج حقول أو كشف تكرارات أو تحليل مخاطر
- **أهداف الدفعة:**
  1. OCR للعقود الممسوحة ضوئياً
  2. استخراج حقول ذكي من النصوص
  3. استيراد جماعي (CSV + ملفات ممسوحة)
  4. كشف العقود المتكررة/المشابهة
  5. تصنيف العقود الذكي
  6. إنشاء ملخص تلقائي
  7. تحليل المخاطر وإشارات التحذير
- **الملفات المتوقع تعديلها:**
  - backend/app/models/contract_intelligence.py (جديد)
  - backend/app/schemas/contract_intelligence.py (جديد)
  - backend/alembic/versions/006_add_contract_intelligence.py (جديد)
  - backend/app/services/ocr_service.py, extraction_service.py, classification_service.py, summary_service.py, duplicate_service.py, risk_service.py (جديد)
  - backend/app/api/contract_intelligence.py (جديد)
  - backend/tests/test_contract_intelligence.py (جديد)
  - src/pages/ (6 صفحات جديدة)
  - src/services/api.ts, src/App.tsx, src/components/Layout.tsx

**بعد الانتهاء:**
- **الطابع الزمني:** 2026-04-17T10:20
- **النتيجة: Done**
- **الاختبارات:** 160 اختبار ناجح (119 سابق + 41 جديد)
- **بناء الواجهة:** ناجح
- **التفاصيل:**
  - ✅ نماذج بيانات: ContractDocument, ContractRiskFlag, ContractDuplicate
  - ✅ ترحيل قاعدة البيانات 006
  - ✅ خدمة OCR (تجريد مع محرك قابل للاستبدال، PDF text + image placeholder)
  - ✅ استخراج حقول (رقم العقد، التواريخ، القيمة، المقاول، المدة، النطاق، المواقع)
  - ✅ تصنيف عقود (8 أنواع + تحليل كلمات مفتاحية عربي/إنجليزي)
  - ✅ إنشاء ملخص (ملخص عربي تلقائي)
  - ✅ كشف تكرارات (5 إشارات: رقم، اسم، عنوان، قيمة، تواريخ)
  - ✅ تحليل مخاطر (10+ أنواع: حقول مفقودة، تواريخ خاطئة، قيمة عالية، انتهاء، نطاق غامض)
  - ✅ 20+ نقطة نهاية API مع RBAC وتسجيل تدقيق
  - ✅ استيراد CSV جماعي مع معاينة + ربط أعمدة
  - ✅ استيراد ملفات ممسوحة دفعياً
  - ✅ تحويل مستند إلى عقد رسمي
  - ✅ 6 صفحات واجهة RTL عربية
  - ✅ تكامل مع صفحة تفاصيل العقد (مخاطر، تكرارات، مصادر)

---

### الدفعة: 2026-04-17T07:51 — Deployment Readiness, E2E Validation, Load Testing, SMTP Verification

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T07:51
- **فهم النظام الحالي:**
  - 76 اختبار ناجح، بناء الواجهة ناجح
  - منصة قوية مع: شكاوى، مهام، عقود، GIS، PWA، RBAC، إشعارات، health checks، audit logging (20+ events)، structured logging
  - Dockerfile يستخدم Python 3.12، non-root appuser، HEALTHCHECK
  - docker-compose.yml يدعم env var overrides ويتضمن healthchecks
  - SMTP integration مُعزّز لكن لم يُختبر مع خادم حقيقي (بيئة CI)
  - لا يوجد entrypoint script مع auto-migration
  - لا يوجد nginx reverse proxy config
  - لا يوجد اختبارات E2E متكاملة (فقط unit/API tests)
  - لا يوجد اختبارات أداء/حمل
  - لا يوجد SMTP test-send endpoint
  - PRODUCTION_DEPLOYMENT_GUIDE.md موجود لكن يحتاج تحسين

- **أهداف هذه الدفعة:**
  1. Production deployment readiness: entrypoint script, nginx config, docker-compose improvements
  2. SMTP verification path: test-send endpoint, verification checklist
  3. End-to-end operational validation: 43+ integration tests covering full workflows
  4. Load/performance testing: lightweight load test script
  5. Documentation updates: operator handoff improvements

- **الملفات المخطط تعديلها:**
  - `backend/Dockerfile` — entrypoint, improved healthcheck
  - `backend/entrypoint.sh` — جديد: DB wait + auto-migration + gunicorn startup
  - `docker-compose.yml` — nginx service, additional env vars
  - `nginx.conf` — جديد: reverse proxy config
  - `backend/app/api/health.py` — SMTP test-send endpoint
  - `backend/tests/test_e2e.py` — جديد: 43 E2E integration tests
  - `backend/tests/load_test.py` — موجود: load test script
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` — deployment guide improvements
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — status update

- **المخاطر/العوائق:**
  - SMTP لا يمكن اختباره مع خادم حقيقي في بيئة CI
  - Docker build لا يمكن تشغيله في هذه البيئة
  - Load tests تحتاج خادم حقيقي قيد التشغيل

**بعد الانتهاء:**
- **النتيجة:** ✅ Done

  **1. Production Deployment Readiness:**
  - ✅ `backend/entrypoint.sh`: DB readiness wait (30s max) + auto-migration + gunicorn startup with configurable workers/timeout
  - ✅ Dockerfile: uses entrypoint.sh, improved healthcheck (uses /health/ready, 30s start_period)
  - ✅ docker-compose.yml: added nginx service, DB_HOST/DB_PORT/GUNICORN_WORKERS/GUNICORN_TIMEOUT env vars, 30s start_period
  - ✅ `nginx.conf`: reverse proxy with rate limiting (30r/s API, 5r/s uploads), security headers, SPA routing, PWA cache control, direct upload serving

  **2. SMTP Verification Path:**
  - ✅ `POST /health/smtp/test-send`: sends real test email (requires staff auth + SMTP enabled)
  - ✅ SMTP implementation verified as hardened: exception-safe, dedup guard, TLS fallback, 30s timeout
  - ⚠️ Real SMTP test: not possible in CI environment. Test-send endpoint ready for production verification.
  - ✅ SMTP verification checklist documented in deployment guide

  **3. End-to-End Operational Validation:**
  - ✅ 43 new integration tests in `backend/tests/test_e2e.py`:
    - TestFullComplaintWorkflow (6): create → track → list → status progression → audit verification
    - TestFullTaskWorkflow (4): create → view → status progression → delete → audit verification
    - TestFullContractWorkflow (6): create → approve → activate → expiring-soon → suspend → cancel
    - TestCitizenAccessRestrictions (7): blocked from internal endpoints, allowed on citizen endpoints
    - TestRoleBasedAccessControl (9): field team, contractor, and multi-role restrictions
    - TestNotificationFlow (3): notifications on status changes and task assignment
    - TestUploadFlow (3): image field handling
    - TestDashboardAndReporting (5): empty state, counts after changes, status updates

  **4. Load/Performance Testing:**
  - ✅ `backend/tests/load_test.py`: stdlib-only load test script
  - Tests 9 endpoints with configurable concurrency
  - Measures avg/p95/min/max response times, error rates, RPS
  - Sequential E2E workflow test
  - CLI: `python -m tests.load_test --base-url http://localhost:8000`
  - ⚠️ Cannot run against live server in CI. Ready for production use.

  **5. Stability:**
  - ✅ 119 tests pass (76 existing + 43 E2E)
  - ✅ Frontend build passes
  - ✅ Arabic RTL UI preserved
  - ✅ All existing functionality preserved

  **Exact files changed:** 8 files
  - `backend/Dockerfile` — entrypoint, improved healthcheck
  - `backend/entrypoint.sh` (new) — DB wait + auto-migration + gunicorn startup
  - `docker-compose.yml` — nginx service, additional env vars
  - `nginx.conf` (new) — reverse proxy config
  - `backend/app/api/health.py` — SMTP test-send endpoint
  - `backend/tests/test_e2e.py` (new) — 43 E2E integration tests
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — status update

---

### الدفعة: 2026-04-17T00:25 — Fix CI + Audit Logging API + PWA Install Prompt

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T00:25
- **فهم النظام الحالي:**
  - CI failing: Node.js 18 في CI workflow لكن Vite 8 + Tailwind CSS 4 + React Router 7 تتطلب Node.js 20+
  - AuditLog model موجود لكن لا يوجد API endpoint لعرض سجلات التدقيق
  - write_audit_log لا يلتقط IP address أو user_agent تلقائياً من Request
  - PWA manifest و service worker موجودان لكن لا يوجد custom install prompt

- **أهداف هذه الدفعة:**
  1. إصلاح CI: تحديث Node.js من 18 إلى 20
  2. Audit Logging API: endpoint لعرض سجلات التدقيق مع pagination + filters
  3. تحسين audit trail: التقاط IP + user_agent تلقائياً من Request
  4. PWA Install Prompt: مكون عربي يعرض عند إمكانية التثبيت

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ CI fix — Node.js 18 → 20 في `.github/workflows/ci.yml`
  2. ✅ `GET /audit-logs/` — endpoint مع pagination + filters (action, entity_type, user_id)
  3. ✅ Migration 005 — indexes لـ created_at و (user_id, entity_type) على audit_logs
  4. ✅ Schema — AuditLogResponse + PaginatedAuditLogs
  5. ✅ RBAC — project_director فقط يمكنه عرض audit logs
  6. ✅ IP capture — write_audit_log يقبل Request ويلتقط IP + user_agent تلقائياً
  7. ✅ Complaints/Tasks/Contracts — يمررون Request إلى write_audit_log
  8. ✅ InstallPrompt component — بانر عربي RTL مع أزرار تثبيت/إغلاق
  9. ✅ localStorage dismiss — المستخدم يمكنه إخفاء البانر نهائياً
  10. ✅ 66 اختبار ناجح (60 سابق + 6 audit log tests)
  11. ✅ بناء الواجهة ناجح

---

### الدفعة: 2026-04-17T07:12 — Production Readiness Batch (Deployment + SMTP + Monitoring + Audit + Performance)

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T07:12
- **فهم النظام الحالي:**
  - 66 اختبار ناجح، بناء الواجهة ناجح
  - منصة قوية مع: شكاوى، مهام، عقود، GIS، PWA، RBAC، إشعارات، health checks
  - SMTP integration موجود لكن لم يُختبر مع خادم حقيقي
  - Audit logging موجود لكن يغطي فقط: complaint_update, task_update, contract_create/update/approve/delete, user_create/update/deactivate, login
  - لا يوجد: audit لتغيير status بشكل منفصل، audit لتغيير assignment، audit لـ task_create/delete، structured logging، request logging middleware، metrics endpoint، readiness probe
  - Dashboard queries تستخدم N+1 pattern (query لكل status)
  - Notification service تستخدم N+1 pattern (query لكل user)
  - Dockerfile يستخدم Python 3.11 ويعمل كـ root
  - docker-compose.yml يحتوي credentials مكشوفة ولا يدعم env vars

- **أهداف هذه الدفعة:**
  1. Production deployment readiness: Dockerfile, docker-compose, deployment guide
  2. SMTP hardening: better error logging, return values
  3. Monitoring foundation: structured logging, request logging middleware, metrics endpoint, readiness probe
  4. Detailed audit logging: status changes, assignments, task creation/deletion, user management with Request
  5. Query optimization: dashboard N+1, notification N+1
  6. Keep all 66 existing tests passing

- **الملفات المخطط تعديلها:**
  - `backend/Dockerfile` — Python 3.12, non-root user, healthcheck, gunicorn
  - `docker-compose.yml` — env var support, healthchecks, restart policies
  - `backend/app/main.py` — structured logging, lifespan, metrics, request logging middleware
  - `backend/app/middleware/request_logging.py` — new: structured request logging
  - `backend/app/services/audit.py` — exception safety, structured logging
  - `backend/app/services/email_service.py` — return bool, better logging
  - `backend/app/api/complaints.py` — audit for status change, assignment change
  - `backend/app/api/tasks.py` — audit for create, delete, status change, assignment
  - `backend/app/api/contracts.py` — log notification failures
  - `backend/app/api/users.py` — Request param, better audit descriptions
  - `backend/app/api/auth.py` — Request param for login audit
  - `backend/app/api/health.py` — readiness probe
  - `backend/app/api/dashboard.py` — GROUP BY optimization
  - `backend/app/services/notification_service.py` — batch user lookups
  - `backend/app/core/config.py` — LOG_LEVEL setting
  - `backend/app/schemas/audit.py` — add user_agent field
  - `backend/.env.example` — updated defaults
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` — comprehensive rewrite
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — status update
  - `backend/tests/test_api.py` — 10 new tests

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**

  **1. Production Deployment Readiness:**
  - ✅ Dockerfile: Python 3.12, non-root `appuser`, HEALTHCHECK directive, gunicorn with uvicorn workers, unbuffered output
  - ✅ docker-compose.yml: env var overrides via `.env`, healthchecks for both DB and backend, restart policies, all SMTP vars exposed, LOG_LEVEL support, reduced token expiry (480 min)
  - ✅ PRODUCTION_DEPLOYMENT_GUIDE.md: comprehensive rewrite with Quick Start, Monitoring & Observability, Audit Trail, Troubleshooting sections
  - ✅ nginx config includes security headers, PWA sw.js cache control, proxy timeout

  **2. SMTP Hardening:**
  - ✅ `send_email()` returns `bool` (True=sent, False=failed/skipped) instead of None
  - ✅ All notification failures logged with `logger.exception()` instead of `pass`
  - ✅ Notification N+1 fixed: batch user lookups with `User.id.in_(user_ids)` 
  - ⚠️ Real SMTP test: not possible in CI environment — no real SMTP server available. The integration is hardened and ready to test with a real server. Steps to verify documented in deployment guide.

  **3. Monitoring & Observability:**
  - ✅ Structured logging: `basicConfig` with timestamp + level + logger name format
  - ✅ Request logging middleware: structured key=value format (method, path, status, duration_ms, client)
  - ✅ Health check paths excluded from request logging to reduce noise
  - ✅ `GET /metrics` endpoint: uptime_seconds, total_requests, error_requests, version
  - ✅ `GET /health/ready` endpoint: readiness probe returns 503 when DB unreachable
  - ✅ LOG_LEVEL configurable via environment variable
  - ✅ Deprecated `@app.on_event("startup")` replaced with modern `lifespan` context manager

  **4. Detailed Audit Logging:**
  - ✅ `login` — now captures IP + user_agent via Request
  - ✅ `complaint_status_change` — separate audit entry for status transitions
  - ✅ `complaint_assignment` — separate audit entry when assigned_to changes
  - ✅ `task_create` — new audit event
  - ✅ `task_status_change` — new audit event
  - ✅ `task_assignment` — new audit event
  - ✅ `task_delete` — new audit event (with Request)
  - ✅ `user_create` — now includes role in description
  - ✅ `user_update` — now includes changed fields diff in description
  - ✅ `user_deactivate` — now includes role, passes Request
  - ✅ `write_audit_log()` — exception-safe (never raises), structured log output
  - ✅ `AuditLogResponse` schema — now includes `user_agent` field

  **5. Query Optimization:**
  - ✅ Dashboard stats: replaced 3+N individual COUNT queries with 3 GROUP BY queries (complaint/task/contract counts by status in single queries)
  - ✅ Notification service: replaced N+1 user lookups with batch `User.id.in_()` queries for both complaint and contract notifications

  **6. Stability:**
  - ✅ 76 tests pass (66 existing + 10 new)
  - ✅ Frontend build passes
  - ✅ Arabic RTL UI preserved
  - ✅ All existing functionality preserved

  **New tests added (10):**
  - `test_metrics_endpoint` — metrics returns uptime and version
  - `test_readiness_endpoint` — readiness probe returns ready
  - `test_health_basic` — basic health check
  - `test_task_create_audit` — task creation audit
  - `test_user_create_audit` — user creation audit with role
  - `test_user_deactivate_audit` — user deactivation audit
  - `test_complaint_status_change_audit` — status change audit
  - `test_contract_approve_audit` — contract approval audit
  - `test_audit_log_response_includes_user_agent` — user_agent in response
  - `test_dashboard_stats_with_data` — optimized dashboard correctness

  **Exact files changed:** 20 files
  - `backend/Dockerfile`
  - `docker-compose.yml`
  - `backend/app/main.py`
  - `backend/app/middleware/__init__.py` (new)
  - `backend/app/middleware/request_logging.py` (new)
  - `backend/app/core/config.py`
  - `backend/app/services/audit.py`
  - `backend/app/services/email_service.py`
  - `backend/app/services/notification_service.py`
  - `backend/app/api/auth.py`
  - `backend/app/api/complaints.py`
  - `backend/app/api/tasks.py`
  - `backend/app/api/contracts.py`
  - `backend/app/api/users.py`
  - `backend/app/api/dashboard.py`
  - `backend/app/api/health.py`
  - `backend/app/schemas/audit.py`
  - `backend/.env.example`
  - `backend/tests/test_api.py`
  - `PRODUCTION_DEPLOYMENT_GUIDE.md`

---

### الدفعة: 2026-04-17T00:01 — PWA + Area Boundaries Migration + Health Monitoring

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T00:01
- **فهم النظام الحالي:**
  - منصة إدارة مشروع دمّر مع واجهة عربية RTL، FastAPI backend + React 19 frontend
  - 52 اختبار ناجح، بناء الواجهة ناجح
  - Mobile responsiveness مكتمل — hamburger nav، card views، responsive filters
  - SMTP معزز — TLS fallback، dedup guard، escape — لم يُختبر مع خادم حقيقي
  - Area boundaries ثابتة في gis.py كـ hardcoded dict — النموذج يحتوي geometry column لكن لا يُستخدم
  - لا يوجد PWA/offline mode — التطبيق يحتاج اتصال إنترنت دائم
  - لا يوجد endpoint صحة تفصيلي — فقط /health بسيط

- **أهداف هذه الدفعة:**
  1. PWA/offline mode — Service Worker + web app manifest للعمل دون اتصال ولإمكانية التثبيت
  2. نقل area boundaries من hardcoded dict إلى قاعدة البيانات (migration + seed update + API update)
  3. Health monitoring — endpoint تفصيلي يتحقق من DB + SMTP
  4. SMTP connection test endpoint

- **الملفات المخطط تعديلها:**
  - `public/manifest.json` — جديد: PWA manifest
  - `public/sw.js` — جديد: Service Worker
  - `src/main.tsx` — تسجيل Service Worker
  - `index.html` — PWA meta tags + manifest link
  - `backend/alembic/versions/004_add_area_boundary_data.py` — جديد: migration
  - `backend/app/scripts/seed_data.py` — تحديث لتخزين boundary data
  - `backend/app/api/gis.py` — قراءة boundaries من DB + endpoint إداري لتحديثها
  - `backend/app/api/health.py` — جديد: health checks تفصيلية
  - `backend/app/main.py` — تسجيل health router
  - `backend/tests/test_api.py` — اختبارات جديدة
  - `PROJECT_REVIEW_AND_PROGRESS.md` — سجل الدفعة
  - `HANDOFF_STATUS.md` — تحديث الحالة

- **المخاطر:**
  - Service Worker caching قد يسبب مشاكل في عرض التحديثات — يجب استخدام network-first strategy
  - migration 004 يجب أن تكون متوافقة مع CI (SQLite)

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ PWA manifest — `public/manifest.json` مع RTL + Arabic meta
  2. ✅ Service Worker — `public/sw.js` بإستراتيجية network-first للتنقل و stale-while-revalidate للأصول الثابتة
  3. ✅ SW Registration — `src/main.tsx` يسجل SW عند التحميل (fail-safe)
  4. ✅ PWA Icons — `icon-192.png` و `icon-512.png` مُولّدة
  5. ✅ PWA meta tags — theme-color، apple-mobile-web-app، manifest link في `index.html`
  6. ✅ Migration 004 — boundary_polygon (Text/JSON) + color (String) مضافة لجدول areas
  7. ✅ Area model — الأعمدة الجديدة مضافة لنموذج `location.py`
  8. ✅ Seed data — boundaries تُخزّن في DB مع backfill للبيانات الموجودة
  9. ✅ GIS API — `area-boundaries` يقرأ من DB بدل hardcoded dict
  10. ✅ PUT `/gis/area-boundaries/{id}` — endpoint لتحديث الحدود (project_director فقط)
  11. ✅ Health detailed — `/health/detailed` يتحقق من DB + SMTP (public)
  12. ✅ SMTP test — `/health/smtp` يختبر اتصال SMTP (يتطلب auth)
  13. ✅ 60 اختبار ناجح (52 سابق + 3 health + 5 area boundary)
  14. ✅ بناء الواجهة ناجح مع PWA files في dist/
  15. ✅ AREA_BOUNDARIES hardcoded dict أُزيل بالكامل من gis.py

- **القرارات الهندسية:**
  - SW strategy: network-first للتنقل (ضمان حداثة البيانات) + stale-while-revalidate للأصول (سرعة)
  - API requests لا تُخزّن مؤقتاً أبداً — البيانات المتغيرة يجب أن تأتي من الخادم دائماً
  - boundary_polygon يُخزّن كـ JSON Text وليس PostGIS geometry — أبسط وأسرع
  - /health/detailed عام (بدون auth) ليعمل مع أدوات المراقبة
  - /health/smtp يتطلب auth لأنه يحاول login على SMTP

- **الفجوات المتبقية:**
  - SMTP لم يُختبر مع خادم SMTP حقيقي (connection test endpoint جاهز)
  - PWA install prompt لم يُضف (المتصفح يعرض prompt تلقائياً)
  - PostGIS geometry column لا يزال غير مُستخدم (boundary_polygon JSON كافٍ)

---

### الدفعة: 2026-04-17T00:00 — Mobile Responsiveness + SMTP Hardening

**قبل البدء:**
- **الطابع الزمني:** 2026-04-17T00:00
- **فهم النظام الحالي:**
  - منصة إدارة مشروع دمّر مع واجهة عربية RTL، FastAPI backend + React 19 frontend
  - 48 اختبار ناجح، بناء الواجهة ناجح
  - RBAC مكتمل، نظام إشعارات (in-app + email templates) جاهز
  - SMTP مُعطّل بالافتراض، لم يُختبر مع خادم حقيقي
  - خريطة عمليات موحدة تعمل (شكاوى + مهام + مناطق)
  - الواجهة تستخدم Tailwind 4 لكن لا تحتوي على تحسينات mobile-first كافية
  - الجداول في صفحات القوائم (شكاوى/مهام/عقود) لا تتأقلم مع الشاشات الصغيرة
  - شريط التنقل يعرض كل العناصر أفقياً — يتطلب scroll على الجوال

- **أهداف هذه الدفعة:**
  1. تحسين تجربة الجوال عبر جميع الشاشات التشغيلية الرئيسية
  2. اختبار/تعزيز نظام SMTP مع خادم حقيقي
  3. تقوية سلوك البريد الإلكتروني (قوالب، حماية، منع التكرار)
  4. تحديث التوثيق

- **الملفات المخطط تعديلها:**
  - `src/components/Layout.tsx` — hamburger menu للجوال
  - `src/index.css` — mobile responsive utilities
  - `src/pages/ComplaintsListPage.tsx` — card view للجوال
  - `src/pages/TasksListPage.tsx` — card view للجوال
  - `src/pages/ContractsListPage.tsx` — card view للجوال
  - `src/pages/ComplaintDetailsPage.tsx` — responsive details
  - `src/pages/TaskDetailsPage.tsx` — responsive details
  - `src/pages/ContractDetailsPage.tsx` — responsive details
  - `src/pages/ReportsPage.tsx` — responsive filters + tables
  - `src/pages/ComplaintsMapPage.tsx` — mobile map layout
  - `src/pages/CitizenDashboardPage.tsx` — mobile adjustments
  - `src/pages/DashboardPage.tsx` — mobile adjustments
  - `backend/app/services/email_service.py` — SMTP hardening
  - `backend/tests/test_api.py` — SMTP verification tests
  - `PROJECT_REVIEW_AND_PROGRESS.md` — batch log
  - `HANDOFF_STATUS.md` — status update

- **المخاطر:**
  - تغيير Layout قد يؤثر على جميع الصفحات — يجب اختبار بناء الواجهة بعد كل تغيير
  - SMTP لن يُختبر مع خادم حقيقي في CI (بيئة sandboxed) — سيُوثّق كجزئي

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ Mobile Layout — hamburger menu للجوال مع قائمة منسدلة، اختفاء تلقائي عند تغيير الصفحة
  2. ✅ Mobile card views — ComplaintsListPage, TasksListPage, ContractsListPage تعرض بطاقات على الجوال بدلاً من جداول
  3. ✅ Responsive filters — فلاتر البحث تتكيف مع عرض الشاشة (column layout على الجوال)
  4. ✅ ReportsPage — فلاتر responsive، tabs 2-column على الجوال، جداول قابلة للتمرير أفقياً
  5. ✅ ContractDetailsPage — أزرار header responsive مع flex-wrap
  6. ✅ DashboardPage — حجم عنوان responsive
  7. ✅ ComplaintsMapPage — ارتفاع خريطة ديناميكي (calc), عنوان responsive
  8. ✅ SMTP hardening — TLS fallback (STARTTLS/SSL)، deduplication guard (5 min)، SSL context
  9. ✅ SMTP dedup tested — اختبارات وحدة تؤكد منع التكرار
  10. ✅ HTML escape verified — اختبار XSS prevention في قوالب البريد
  11. ✅ RTL template verified — اختبار أن قالب البريد يحتوي dir="rtl" و lang="ar"
  12. ✅ 52 اختبار ناجح (48 سابق + 4 جديد: dedup guard, dedup block, XSS escape, RTL template)
  13. ✅ بناء الواجهة ناجح (1.75s)
  14. ✅ Production deployment guide updated with SMTP hardening docs
- **القرارات الهندسية:**
  - Mobile nav: hamburger مع قائمة عمودية بدل scroll أفقي — أسهل للاستخدام الميداني
  - Card views: بطاقات تظهر فقط تحت 768px (md breakpoint) — الجداول تبقى على desktop
  - CSS approach: responsive-table-desktop / responsive-cards-mobile classes في index.css — بسيط ومباشر
  - SMTP dedup: 5 دقائق نافذة — توازن بين منع الضوضاء والسماح بتحديثات متعددة
  - TLS: port 465 = SMTP_SSL, port 587+ = STARTTLS — يتبع المعايير الصناعية
- **الفجوات المتبقية:**
  - SMTP لم يُختبر مع خادم SMTP حقيقي (الحماية والقوالب جاهزة، لم يُتحقق من التوصيل الفعلي)
  - PWA/offline mode لم يُنفذ بعد
  - area boundaries ثابتة في الكود

---

### الدفعة: 2026-04-16T22:59 — CI/CD, Production Guide, SMTP, GIS

**قبل البدء:**
- **الطابع الزمني:** 2026-04-16T22:59
- **فهم النظام الحالي:**
  - منصة إدارة مشروع دمّر مع واجهة عربية RTL، FastAPI backend + React 19 frontend
  - 38 اختبار ناجح، بناء الواجهة ناجح
  - RBAC مكتمل: citizen مقيد، 8 أدوار مستخدم
  - نظام إشعارات داخلي يعمل (in-app)، SMTP جاهز في الإعدادات لكن غير مُفعّل
  - خريطة شكاوى تعرض 7 شكاوى بإحداثيات — نقاط فقط بدون مناطق
  - لا يوجد CI/CD أو دليل نشر إنتاجي
  - لا يوجد إرسال بريد إلكتروني فعلي

- **أهداف هذه الدفعة:**
  1. إنشاء CI/CD pipeline (GitHub Actions) لاختبار الباكند وبناء الواجهة تلقائياً
  2. إنشاء دليل نشر إنتاجي شامل (PRODUCTION_DEPLOYMENT_GUIDE.md)
  3. تفعيل SMTP للإشعارات (شكاوى، مهام، عقود) بطريقة آمنة
  4. تحسين GIS — إضافة مناطق (polygons)، مهام على الخريطة، خريطة عمليات موحدة

- **الملفات المخطط تعديلها/إنشاؤها:**
  - `.github/workflows/ci.yml` — جديد
  - `PRODUCTION_DEPLOYMENT_GUIDE.md` — جديد
  - `backend/app/services/email_service.py` — جديد
  - `backend/app/api/gis.py` — جديد
  - `backend/alembic/versions/003_add_task_coordinates.py` — جديد
  - `backend/app/services/notification_service.py` — ربط البريد الإلكتروني
  - `backend/app/models/task.py` — إضافة lat/lng
  - `backend/app/schemas/task.py` — إضافة lat/lng
  - `backend/app/main.py` — تسجيل GIS router
  - `backend/app/scripts/seed_data.py` — إحداثيات للمهام
  - `backend/tests/test_api.py` — اختبارات GIS + email
  - `src/components/MapView.tsx` — دعم polygons + multi-type markers
  - `src/pages/ComplaintsMapPage.tsx` — خريطة عمليات موحدة
  - `src/services/api.ts` — endpoints جديدة للـ GIS
  - `README.md` — إضافة روابط للدليل و CI

- **المخاطر:**
  - SMTP قد لا يعمل بدون خادم SMTP حقيقي — مصمم للعمل بدون SMTP (fail-safe)
  - تغيير MapView قد يؤثر على الصفحات الأخرى — تم اختبار التوافق الخلفي

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ CI/CD pipeline — `.github/workflows/ci.yml` يعمل مع backend tests + frontend build
  2. ✅ دليل نشر إنتاجي — `PRODUCTION_DEPLOYMENT_GUIDE.md` شامل (14 قسم)
  3. ✅ SMTP email service — `email_service.py` مع 3 أنواع إشعارات بريد إلكتروني
  4. ✅ SMTP مربوط بـ notification_service — شكاوى، مهام، عقود
  5. ✅ SMTP fail-safe — لا يؤثر على العمليات الأساسية عند الفشل
  6. ✅ GIS API — `/gis/operations-map` و `/gis/area-boundaries` endpoints جديدة
  7. ✅ Task coordinates — lat/lng مضاف لنموذج المهام + migration 003
  8. ✅ خريطة عمليات موحدة — شكاوى + مهام مع تمييز بصري (دوائر vs مربعات)
  9. ✅ مناطق على الخريطة — 8 polygons لمناطق دمّر مع ألوان وتسميات
  10. ✅ 48 اختبار ناجح (38 سابق + 10 جديد)
  11. ✅ بناء الواجهة ناجح (1.83s)
  12. ✅ README محدّث مع روابط للدليل و CI

- **القرارات الهندسية:**
  - CI يستخدم SQLite in-memory (لا حاجة لـ PostgreSQL في CI) — أسرع وأبسط
  - SMTP يعمل فقط عند `SMTP_ENABLED=true` — آمن بالافتراض
  - email_service.py لا يستخدم مكتبات خارجية — smtplib مدمج في Python
  - area boundaries تُخزّن كبيانات ثابتة في gis.py (ليست في DB) — كافية للمرحلة الحالية
  - المهام تحتوي الآن على lat/lng — يمكن عرضها على الخريطة
  - ComplaintsMapPage أصبح خريطة عمليات موحدة — يعرض شكاوى + مهام + مناطق
  - Task markers تظهر كمربعات مائلة، complaint markers كدوائر — تمييز بصري واضح
  - HTML emails تستخدم html.escape لمنع XSS

- **الفجوات المتبقية:**
  - SMTP لم يُختبر مع خادم SMTP حقيقي (مصمم للعمل بشكل آمن عند الفشل)
  - area boundaries ثابتة في الكود — في المستقبل يمكن نقلها إلى PostGIS geometry
  - لا يوجد اختبار integration لـ SMTP مع خادم حقيقي
  - PWA/offline mode لم يُنفذ بعد
  - mobile responsiveness يحتاج تحسين

---

### الدفعة: 2026-04-16T22:23 — تعزيز الجاهزية النهائية وإكمال التكامل

**قبل البدء:**
- **الطابع الزمني:** 2026-04-16T22:23
- **فهم النظام الحالي:**
  - منصة إدارة مشروع دمّر مع واجهة عربية RTL
  - باكند FastAPI مع PostgreSQL/PostGIS، واجهة React 19 + Vite 8 + Tailwind 4
  - RBAC مُطبّق: citizen مُقيّد من endpoints تشغيلية، project_director يدير المستخدمين
  - Notification model موجود ومُصدّر، migration 002 جاهز لكن لم يُختبر على PostgreSQL حقيقي
  - إشعارات الشكاوى مربوطة، إشعارات المهام/العقود غير مربوطة بعد
  - لا يوجد حساب مواطن تجريبي في seed data
  - الشكاوى التجريبية لا تحتوي على إحداثيات (الخريطة فارغة)
  - /dashboard مفتوح لأي مستخدم مُصادق بما فيهم citizen
  - لا توجد اختبارات لمنع citizen من الوصول لـ endpoints المقيدة

- **أهداف هذه الدفعة:**
  1. اختبار Alembic migration على PostgreSQL حقيقي (Docker) وإصلاح أي مشاكل
  2. إضافة اختبارات RBAC لمنع citizen من الوصول لـ endpoints المقيدة
  3. تقييد /dashboard للموظفين الداخليين (القرار الأكثر أماناً)
  4. ربط إشعارات المهام والعقود (الدوال جاهزة، تحتاج تفعيل)
  5. إضافة حساب مواطن تجريبي + إحداثيات واقعية للشكاوى
  6. تحسين الشعور المهني للنظام

- **الملفات المخطط تعديلها:**
  - `backend/app/api/dashboard.py` — تقييد بـ internal staff
  - `backend/app/api/tasks.py` — ربط إشعارات المهام
  - `backend/app/api/contracts.py` — ربط إشعارات العقود
  - `backend/app/services/notification_service.py` — إضافة notify_contract_status_change
  - `backend/app/scripts/seed_data.py` — مواطن تجريبي + إحداثيات
  - `backend/tests/conftest.py` — fixture مواطن
  - `backend/tests/test_api.py` — اختبارات citizen denial
  - `src/App.tsx` — تقييد /dashboard بالدور

- **المخاطر:**
  - Docker PostgreSQL قد لا يكون متاحاً في بيئة CI
  - تقييد /dashboard قد يؤثر على citizen login redirect

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ Alembic migration على PostgreSQL حقيقي — `alembic upgrade head` نجح (001 + 002)
  2. ✅ جدول notifications مع FK + indexes على PostgreSQL — schema يطابق النموذج
  3. ✅ Seed data يعمل على PostgreSQL — 8 مستخدمين، 8 مناطق، 12 مبنى، 7 شكاوى، 5 مهام، 5 عقود
  4. ✅ اختبارات citizen denial — 11 اختبار يؤكد منع citizen من:
     - `/complaints/` `/complaints/{id}` `/tasks/` `/tasks/{id}` `/contracts/` `/contracts/{id}`
     - `/reports/summary` `/users/` `/dashboard/stats` `/dashboard/recent-activity` `/complaints/map/markers`
  5. ✅ اختبار citizen CAN access — `/citizen/my-complaints` يعود 200
  6. ✅ /dashboard مقيد بـ internal staff — باكند: `get_current_internal_user`، واجهة: `RoleProtectedRoute`
  7. ✅ citizen يُحوّل لـ /citizen بدل /dashboard عند محاولة الوصول لصفحة مقيدة
  8. ✅ إشعارات المهام مربوطة — create_task وupdate_task يرسلان إشعاراً عند الإسناد
  9. ✅ إشعارات العقود مربوطة — approve_contract يرسل إشعاراً لمديري العقود والمدير
  10. ✅ حساب مواطن تجريبي — citizen1 بهاتف +963911234567 (يطابق شكوى CMP00000001)
  11. ✅ إحداثيات واقعية — جميع الشكاوى السبع تحتوي lat/lng في منطقة دمّر
  12. ✅ 38 اختبار ناجح (26 سابق + 12 جديد)
  13. ✅ بناء الواجهة — npm run build ناجح (1.85s)
  14. ✅ README محدّث — حساب citizen1 موثق
- **القرارات الهندسية:**
  - /dashboard و /dashboard/stats و /dashboard/recent-activity مقيدة بـ internal staff (القرار الأكثر أماناً — citizen يحتوي على بيانات تشغيلية)
  - /settings تبقى مفتوحة لأي مُصادق (سلوك مقصود — إعدادات شخصية)
  - إشعارات العقود تُرسل لجميع مديري العقود والمدير (ليس فقط المُنشئ)
  - notify_task_assigned لا يُرسل إشعاراً إذا assigned_to == current_user (لتجنب الضوضاء)
- **الفجوات المتبقية:**
  - إرسال بريد إلكتروني فعلي (SMTP) — الأساس جاهز لكن غير مُفعّل
  - Alembic migration لم يُختبر تلقائياً في CI/CD (تم يدوياً في هذه الدفعة)
  - لا توجد اختبارات وحدة لـ notification_service.py (الاختبارات الحالية تختبر الـ API)

---

### الدفعة: 2026-04-16T21:44 — 5 إصلاحات حرجة لتعزيز الثقة في MVP

**قبل البدء:**
- **الطابع الزمني:** 2026-04-16T21:44
- **الهدف:** تنفيذ 5 إصلاحات حرجة لجعل MVP أكثر موثوقية للعرض والمراجعة
- **المشاكل المستهدفة:**
  1. إكمال قاعدة بيانات الإشعارات — Notification غير مُصدّر في `__init__.py`، لا يوجد migration مخصص
  2. تقوية RBAC — بعض endpoints GET الحساسة متاحة لأي مستخدم مُصادق، مسارات الواجهة غير مقيدة بالدور
  3. نقل API base URL إلى env config — لا يزال hardcoded `localhost:8000`
  4. إزالة بقايا Spark — نصوص Spark في ErrorFallback، ملفات spark.meta.json
  5. استقرار بيئة الاختبار — مشاكل توافق passlib/bcrypt
- **الملفات المخطط تعديلها:**
  - `backend/app/models/__init__.py`
  - `backend/alembic/versions/002_add_notifications.py` (جديد)
  - `backend/app/api/users.py`
  - `backend/app/api/reports.py`
  - `backend/app/api/contracts.py`
  - `backend/app/api/tasks.py`
  - `backend/app/api/complaints.py`
  - `backend/app/api/locations.py`
  - `backend/requirements.txt`
  - `src/App.tsx`
  - `src/services/api.ts`
  - `src/components/FileUpload.tsx`
  - `src/pages/ContractDetailsPage.tsx`
  - `src/ErrorFallback.tsx`
  - `.env.example` (frontend — جديد)
  - `README.md`
  - `spark.meta.json` (حذف)
  - `.spark-initial-sha` (حذف)
  - `runtime.config.json` (حذف)
- **المخاطر:** تغيير RBAC قد يؤثر على اختبارات RBAC الحالية — يجب التأكد من بقاء الاختبارات ناجحة

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ إكمال قاعدة بيانات الإشعارات — `Notification` و `NotificationType` مُصدّران في `__init__.py`، migration `002_add_notifications.py` جاهز
  2. ✅ تقوية RBAC على الباكند — `get_current_internal_user` dep جديد يستبعد citizen، مطبّق على:
     - `GET /users/` و `/users/{id}` → project_director فقط
     - `GET /complaints/` و `/complaints/{id}` و `/complaints/map/markers` و `/complaints/{id}/activities` → internal staff
     - `GET /tasks/` و `/tasks/{id}` و `/tasks/{id}/activities` → internal staff
     - `GET /contracts/` و `/contracts/{id}` و `/contracts/expiring-soon` و `/contracts/{id}/approvals` و `generate-pdf` → internal staff
     - جميع نقاط التقارير → internal staff
  3. ✅ تقوية RBAC على الواجهة — `App.tsx` يقيد المسارات بالدور:
     - `/citizen` → citizen فقط
     - `/complaints` `/tasks` `/contracts` `/locations` `/complaints-map` → internal staff
     - `/users` → project_director
     - `/reports` → أدوار إدارية (بدون citizen, field_team, contractor)
  4. ✅ نقل API base URL — `src/config.ts` مع `VITE_API_BASE_URL`، مستخدم في `api.ts` و `FileUpload.tsx` و `ContractDetailsPage.tsx`
  5. ✅ إزالة بقايا Spark — `ErrorFallback.tsx` بنصوص عربية، حذف `spark.meta.json` و `.spark-initial-sha` و `runtime.config.json`
  6. ✅ استقرار الاختبارات — `bcrypt==3.2.2` مُثبّت في `requirements.txt`، 26 اختبار ناجح
  7. ✅ بناء الواجهة — `npm run build` ناجح (1.69s)
  8. ✅ `README.md` محدّث — تعليمات env، اختبارات، إزالة register endpoint
  9. ✅ `.env.example` للواجهة — مع `VITE_API_BASE_URL`
- **الفجوات المتبقية:**
  - لم يُعدّل `locations.py` — المواقع بيانات مرجعية يمكن للجميع رؤيتها (سلوك مقصود)
  - اختبار Alembic migration على PostgreSQL الحقيقي لم يتم (SQLite فقط) — يحتاج بيئة Docker
  - لوحة المعلومات `/dashboard` و `/settings` لا تزال مفتوحة لأي مستخدم مُصادق (سلوك مقصود لسهولة الاستخدام)

---

### الدفعة: 2026-04-16T21:10 — المرحلة الثانية: لوحة تحكم المواطن + إشعارات + خرائط GIS

**قبل البدء:**
- **الهدف:** بناء ميزات المرحلة الثانية ذات القيمة المباشرة للمستخدم
- **المهام المخططة:**
  1. لوحة تحكم المواطن — صفحة مُسجّل دخول تعرض شكاوى المواطن وحالاتها
  2. أساس الإشعارات — نموذج إشعارات + خدمة + واجهة API + ربط مع تغيير حالة الشكوى
  3. تكامل خرائط GIS — مكون خريطة Leaflet يعرض مواقع الشكاوى على خريطة
  4. تحسين الشعور التشغيلي — تسميات، هيكل تنقل، تناسق
- **الملفات المتأثرة:**
  - `backend/app/models/notification.py` — نموذج إشعارات جديد
  - `backend/app/schemas/notification.py` — مخططات إشعارات
  - `backend/app/api/notifications.py` — نقاط API للإشعارات
  - `backend/app/services/notification_service.py` — خدمة إشعارات
  - `backend/app/api/complaints.py` — ربط إشعارات مع تغيير حالة الشكوى
  - `backend/app/api/deps.py` — dependency لمواطن
  - `backend/app/main.py` — تسجيل router الإشعارات
  - `backend/app/core/config.py` — إعدادات البريد الإلكتروني
  - `src/pages/CitizenDashboardPage.tsx` — صفحة لوحة تحكم المواطن
  - `src/pages/ComplaintsMapPage.tsx` — صفحة خريطة الشكاوى
  - `src/components/NotificationBell.tsx` — مكون جرس الإشعارات
  - `src/components/MapView.tsx` — مكون الخريطة
  - `src/components/Layout.tsx` — تحديث التنقل
  - `src/services/api.ts` — إضافة API الإشعارات والخريطة
  - `src/App.tsx` — مسارات جديدة
  - `package.json` — إضافة leaflet
- **المخاطر:** لا مخاطر كبيرة — ميزات إضافية متوافقة مع الوراء

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ لوحة تحكم المواطن — `/citizen` تعرض شكاوى المواطن المُسجّل حسب رقم الهاتف مع فلترة حسب الحالة
  2. ✅ نقطة API المواطن — `GET /complaints/citizen/my-complaints` تُرجع شكاوى المواطن مع ترقيم
  3. ✅ نظام إشعارات — نموذج `Notification` + خدمة + 3 نقاط API (`GET /notifications/`, `POST /mark-read`, `POST /mark-all-read`)
  4. ✅ ربط إشعارات — تغيير حالة الشكوى يُنشئ إشعارات تلقائياً للمسؤولين والمُعيّن
  5. ✅ خريطة GIS — `/complaints-map` تعرض شكاوى بإحداثيات على خريطة Leaflet مع علامات ملونة حسب الحالة
  6. ✅ نقطة API الخريطة — `GET /complaints/map/markers` تُرجع شكاوى بإحداثيات مع فلترة
  7. ✅ مكون MapView — قابل لإعادة الاستخدام مع علامات ملونة ونوافذ منبثقة
  8. ✅ جرس الإشعارات — مكون `NotificationBell` مع polling كل 30 ثانية وعدّاد غير مقروء
  9. ✅ تنقل محسّن — المواطن يرى "شكاواي"، الإدارة ترى القائمة الكاملة، خريطة الشكاوى متاحة للجميع
  10. ✅ بناء الواجهة — `npm run build` ناجح (1.84s)
  11. ✅ اختبارات API — 26 اختبار ناجح (جميع الاختبارات السابقة تمر)
  12. ✅ تجميع Python — جميع الملفات الجديدة تُجمع بنجاح
  13. ✅ إعدادات بريد إلكتروني — متغيرات SMTP في config.py (معطلة افتراضياً — جاهزة للتفعيل)
- **الفجوات المتبقية:**
  - إرسال بريد إلكتروني فعلي (SMTP) — الأساس جاهز لكن غير مُفعّل
  - إشعارات المهام والعقود — الخدمة جاهزة لكن الربط يحتاج تنفيذ في tasks.py/contracts.py
  - بيانات إحداثيات تجريبية — الشكاوى الحالية قد لا تحتوي على lat/lng
  - حساب مواطن تجريبي — يحتاج إنشاء بواسطة المدير

---

### الدفعة: 2026-04-16T20:39 — تحسين التشغيل والتقارير والاختبارات والأداء

**قبل البدء:**
- **الهدف:** تحسين الاكتمال التشغيلي وفائدة التقارير وتغطية الاختبارات وأداء الواجهة
- **المهام المخططة:**
  1. إضافة تصدير CSV من صفحة التقارير (نقطة API + أزرار تنزيل على الواجهة)
  2. إضافة اختبارات API أساسية للتدفقات الحرجة (أمان + RBAC + أشكال بيانات)
  3. تطبيق ترقيم صفحات حقيقي على نقاط الشكاوى/المهام/العقود
  4. تحسين فائدة التقارير (فلاتر إضافية: نوع الشكوى، نوع العقد، الأولوية، المسؤول)
  5. إضافة تقسيم الكود وتحميل كسول للمسارات الرئيسية
- **الملفات المتأثرة:**
  - `backend/app/api/reports.py` — إضافة نقطة CSV
  - `backend/app/api/complaints.py` — ترقيم صفحات مع total_count
  - `backend/app/api/tasks.py` — ترقيم صفحات مع total_count
  - `backend/app/api/contracts.py` — ترقيم صفحات مع total_count
  - `backend/app/schemas/report.py` — مخططات ترقيم إضافية
  - `backend/tests/` — اختبارات API جديدة
  - `backend/requirements.txt` — إضافة pytest + httpx
  - `src/pages/ReportsPage.tsx` — تصدير CSV + فلاتر إضافية
  - `src/pages/ComplaintsListPage.tsx` — ترقيم من الخادم
  - `src/pages/TasksListPage.tsx` — ترقيم من الخادم
  - `src/pages/ContractsListPage.tsx` — ترقيم من الخادم
  - `src/services/api.ts` — تحديث دوال API
  - `src/App.tsx` — تحميل كسول للصفحات
- **المخاطر:** لا مخاطر كبيرة — تغييرات إضافية متوافقة مع الوراء

**بعد الانتهاء:**
- **النتيجة:** ✅ Done
- **التحقق:**
  1. ✅ تصدير CSV — 3 نقاط API تعمل (complaints/tasks/contracts CSV) + أزرار تنزيل على الواجهة
  2. ✅ اختبارات API — 26 اختبار ناجح (pytest) تغطي: أمان، RBAC، بيانات ملفات، تقارير، ترقيم، CSV
  3. ✅ ترقيم صفحات — complaints/tasks/contracts list endpoints ترجع `{total_count, items}` + الواجهة تستخدم server-side pagination
  4. ✅ فلاتر تقارير — نوع الشكوى، نوع العقد، الأولوية، الحالة، المنطقة، التاريخ
  5. ✅ code splitting — React.lazy + Suspense لـ 14 صفحة — حزم منفصلة
  6. ✅ بناء الواجهة — `npm run build` ناجح (1.41s)
  7. ✅ بحث server-side — complaints/tasks/contracts تدعم بحث من الخادم
- **الفجوات المتبقية:** لا فجوات — جميع المهام مكتملة ومتحقق منها

---

### الدفعة: 2026-04-16T20:09 — تعزيز الأمان و RBAC على الواجهة الأمامية

**قبل البدء:**
- **الهدف:** تعزيز الأمان (rate limiting، تنظيف CORS، تحذير كلمات المرور الافتراضية) وتطبيق RBAC على واجهة المستخدم
- **المشاكل المعالجة:**
  1. لا يوجد rate limiting على نقاط النهاية العامة — عرضة للإساءة
  2. CORS مثبت يدوياً لـ localhost فقط — غير مرن للنشر
  3. لا تحذير عند استخدام كلمات المرور الافتراضية الضعيفة
  4. الواجهة تعرض جميع الصفحات والأزرار لجميع المستخدمين بغض النظر عن الدور
  5. التحقق من RBAC على الخادم لا يزال صحيحاً
- **الملفات المخطط تعديلها:**
  - `backend/requirements.txt` — إضافة slowapi
  - `backend/app/core/config.py` — إضافة CORS_ORIGINS
  - `backend/app/main.py` — CORS من متغيرات البيئة + rate limiter + تحذير بدء التشغيل
  - `backend/app/api/uploads.py` — rate limiting على /uploads/public
  - `backend/app/api/complaints.py` — rate limiting على /complaints/ و /complaints/track
  - `backend/app/scripts/seed_data.py` — تحذير كلمات المرور الافتراضية
  - `backend/.env.example` — إضافة CORS_ORIGINS
  - `docker-compose.yml` — إضافة CORS_ORIGINS
  - `src/hooks/useAuth.ts` — هوك مصادقة جديد
  - `src/components/RoleGuard.tsx` — مكون حماية الأدوار
  - `src/components/Layout.tsx` — فلترة القائمة حسب الدور
  - `src/App.tsx` — حماية المسارات حسب الدور
  - `src/pages/ComplaintDetailsPage.tsx` — إخفاء أزرار التحديث
  - `src/pages/TaskDetailsPage.tsx` — إخفاء أزرار التحديث
  - `src/pages/ContractDetailsPage.tsx` — إخفاء أزرار الحذف/PDF
  - `src/services/api.ts` — تخزين بيانات المستخدم عند الدخول
- **المخاطر:** لا مخاطر كبيرة — تغييرات إضافية فقط

**النتائج:**
- ✅ Rate limiting: `/uploads/public` (10/دقيقة)، `/complaints/` إنشاء (5/دقيقة)، `/complaints/track` (10/دقيقة)
- ✅ CORS: الأصول تُقرأ من متغير `CORS_ORIGINS` (قيمة افتراضية: localhost:5173,localhost:3000)
- ✅ تحذير كلمات المرور: يُعرض عند seed وعند بدء تشغيل الخادم
- ✅ RBAC واجهة: صفحة المستخدمين مخفية لغير المدير، أزرار التحديث مخفية لغير المسؤولين
- ✅ RBAC خادم: لا تغيير — لا يزال يُطبق correctly
- ✅ بناء الواجهة: `npm run build` ناجح (604 KB)
- ✅ تجميع Python: جميع الملفات تُجمع بنجاح

---

### الدفعة: 2026-04-16 — إصلاحات أمنية وتشغيلية حرجة
**الهدف:** تنفيذ 6 إصلاحات حرجة لتحسين الأمان والتشغيل  
**المشاكل المعالجة:**
1. ثغرة أمنية في `/auth/register` تسمح بإنشاء حسابات مميزة بشكل عام
2. فشل بناء الواجهة الأمامية بسبب تعريفات شاشات غير صالحة في tailwind
3. عدم عمل رفع ملفات الشكاوى العامة (يتطلب مصادقة)
4. عدم اتساق شكل بيانات الملفات بين الخادم والواجهة
5. عدم دقة وثائق تتبع المشروع
6. ضعف التحكم بالوصول على نقاط النهاية الحساسة

**الملفات المتأثرة:**
- `backend/app/api/auth.py` — إزالة نقطة تسجيل عامة
- `backend/app/api/complaints.py` — RBAC + تسلسل ملفات
- `backend/app/api/tasks.py` — RBAC + تسلسل ملفات
- `backend/app/api/contracts.py` — تسلسل ملفات
- `backend/app/api/uploads.py` — نقطة رفع عامة آمنة
- `backend/app/schemas/complaint.py` — حقول ملفات كمصفوفات
- `backend/app/schemas/task.py` — حقول ملفات كمصفوفات
- `backend/app/schemas/contract.py` — حقول ملفات كمصفوفات
- `tailwind.config.js` — إزالة شاشات غير صالحة
- `src/services/api.ts` — إضافة رفع ملفات عام
- `src/pages/ComplaintSubmitPage.tsx` — استخدام رفع عام
- `src/pages/ComplaintDetailsPage.tsx` — تحديث استخدام الصور
- `PROJECT_REVIEW_AND_PROGRESS.md` — تحديث صادق
- `HANDOFF_STATUS.md` — تحديث صادق

**النتائج:**
- ✅ P1: `/auth/register` محذوفة — إنشاء المستخدمين فقط عبر `/users/` بواسطة المدير
- ✅ P2: `npm run build` ناجح — إزالة شاشات coarse/fine/pwa
- ✅ P3: رفع الشكاوى العامة يعمل عبر `/uploads/public`
- ✅ P4: حقول الملفات تُرجع كمصفوفات JSON عبر API
- ✅ P5: وثائق المشروع مُحدّثة بصدق
- ✅ P6: RBAC مُطبق على شكاوى ومهام

---

## الميزات المنجزة بالكامل ✅

### الواجهة الخلفية (Backend - FastAPI)
- [x] نظام مصادقة JWT كامل مع أدوار مستخدمين (8 أدوار تشمل citizen)
- [x] CRUD كامل للشكاوى مع رقم تتبع تلقائي
- [x] CRUD كامل للمهام مع ربط بالشكاوى/العقود
- [x] CRUD كامل للعقود مع نظام موافقات
- [x] إدارة المناطق والمباني (8 مناطق، 12 مبنى)
- [x] لوحة تحكم إحصائية مع نشاطات حديثة
- [x] نظام رفع الملفات مع تصنيف (مع نقطة رفع عامة للشكاوى)
- [x] إنشاء PDF للعقود مع QR code
- [x] سجل تدقيق لجميع العمليات
- [x] نقاط API للتقارير مع فلاتر شاملة
- [x] بحث وفلترة متقدمة على المستخدمين
- [x] بيانات تجريبية واقعية
- [x] تسجيل عام مغلق — إنشاء المستخدمين فقط بواسطة مدير المشروع
- [x] RBAC على نقاط النهاية الحساسة (شكاوى، مهام، عقود، مستخدمين)
- [x] حقول الملفات (صور، مرفقات، صور قبل/بعد) تُرجع كمصفوفات JSON
- [x] Rate limiting على نقاط النهاية العامة (slowapi)
- [x] CORS من متغيرات بيئة (CORS_ORIGINS)
- [x] تحذير كلمات المرور الافتراضية عند seed وبدء التشغيل
- [x] نظام إشعارات داخلية (in-app) — نموذج + خدمة + API
- [x] ربط إشعارات تلقائي مع تغيير حالة الشكوى
- [x] نقطة API لشكاوى المواطن (`/complaints/citizen/my-complaints`)
- [x] نقطة API لعلامات الخريطة (`/complaints/map/markers`)
- [x] إعدادات SMTP في config (معطلة افتراضياً — جاهزة للتفعيل)

### الواجهة الأمامية (Frontend - React 19 + Vite)
- [x] واجهة RTL عربية كاملة (خط Cairo)
- [x] صفحة تسجيل الدخول
- [x] لوحة تحكم بإحصائيات حية
- [x] قائمة الشكاوى مع بحث وفلترة وترقيم
- [x] تفاصيل الشكوى مع مرفقات وسجل نشاطات
- [x] تقديم شكوى عامة مع رفع ملفات (بدون تسجيل دخول)
- [x] تتبع الشكوى بالرقم والهاتف
- [x] قائمة المهام مع بحث وفلترة
- [x] تفاصيل المهمة مع صور قبل/بعد
- [x] قائمة العقود مع بحث وفلترة
- [x] تفاصيل العقد مع مرفقات و PDF
- [x] صفحة المواقع
- [x] صفحة إدارة المستخدمين
- [x] صفحة التقارير
- [x] صفحة الإعدادات
- [x] مكون رفع ملفات مع تحقق
- [x] RBAC على واجهة المستخدم (إخفاء صفحات وأزرار حسب الدور)
- [x] هوك مصادقة `useAuth()` ومكون `RoleGuard`
- [x] `npm run build` ناجح (604 KB)
- [x] لوحة تحكم المواطن — صفحة `/citizen` مع عرض شكاوى المواطن وفلترة وتفاصيل
- [x] خريطة الشكاوى — صفحة `/complaints-map` مع Leaflet وعلامات ملونة حسب الحالة
- [x] مكون `MapView` قابل لإعادة الاستخدام
- [x] مكون `NotificationBell` مع polling وعدّاد غير مقروء
- [x] تنقل محسّن — المواطن يرى "شكاواي"، الإدارة ترى القائمة الكاملة

---

## الحالة الحقيقية المُتحقق منها

| المكون | الحالة | ملاحظات |
|---|---|---|
| بناء الواجهة (npm run build) | ✅ ناجح | 1.84s build |
| تجميع الخادم (python compile) | ✅ ناجح | جميع ملفات API و schemas تُجمع بنجاح |
| اختبارات API (pytest) | ✅ ناجح | 26 اختبار ناجح |
| أمان التسجيل | ✅ مُصلح | `/auth/register` محذوفة — الإنشاء فقط عبر `/users/` بصلاحيات مدير |
| رفع ملفات الشكاوى العامة | ✅ مُصلح | `/uploads/public` متاح بدون مصادقة |
| Rate limiting | ✅ مُطبق | `/uploads/public` 10/min، `/complaints/` 5/min، `/complaints/track` 10/min |
| CORS من متغيرات البيئة | ✅ مُطبق | `CORS_ORIGINS` env var — قيمة افتراضية: localhost |
| تحذير كلمات المرور الافتراضية | ✅ مُطبق | عند seed وعند بدء تشغيل الخادم |
| RBAC — واجهة المستخدم | ✅ مُطبق | إخفاء صفحات وأزرار حسب الدور |
| RBAC — تحديث الشكاوى | ✅ مُصلح | مقيد بالمدير والمسؤولين |
| RBAC — إنشاء/تحديث/حذف المهام | ✅ مُصلح | مقيد بالمدير والمشرفين |
| RBAC — العقود | ✅ كان مُطبق | مقيد بمدير العقود والمدير |
| RBAC — المستخدمين | ✅ كان مُطبق | مقيد بمدير المشروع |
| لوحة تحكم المواطن | ✅ مُنفذ | `/citizen` — شكاوى المواطن مع فلترة |
| إشعارات داخلية | ✅ مُنفذ | نموذج + خدمة + API + ربط مع تغيير حالة الشكوى |
| خريطة الشكاوى GIS | ✅ مُنفذ | `/complaints-map` — Leaflet + علامات ملونة |
| جرس الإشعارات | ✅ مُنفذ | polling كل 30 ثانية + عدّاد غير مقروء |
| تصدير CSV | ✅ مُنفذ | 3 نقاط API |
| إشعارات بريد إلكتروني | ⚠️ جزئي | أساس SMTP جاهز — معطل افتراضياً |

---

## حالة الخادم والبناء
- الخادم الخلفي: `uvicorn app.main:app --reload --port 8000`
- الواجهة الأمامية: `npm run build` ← **ناجح** (تم التحقق 2026-04-16)
- Docker Compose: `docker compose up` للتشغيل الكامل

---

## بيانات تجريبية
### حسابات الدخول:
| المستخدم | كلمة المرور | الدور |
|---|---|---|
| director | password123 | مدير المشروع |
| contracts_mgr | password123 | مدير العقود |
| engineer | password123 | مشرف هندسي |
| complaints_off | password123 | مسؤول الشكاوى |
| area_sup | password123 | مشرف المنطقة |
| field_user | password123 | فريق ميداني |
| contractor | password123 | مستخدم مقاول |

⚠️ ملاحظة: لا يوجد تسجيل عام — إنشاء المستخدمين فقط بواسطة مدير المشروع عبر `/users/`

---

## الثغرات المتبقية (المرحلة التالية)
- [ ] إرسال بريد إلكتروني فعلي (SMTP) — الأساس جاهز لكن غير مُفعّل
- [ ] إشعارات المهام والعقود — الخدمة جاهزة لكن الربط يحتاج تنفيذ
- [ ] وضع عدم الاتصال (PWA/offline mode)
- [ ] تحسين تجربة الجوال (mobile responsiveness)
- [ ] نشر على خادم إنتاج
- [ ] اختبارات وحدة وتكامل إضافية
- [ ] بيانات إحداثيات تجريبية للشكاوى (لعرض علامات على الخريطة)
- [ ] حساب مواطن تجريبي في seed data
- [ ] تكامل GIS متقدم — عرض جزر/مباني/مناطق على الخريطة
