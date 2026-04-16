# حالة التسليم
# HANDOFF_STATUS.md

## آخر تحديث: 2026-04-16T21:44

---

## الدفعة الحالية: 2026-04-16T21:44 — 5 إصلاحات حرجة لتعزيز الثقة في MVP

### الملفات المُعدّلة/الجديدة في هذه الدفعة:
| الملف | التغيير |
|---|---|
| `backend/app/models/__init__.py` | إضافة `Notification` و `NotificationType` للتصدير |
| `backend/alembic/versions/002_add_notifications.py` | **جديد** — Alembic migration لجدول notifications |
| `backend/app/api/deps.py` | إضافة `get_current_internal_user` — يستبعد citizen |
| `backend/app/api/users.py` | تقييد `GET /users/` و `/users/{id}` بـ project_director |
| `backend/app/api/complaints.py` | تقييد GET endpoints بـ internal staff (citizen يستخدم `/citizen/my-complaints`) |
| `backend/app/api/tasks.py` | تقييد GET endpoints بـ internal staff |
| `backend/app/api/contracts.py` | تقييد GET endpoints بـ internal staff |
| `backend/app/api/reports.py` | تقييد جميع نقاط التقارير بـ internal staff |
| `backend/requirements.txt` | تثبيت `bcrypt==3.2.2` لتوافق passlib |
| `src/config.ts` | **جديد** — تكوين API base URL من متغير بيئة |
| `src/services/api.ts` | استخدام `config.API_BASE_URL` بدل hardcoded URL |
| `src/components/FileUpload.tsx` | استخدام `config.API_BASE_URL` |
| `src/pages/ContractDetailsPage.tsx` | استخدام `config.API_BASE_URL` |
| `src/App.tsx` | تقوية route guards — تقييد المسارات حسب الدور |
| `src/ErrorFallback.tsx` | إزالة نصوص Spark، استبدال بنصوص عربية |
| `src/styles/theme.css` | إزالة ذكر Spark من التعليق |
| `.env.example` | **جديد** — متغيرات بيئة الواجهة |
| `README.md` | تحديث — تعليمات env، اختبارات، إزالة register endpoint |
| `spark.meta.json` | **محذوف** |
| `.spark-initial-sha` | **محذوف** |
| `runtime.config.json` | **محذوف** |

---

## الحالة الحقيقية المُتحقق منها

### ✅ مكتمل ومُتحقق منه:
1. **إكمال قاعدة بيانات الإشعارات** — `Notification` مُصدّر في `__init__.py`، migration `002` جاهز، env.py يكتشف النموذج
2. **تقوية RBAC على الباكند** — citizens لا يستطيعون الوصول لـ `/complaints/` `/tasks/` `/contracts/` `/reports/` `/users/`
3. **تقوية RBAC على الواجهة** — route guards في App.tsx تقيد المسارات حسب الدور
4. **نقل API base URL** — `VITE_API_BASE_URL` في `src/config.ts` يُستخدم في جميع الملفات
5. **إزالة بقايا Spark** — `ErrorFallback.tsx` بنصوص عربية، ملفات Spark محذوفة
6. **استقرار بيئة الاختبار** — `bcrypt==3.2.2` مُثبّت، 26 اختبار ناجح
7. **بناء الواجهة** — `npm run build` ناجح (1.69s)
8. **README محدّث** — تعليمات بيئة، اختبارات، توثيق bcrypt pin

### ⚠️ جزئي:
- **اختبار migration على PostgreSQL** — migration جاهز لكن لم يُختبر على PostgreSQL حقيقي (SQLite في الاختبارات)
- **إشعارات البريد الإلكتروني** — إعدادات SMTP جاهزة في config لكن غير مُفعّلة
- **إشعارات المهام/العقود** — دالة `notify_task_assigned` جاهزة لكن لم تُربط بـ tasks.py بعد

### ❌ غير مُنفذ (المرحلة التالية):
- PWA/offline mode
- تكامل GIS متقدم — جزر/مباني/مناطق على الخريطة
- حساب مواطن تجريبي في seed data
- بيانات إحداثيات تجريبية للشكاوى

### ⚠️ ملاحظات مهمة:
- كلمات المرور التجريبية يجب تغييرها في الإنتاج — الخادم يحذر عند البدء
- CORS يُقرأ من `CORS_ORIGINS` env var — يجب تحديثه عند النشر
- `field_team` و `contractor_user` لا يمكنهم تحديث الشكاوى أو المهام (سلوك مقصود)
- `citizen` لا يمكنه الوصول لصفحات إدارية — يُحوّل تلقائياً إلى `/dashboard`
- لاستخدام لوحة تحكم المواطن، يجب إنشاء حساب مواطن عبر `/users/` بواسطة المدير
- خريطة الشكاوى تعرض فقط الشكاوى التي تحتوي على إحداثيات (latitude/longitude)
- `bcrypt==3.2.2` مُثبّت لتوافق `passlib==1.7.4` — لا تحدّث بدون اختبار

---

## الدفعات السابقة

### الدفعة: 2026-04-16T21:10 — المرحلة الثانية: لوحة تحكم المواطن + إشعارات + خرائط GIS
**الملفات المعدلة:** `backend/app/models/notification.py`, `backend/app/schemas/notification.py`, `backend/app/services/notification_service.py`, `backend/app/api/notifications.py`, `backend/app/api/complaints.py`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/.env.example`, `src/pages/CitizenDashboardPage.tsx`, `src/pages/ComplaintsMapPage.tsx`, `src/components/MapView.tsx`, `src/components/NotificationBell.tsx`, `src/components/Layout.tsx`, `src/services/api.ts`, `src/App.tsx`, `package.json`

---

## الدفعة القادمة المُقترحة
1. اختبار Alembic migration على PostgreSQL حقيقي (Docker)
2. إضافة اختبارات RBAC جديدة — citizen لا يستطيع الوصول لـ endpoints المقيدة
3. إرسال بريد إلكتروني فعلي عبر SMTP (تفعيل أساس الإشعارات الموجود)
4. ربط إشعارات المهام والعقود (دوال جاهزة في notification_service.py)
5. حساب مواطن تجريبي + بيانات إحداثيات تجريبية
6. تكامل GIS متقدم — عرض جزر/مباني/مناطق على الخريطة
7. PWA/offline mode
8. تحسين تجربة الجوال (mobile responsiveness)
9. نشر على خادم إنتاج
