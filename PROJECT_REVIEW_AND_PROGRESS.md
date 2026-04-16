# مراجعة المشروع وتقدم العمل
# PROJECT_REVIEW_AND_PROGRESS.md

## نظرة عامة على المشروع
**الاسم:** منصة إدارة مشروع دمّر  
**الغرض:** نظام إدارة شكاوى، مهام، وعقود لمشروع دمّر السكني في دمشق  
**المرحلة الحالية:** المرحلة الثالثة - تجهيز الإنتاج  
**آخر تحديث:** 2026-04-17

---

## سجل الدفعات (Batch Log)

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
