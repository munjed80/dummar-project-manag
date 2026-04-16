# حالة التسليم
# HANDOFF_STATUS.md

## آخر تحديث: 2026-04-16T20:09

---

## الدفعة الحالية: 2026-04-16T20:09 — تعزيز الأمان و RBAC على الواجهة الأمامية

### الملفات المُعدّلة في هذه الدفعة:
| الملف | التغيير |
|---|---|
| `backend/requirements.txt` | إضافة `slowapi==0.1.9` |
| `backend/app/core/config.py` | إضافة `CORS_ORIGINS` env var مع `get_cors_origins()` |
| `backend/app/main.py` | CORS من env vars + rate limiter (slowapi) + تحذير كلمات المرور عند بدء التشغيل |
| `backend/app/api/uploads.py` | rate limiting `10/minute` على `/uploads/public` |
| `backend/app/api/complaints.py` | rate limiting `5/minute` على `POST /complaints/` و `10/minute` على `/complaints/track` |
| `backend/app/scripts/seed_data.py` | `check_default_passwords()` — تحذير كلمات المرور الافتراضية عند seed وبدء التشغيل |
| `backend/.env.example` | إضافة `CORS_ORIGINS` |
| `docker-compose.yml` | إضافة `CORS_ORIGINS` env var |
| `src/hooks/useAuth.ts` | هوك مصادقة جديد — دور المستخدم + صلاحيات (canManageComplaints/Tasks/Contracts/Users) |
| `src/components/RoleGuard.tsx` | مكون حماية أدوار قابل لإعادة الاستخدام |
| `src/components/Layout.tsx` | فلترة عناصر القائمة حسب الدور (المستخدمون لمدير المشروع فقط) |
| `src/App.tsx` | `RoleProtectedRoute` — حماية `/users` بدور project_director |
| `src/pages/ComplaintDetailsPage.tsx` | إخفاء بطاقة "تحديث الشكوى" لغير المسؤولين |
| `src/pages/TaskDetailsPage.tsx` | إخفاء بطاقة "تحديث المهمة" لغير المسؤولين |
| `src/pages/ContractDetailsPage.tsx` | إخفاء أزرار "إنشاء PDF" و "حذف" لغير مدير العقود/المدير |
| `src/services/api.ts` | تخزين بيانات المستخدم في localStorage عند الدخول + مسحها عند الخروج |

---

## الحالة الحقيقية المُتحقق منها

### ✅ مكتمل ومُتحقق منه:
1. **Rate limiting** — `/uploads/public` (10/min)، `POST /complaints/` (5/min)، `/complaints/track` (10/min)
2. **CORS من env vars** — `CORS_ORIGINS` env var، قيمة افتراضية `localhost:5173,localhost:3000`
3. **تحذير كلمات المرور الافتراضية** — يُعرض عند seed وعند startup
4. **RBAC واجهة — قائمة التنقل** — صفحة المستخدمين مخفية لغير مدير المشروع
5. **RBAC واجهة — حماية المسارات** — `/users` محمي بدور project_director
6. **RBAC واجهة — أزرار الشكاوى** — بطاقة التحديث مخفية لغير المسؤولين
7. **RBAC واجهة — أزرار المهام** — بطاقة التحديث مخفية لغير المسؤولين
8. **RBAC واجهة — أزرار العقود** — PDF وحذف مخفيان لغير مدير العقود/المدير
9. **بناء الواجهة** — `npm run build` ناجح (604 KB)
10. **تجميع Python** — جميع الملفات تُجمع بنجاح
11. **RBAC خادم** — لا تغيير — لا يزال يُطبق correctly

### ❌ غير مُنفذ (المرحلة الثانية):
- تصدير CSV
- إشعارات push/email
- اختبارات وحدة/تكامل
- تكامل GIS/خرائط
- PWA/offline mode
- code splitting

### ⚠️ ملاحظات مهمة:
- كلمات المرور التجريبية يجب تغييرها في الإنتاج — الخادم يحذر عند البدء
- CORS يُقرأ من `CORS_ORIGINS` env var — يجب تحديثه عند النشر
- `field_team` و `contractor_user` لا يمكنهم تحديث الشكاوى أو المهام (سلوك مقصود) — وأزرار التحديث مخفية لهم الآن

---

## الدفعات السابقة

### الدفعة: 2026-04-16 — إصلاحات أمنية وتشغيلية حرجة
**الملفات المعدلة:** `auth.py`, `complaints.py`, `tasks.py`, `contracts.py`, `uploads.py`, schemas, `tailwind.config.js`, `api.ts`, `ComplaintSubmitPage.tsx`, `ComplaintDetailsPage.tsx`

### الدفعة: 2026-04-15 — إنشاء صفحات وتقارير
**ملفات جديدة:**
| الملف | الوصف |
|---|---|
| `src/pages/UsersPage.tsx` | صفحة إدارة المستخدمين كاملة |
| `src/pages/ReportsPage.tsx` | صفحة التقارير |
| `src/pages/SettingsPage.tsx` | صفحة الإعدادات |
| `src/components/FileUpload.tsx` | مكون رفع ملفات |
| `backend/app/api/reports.py` | نقاط API للتقارير |
| `backend/app/schemas/report.py` | مخططات Pydantic للتقارير |

---

## الدفعة القادمة المُقترحة
1. تصدير CSV من التقارير
2. اختبارات وحدة أساسية للـ API
3. تحسين حجم الحزمة (code splitting, lazy loading)
4. إشعارات داخلية (in-app notifications)
5. لوحة تحكم المواطن (citizen dashboard)
