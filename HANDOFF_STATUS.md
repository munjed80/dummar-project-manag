# حالة التسليم
# HANDOFF_STATUS.md

## آخر تحديث: 2026-04-16

---

## الدفعة الحالية: 2026-04-16 — إصلاحات أمنية وتشغيلية حرجة

### الملفات المُعدّلة في هذه الدفعة:
| الملف | التغيير |
|---|---|
| `backend/app/api/auth.py` | إزالة `/auth/register` — التسجيل العام مغلق تماماً |
| `backend/app/api/complaints.py` | RBAC (مدير/مسؤول شكاوى/مشرف) + تسلسل images كـ JSON |
| `backend/app/api/tasks.py` | RBAC (مدير/مشرف هندسي/مشرف منطقة) + تسلسل before_photos/after_photos |
| `backend/app/api/contracts.py` | تسلسل attachments كـ JSON عند التحديث |
| `backend/app/api/uploads.py` | إضافة `/uploads/public` لرفع ملفات الشكاوى بدون مصادقة |
| `backend/app/schemas/complaint.py` | `images` → `List[str]` + field_validator للتحليل من DB |
| `backend/app/schemas/task.py` | `before_photos`/`after_photos` → `List[str]` + field_validator |
| `backend/app/schemas/contract.py` | `attachments` → `List[str]` + field_validator |
| `tailwind.config.js` | إزالة screens: coarse, fine, pwa (كانت تكسر البناء) |
| `src/services/api.ts` | إضافة `uploadFilePublic()` للرفع بدون مصادقة |
| `src/pages/ComplaintSubmitPage.tsx` | استخدام `uploadFilePublic` + إرسال images كمصفوفة |
| `src/pages/ComplaintDetailsPage.tsx` | تحديث إرسال images كمصفوفة |
| `PROJECT_REVIEW_AND_PROGRESS.md` | تحديث صادق بالحالة الحقيقية |
| `HANDOFF_STATUS.md` | تحديث صادق (هذا الملف) |

---

## الحالة الحقيقية المُتحقق منها

### ✅ مكتمل ومُتحقق منه:
1. **بناء الواجهة الأمامية** — `npm run build` ناجح (601 KB bundle)
2. **تجميع الخادم** — جميع ملفات Python تُجمع بنجاح
3. **أمان التسجيل** — `/auth/register` محذوفة، المستخدمون يُنشأون فقط بواسطة مدير المشروع عبر `/users/`
4. **رفع الشكاوى العامة** — `/uploads/public` متاح بدون مصادقة، يقبل صور و PDF فقط
5. **استمرار مرفقات الشكوى** — `ComplaintUpdate` يقبل `images: List[str]`
6. **استمرار صور المهام** — `TaskUpdate` يقبل `before_photos`/`after_photos: List[str]`
7. **استمرار مرفقات العقود** — `ContractUpdate` يقبل `attachments: List[str]`
8. **RBAC — تحديث الشكاوى** — مقيد بالأدوار: project_director, complaints_officer, engineer_supervisor, area_supervisor
9. **RBAC — إنشاء/تحديث/حذف المهام** — مقيد بالأدوار: project_director, engineer_supervisor, area_supervisor, complaints_officer
10. **RBAC — العقود** — كان مُطبقاً (contracts_manager, project_director)
11. **RBAC — المستخدمين** — كان مُطبقاً (project_director فقط)
12. **شكل بيانات الملفات** — API تُرجع مصفوفات JSON، الواجهة تستقبل `string[]`

### ❌ غير مُنفذ (المرحلة الثانية):
- تصدير CSV
- إشعارات push/email
- اختبارات وحدة/تكامل
- RBAC على مستوى واجهة المستخدم (إخفاء أزرار/صفحات حسب الدور)
- rate limiting على API
- تكامل GIS/خرائط
- PWA/offline mode
- code splitting

### ⚠️ ملاحظات مهمة:
- كلمات المرور التجريبية يجب تغييرها في الإنتاج
- CORS مقيد لـ localhost فقط
- لا يوجد rate limiting على `/uploads/public` — ينبغي إضافته قبل الإنتاج
- RBAC مُطبق على مستوى API فقط — الواجهة لا تخفي أزرار حسب الدور بعد
- `field_team` و `contractor_user` لا يمكنهم تحديث الشكاوى أو المهام (سلوك مقصود)

---

## الدفعات السابقة

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
1. RBAC على مستوى واجهة المستخدم (إخفاء أقسام حسب الدور)
2. Rate limiting على `/uploads/public`
3. تصدير CSV من التقارير
4. اختبارات وحدة أساسية للـ API
5. تحسين حجم الحزمة (code splitting)
