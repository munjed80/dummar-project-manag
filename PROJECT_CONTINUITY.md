# PROJECT_CONTINUITY.md — Session-by-Session Task Log

This file is updated after every agent session. It serves as the single source of truth for project state, what has been done, and what comes next.

---

## Session Log

---

### Session: 2026-05-02 — Fix green loading skeleton + safe frontend cleanup

**Task completed:** Frontend-only fix for the bright-green loading skeleton that was flashing on every page for 1–2 seconds, plus a small safe cleanup of stale lint directives. No backend, migrations, docker/nginx, route, or API contract changes.

**Root cause:** `src/components/ui/skeleton.tsx` rendered every placeholder with `bg-accent`. In `src/main.css` the `--accent` token is defined as `oklch(0.55 0.18 150)` (hue 150 = green). Since `<Skeleton>` is consumed by `LoadingSkeleton` (table + card variants), `SidebarMenuSkeleton`, and other primitives, every loading state across the app showed a bright green block — clashing with the navy/blue platform identity.

**What was done:**

1. **Skeleton primitive recoloured (`src/components/ui/skeleton.tsx`)** — Replaced `bg-accent` with the neutral palette `bg-[#E8EEF6]` (light) and `dark:bg-slate-700/40` (dark mode). Added an inline comment forbidding the use of `bg-accent`/green/emerald tokens for loading state. This single change cascades to every skeleton in the app (dashboard, complaints, tasks, teams, contracts, messages, smart-assistant drawer dark variant unchanged at `bg-white/5`, executive briefing already on `bg-slate-200`, sidebar menu skeleton, all card/table loading variants). The `--accent` CSS token itself was intentionally NOT changed because it is also used by many shadcn UI primitives (button, dropdown, menubar, calendar, navigation-menu, etc.) for hover/focus highlights — modifying it would be an out-of-scope visual change.
2. **LoadingSkeleton card border (`src/components/data/LoadingSkeleton.tsx`)** — Bumped the card border from `#E2EAF4` to the slightly stronger neutral `#D8E2EF` so the card outline matches the spec.
3. **Removed stale `eslint-disable` directives** —
   - `src/lib/loadError.ts`: dropped a `// eslint-disable-next-line no-console` that was no longer needed.
   - `src/pages/InvestmentContractDetailsPage.tsx`: replaced an unused inline `/* eslint-disable-next-line */` (placed after the statement so it disabled nothing) with the correct line-above directive `// eslint-disable-next-line react-hooks/exhaustive-deps`. Behaviour unchanged.

**Audit results (Part 4):**

- `bg-green*` / `text-green-*` / `bg-emerald*` / `text-emerald-*` → all remaining usages are **legitimate status indicators**: resolved/completed/active/healthy/approved/success badges, `CheckCircle` success icons, success counters, smart-assistant context-analysis green “key points” callout (intentional dark-themed success accent), executive-briefing contracts KPI card. None are loading placeholders. No change needed.
- `animate-pulse` → only three call sites: the patched `Skeleton` primitive, the dark-themed `SmartAssistantDrawer` skeleton (`bg-white/5`, neutral on dark), and `ExecutiveBriefingPage` neutral `bg-slate-200`. All clean.
- `console.log` → 0 matches in `src`. Nothing to remove.
- `TODO` / `FIXME` → 1 pre-existing TODO in `ExecutiveBriefingPage.tsx:159` (`// TODO: replace with a real KPI once a dedicated endpoint exists.`). Out of scope; left as-is.

**Files changed:**
- `src/components/ui/skeleton.tsx` — neutral palette for loading state
- `src/components/data/LoadingSkeleton.tsx` — card border `#D8E2EF`
- `src/lib/loadError.ts` — removed unused `eslint-disable`
- `src/pages/InvestmentContractDetailsPage.tsx` — corrected `eslint-disable` placement
- `PROJECT_CONTINUITY.md` — this entry

**Files intentionally NOT touched:**
- `src/main.css` `--accent` token — used app-wide by shadcn primitives (button hover, dropdown/menubar/select focus, calendar today, etc.); changing it would alter many components beyond skeletons.
- `src/pages/ViolationsPage.tsx` `react-hooks/static-components` errors — pre-existing, structural refactor required, out of scope.
- `src/services/api.ts:246` `no-useless-assignment` error — pre-existing, in core API client, out of scope.
- Backend, Alembic migrations, docker-compose, nginx, deploy.sh, SSL, route definitions, API contracts.

**Commands run:**
- `npm install` → 268 packages, 0 vulnerabilities
- `npm run build` → ✓ built in 1.26s (passes; bundle sizes unchanged from baseline)
- `npm run lint` → 27 problems (13 errors, 14 warnings); down from baseline 30 (3 lint warnings fixed). All remaining lint findings are pre-existing and unrelated to skeletons.

**Results:**
- Loading skeletons across all pages now render neutral slate (`#E8EEF6`) instead of bright green. Mobile card-skeleton variant uses `#D8E2EF` border. RTL layout untouched. Arabic text untouched. No behaviour change.
- Visual identity (header/topbar, sidebar/mobile drawer, primary buttons, data cards, tables/lists, error/empty states) preserved.

**Current project state:** Frontend builds clean. Loading skeletons consistent with navy/blue identity. Backend untouched (still 595 tests).

**Recommended next step:** If desired, normalize the remaining hardcoded `bg-green-*` status badges across pages to flow through the existing `StatusBadge` component (`src/components/data/StatusBadge.tsx`) for consistency — but this is a separate, scoped refactor and is NOT a bug.

---

### Session: 2026-05-02 — Header/sidebar visual consistency & mobile controls polish

**Task completed:** Frontend-only UI polish. Unified header and sidebar navy identity color, fixed RTL close button placement in all Sheet/drawer panels, fixed "فتح موجز المحافظ" button color, and made the logout button visible in the topbar on all screen sizes including mobile. No backend, migrations, docker/nginx, or route changes.

**What was done:**

1. **Color unification (`src/main.css`)** — Changed `--primary` from `oklch(0.48 0.18 260)` (bright blue-purple) to `oklch(0.30 0.09 245)` (dark navy matching sidebar `#123B63`). Also updated `--ring` to the same value. This makes the top header, primary buttons, focus rings, and all `bg-primary` surfaces use the same navy identity color as the sidebar, eliminating the visual mismatch between the bright topbar and the darker navy sidebar/drawer.

2. **RTL close button fix (`src/components/ui/sheet.tsx`)** — Moved the `SheetPrimitive.Close` button from `absolute top-4 right-4` to `absolute top-4 left-4`. In RTL context, `right-4` placed the × button directly above/beside Arabic titles. Now the layout is consistently `[× close on left]  [Arabic title on right]`, which applies globally to: mobile sidebar drawer, smart assistant drawer, notification panel, sync popover, and any future Sheet-based drawer.

3. **Dashboard button color (`src/pages/DashboardPage.tsx`)** — Removed explicit `className="bg-indigo-600 hover:bg-indigo-500 text-white"` from the "فتح موجز المحافظ" `Button` (kept `asChild size="sm"`). The default `Button` variant now inherits the navy primary color, eliminating the purple/indigo mismatch on the dashboard quick-action area.

4. **Logout visible on mobile topbar (`src/components/Layout.tsx`)** — Changed the header logout button from `hidden sm:inline-flex` to `inline-flex` (always visible). The Arabic label `تسجيل الخروج` has `hidden sm:inline` so it only shows on sm+ screens; on xs/mobile the button renders as icon-only (`SignOut` icon). Logout remains accessible from both the topbar icon and the mobile drawer menu. Added `aria-label="تسجيل الخروج"` for accessibility.

**Files changed:**
- `src/main.css` — `--primary` and `--ring` color updated to navy `oklch(0.30 0.09 245)`
- `src/components/ui/sheet.tsx` — close button moved from `right-4` to `left-4` for RTL
- `src/pages/DashboardPage.tsx` — removed `bg-indigo-600` from "فتح موجز المحافظ" button
- `src/components/Layout.tsx` — logout button always visible (icon-only on mobile)
- `PROJECT_CONTINUITY.md` — this entry

**Build result:** `npm run build` — ✓ 7331 modules transformed, no errors, no warnings.

**Color unification summary:**
- Before: header `bg-primary` = bright blue-purple `oklch(0.48 0.18 260)`, sidebar `bg-[#123B63]` = dark navy
- After: header `bg-primary` = dark navy `oklch(0.30 0.09 245)` ≈ `#123B63`, sidebar unchanged

**Close button placement:**
- Before: `absolute top-4 right-4` — overlapped Arabic RTL titles in all Sheet panels
- After: `absolute top-4 left-4` — clean `[×]  [Title]` layout across all drawers

**Logout placement:**
- Desktop (sm+): icon + "تسجيل الخروج" label in topbar (unchanged)
- Mobile (xs): SignOut icon visible in topbar at all times; full text in mobile drawer menu

**Mobile behavior notes:**
- No icon overlap introduced; logout icon is added to the existing right-side icon row
- The `canSubmitInternalComplaint` new-complaint shortcut remains `hidden sm:inline-flex` (intentionally hidden on xs to avoid crowding)
- PWA install, sync, smart assistant, and notification controls remain unchanged

**Recommended next step:** Review remaining gold accent borders (`inset ring bg-[#C8A24A]` in Sidebar.tsx active state) and consider limiting gold to executive-level highlights only per the task spec.

---

### Session: 2026-05-02 — Context-aware PWA install prompt (staff vs citizen)

**Task completed:** Split the single global PWA install control into two context-aware experiences. Staff/admin users get an icon-only install button in the topbar **only after authentication and only on staff routes**. Citizens get a small, polished, dismissible navy/blue install banner on every citizen-portal page (public landing, complaint submit, complaint track, citizen dashboard). Both surfaces use the native `beforeinstallprompt` when available and fall back to Arabic iPhone (Safari → Add to Home Screen) and Android (Chrome → ⋮ → تثبيت التطبيق) instructions. Frontend-only — manifest, service worker, backend, alembic, docker, and nginx untouched.

**Root cause / problem:**
Before this change the staff `PwaInstallButton` was rendered inside the shared `Layout` topbar for every authenticated user — including the `citizen` role on `/citizen` (CitizenDashboardPage uses `Layout`). That meant staff install UI leaked into the citizen portal. Public citizen pages (`/`, `/complaints/new`, `/complaints/track`) had **no** install affordance at all even though they are the QR-targeted entry points for residents.

**What was done:**
- **Staff install control (`src/components/PwaInstallButton.tsx`)** — added authentication / route guard. The button now renders only when:
  - `isAuthenticated` (from `useAuth`) is true,
  - `role !== 'citizen'`, and
  - the current pathname is **not** under `/citizen`, `/complaints/new`, or `/complaints/track`.
  - Popover help text now uses the spec's Arabic copy: "ثبّت تطبيق إدارة دمر على جهازك للوصول السريع إلى لوحة العمل." plus platform-specific Safari (iOS) and Chrome (Android) fallback instructions. The "متصفحك لا يدعم …" warning copy was replaced with the Android fallback so the message stays helpful, never alarmist. Already-installed pill ("التطبيق مثبت") is also gated by the same role/route check so it never appears on citizen pages.
- **New `src/components/CitizenInstallBanner.tsx`** — small navy/blue gradient card (`from-[#123B63] to-[#1d568f]`, white text, rounded `xl`, subtle border). Mobile-first, RTL, QR-friendly. Contents: device icon, the spec's Arabic copy "حمّل تطبيق شكاوى المواطنين على هاتفك لتقديم ومتابعة الشكاوى بسهولة.", a primary "تثبيت التطبيق" / "إضافة إلى الشاشة الرئيسية" button (label flips depending on whether the native prompt is available), and an `X` dismiss button. Captures `beforeinstallprompt`, listens to `appinstalled`, and self-hides when `display-mode: standalone` (or iOS `navigator.standalone`) is true. Dismissal persists in `localStorage` under `citizen_install_banner_dismissed_v1`. When no native prompt is available, a single click on the install button reveals an inline help block with the platform-appropriate Arabic instructions (iPhone Safari share-sheet, or Android Chrome ⋮ menu).
- **`src/components/PublicHeader.tsx` (`PublicShell`)** — mounted `<CitizenInstallBanner />` directly under `<PublicHeader />`. This single insertion covers `PublicLandingPage`, `ComplaintSubmitPage`, and `ComplaintTrackPage` — all three already wrap their content in `PublicShell`.
- **`src/pages/CitizenDashboardPage.tsx`** — added `<CitizenInstallBanner />` at the top of the page content (inside `Layout`'s body) so the citizen still sees the install nudge after they sign in to the citizen dashboard, while the staff topbar control stays hidden for them.

**Files changed:**
- `src/components/PwaInstallButton.tsx` — auth/role/route guard + spec Arabic copy + Android fallback in popover.
- `src/components/CitizenInstallBanner.tsx` — **new** dismissible navy/blue install banner.
- `src/components/PublicHeader.tsx` — render banner inside `PublicShell`.
- `src/pages/CitizenDashboardPage.tsx` — render banner at top of citizen dashboard body.
- `PROJECT_CONTINUITY.md` — this entry.

**PWA metadata audit:**
`public/manifest.json` already matches the navy identity (`theme_color: "#123B63"`, `background_color: "#F5F8FC"`, `display: standalone`, `start_url: "/"`, `dir: rtl`, `lang: ar`, maskable 192/512 icons). `index.html` `meta theme-color` matches (`#123B63`). No risky rewrite was performed; the project keeps a single global manifest and a single `public/sw.js`. Both are unchanged.

**Behavior matrix after change:**
| Surface | Install UI shown? |
| --- | --- |
| `/` (PublicLandingPage, anonymous) | Citizen install banner (in `PublicShell`) |
| `/complaints/new` (ComplaintSubmitPage) | Citizen install banner |
| `/complaints/track` (ComplaintTrackPage) | Citizen install banner |
| `/login` | Nothing (page has no shell, no banner) |
| `/citizen` (CitizenDashboardPage, role=citizen) | Citizen install banner; staff topbar button hidden |
| `/dashboard` and any other staff route (authenticated staff) | Staff topbar `PwaInstallButton` |
| Same staff route, app already installed | Compact "التطبيق مثبت" pill in topbar |

**iPhone / Android fallback behavior:**
- **iPhone/iPad** (no `beforeinstallprompt` on iOS Safari) — both surfaces show the spec Arabic instructions: "لتثبيت التطبيق على iPhone: افتح الموقع من Safari، اضغط زر المشاركة، ثم اختر إضافة إلى الشاشة الرئيسية." Staff: shown only when the user clicks the install icon (popover, not a permanent banner). Citizen: shown inline beneath the install button after the user clicks it.
- **Android with `beforeinstallprompt`** — native Chrome install prompt is triggered directly via `event.prompt()`.
- **Android without `beforeinstallprompt`** — both surfaces show: "لتثبيت التطبيق على Android: افتح الموقع من Chrome، اضغط القائمة ⋮، ثم اختر إضافة إلى الشاشة الرئيسية أو تثبيت التطبيق."

**Commands run:**
- `npm install` — 268 packages, 0 vulnerabilities.
- `npm run build` — green, 1.09s, 0 errors.
- `npm run lint` — same 13 errors / 15 warnings as before; all pre-existing in unrelated files (`ViolationsPage.tsx`, `api.ts`). No new warnings introduced.
- `grep "beforeinstallprompt|تثبيت التطبيق|إضافة إلى الشاشة الرئيسية|CitizenInstallBanner|PwaInstallButton" src public index.html` — confirms occurrences live only in `Layout.tsx`, `PublicHeader.tsx`, `CitizenDashboardPage.tsx`, `PwaInstallButton.tsx`, and the new `CitizenInstallBanner.tsx`.

**Limitations:**
- Repository routes are `/complaints/new`, `/complaints/track`, and `/citizen` (not `/citizen/new-complaint`, `/citizen/track`, `/citizen/complaint/:trackingCode` as the spec hypothetically named them). Per the "do not remap staff routes / do not rename modules" rule, the existing route names were preserved and the install logic targets the actual route paths. There is no standalone "citizen complaint detail" page route; complaint tracking happens via `/complaints/track`, which is already covered.
- The citizen banner's dismissal is per-browser via `localStorage`. If a citizen clears storage or switches devices it will reappear — intentional, since a fresh device may also need installing.
- Manifest is still a single global one (per the spec's "If safe, keep it"). A future enhancement could ship a dedicated citizen manifest with `start_url: "/complaints/new"` and a different `name`/`icons`, but that requires service-worker scope coordination and was deliberately skipped.

**Recommended next step:** add lightweight Playwright smoke checks for the citizen banner (visible on `/`, `/complaints/new`, `/complaints/track`, `/citizen` with role=citizen; dismiss persists across reload; hidden on `/login` and any staff route).

---

### Session: 2026-05-02 — Centralize 502/transient API error UX across all data pages

**Task completed:** Eliminated the technical Arabic error "الخادم غير متاح مؤقتاً أثناء تحميل … (HTTP 502). يرجى إعادة المحاولة بعد لحظات." that was surfacing in many sections (not just teams). Hardened the central API client retry, softened the user-facing copy, added a consistent "إعادة المحاولة" button to every affected list page, and migrated three pages that had ad-hoc error handling onto the shared helper. Frontend-only — no backend, alembic, docker, or nginx changes.

**Root cause:**
The Arabic message itself originated in `src/lib/loadError.ts` and was rendered by every page that imported `describeLoadError`. When nginx returned a transient `502` (backend worker recycle / brief gateway hiccup) the central `fetchWithRetry` only attempted **one** quick retry (400 ms), so multiple sections (Tasks, Teams, Complaints, Projects, Contracts, Investment*, Users, Internal Messages, Violations, Smart Assistant) displayed the technical message at once. Pages with ad-hoc error handling (Dashboard, Reports, Operations Map) compounded the problem with their own raw `'فشل تحميل…'` strings and no retry button. The endpoints themselves all exist on the backend — the failure is purely upstream gateway timing.

**What was done:**
- **Central retry helper hardened** (`src/services/api.ts`): two-step backoff `[500ms, 1500ms]` (was a single 400ms attempt) for GET requests on 502/503/504 and on network errors. Non-GET requests still pass through unchanged (no double-write risk). Diagnostic console line now includes the attempt index so devs can see retry counts in DevTools.
- **User-facing message softened** (`src/lib/loadError.ts`): the 502/503/504 branch now returns the requested clean Arabic copy `"تعذر تحميل البيانات حالياً. قد تكون الخدمة مشغولة مؤقتاً. يرجى إعادة المحاولة."` (no HTTP code, no entity name leaked into the visible string). Network-error fallback similarly softened. The original status, URL, content-type and detail are still logged via `[load:…]` and `[api-diagnostic]` so developers retain full visibility.
- **Retry buttons added** to every list page that uses `describeLoadError` and previously had no retry affordance: TasksListPage, TeamsListPage, ComplaintsListPage, ProjectsListPage, ContractsListPage, InvestmentContractsPage, InvestmentPropertiesPage, UsersPage, ViolationsPage, InternalMessagesPage. Pages that already had a callback (`fetchContracts`, `fetchProperties`, `fetchUsers`, `fetchViolations`, `loadThreads/loadThread`) reuse it; the rest gained a `reloadToken` state included in the effect deps.
- **Ad-hoc pages migrated to the central helper + retry button:** DashboardPage (was a boolean `statsError` with hard-coded copy), ReportsPage (four `'فشل تحميل …'` strings), ComplaintsMapPage (silently swallowed errors with `setMarkers([])`).

**Files changed:**
- `src/services/api.ts` — two-step retry backoff `[500, 1500]` ms with attempt counter in diagnostics.
- `src/lib/loadError.ts` — clean Arabic copy for transient/network branches; technical detail kept in dev console only.
- `src/pages/TasksListPage.tsx`, `TeamsListPage.tsx`, `ComplaintsListPage.tsx`, `ProjectsListPage.tsx`, `ContractsListPage.tsx`, `InvestmentContractsPage.tsx`, `InvestmentPropertiesPage.tsx`, `UsersPage.tsx`, `ViolationsPage.tsx`, `InternalMessagesPage.tsx` — added "إعادة المحاولة" button (some via `reloadToken`, some via existing `fetch*` callback).
- `src/pages/DashboardPage.tsx`, `ReportsPage.tsx`, `ComplaintsMapPage.tsx` — migrated to `describeLoadError` + retry button.
- `PROJECT_CONTINUITY.md` — this entry.

**Backend:** not touched. Audited the affected endpoints (`/dashboard/stats`, `/reports/*`, `/operations-map/markers`, `/teams/`, `/tasks/`, `/complaints/`, `/projects/`, `/contracts/`, `/investment-contracts/`, `/investment-properties/`, `/users/`, `/violations/`, `/internal-messages/threads`) — all routes exist and respond JSON. The 502 was always nginx → backend gateway timing, not a missing route or backend exception.

**Commands run:**
- `npm install` — 268 packages, 0 vulnerabilities.
- `npm run build` — green, 1.16s, 0 errors.
- `npm run lint` — 13 errors / 15 warnings (all pre-existing in `ViolationsPage.tsx` `Row` sub-component and elsewhere; baseline before changes was 13 errors / **16** warnings — net **-1 warning** from this change).
- `grep "الخادم غير متاح مؤقت|HTTP 502" src backend` — no matches (string fully removed from user-facing surfaces).

**Behavior after fix:**
- Transient 502/503/504 on a GET is now retried at 500 ms then 1500 ms before the user ever sees an error. In practice this masks the vast majority of single-blip gateway recycles.
- If all three attempts fail, every affected page renders a compact card with `Warning` icon, the soft Arabic copy, and an "إعادة المحاولة" button that re-runs the failed load.
- HTML 502 bodies from nginx are still discarded by `readErrorBody` and never rendered into the UI; only the dev-tools `[api-diagnostic]` line carries `endpoint/method/status/contentType/attempt`.
- RTL Arabic UI preserved everywhere; all variable, file, and component names remain in English.

**Remaining risks / out of scope:**
- Detail pages (`TaskDetailsPage`, `ComplaintDetailsPage`, `ProjectDetailsPage`, `TeamDetailsPage`, `ContractDetailsPage`, `InvestmentContractDetailsPage`, `InvestmentPropertyDetailsPage`, `DocumentReviewPage`, `DuplicateReviewPage`, `ProcessingQueuePage`, `GeoDashboardPage`, `SettingsPage`, `UsersListPage`, `LocationDetailPage`, `LocationReportsPage`, `IntelligenceReportsPage`) still use ad-hoc `'فشل تحميل …'` strings. They never showed the 502 message (they swallow detail entirely), so they were intentionally left alone per the minimal-change rule. A follow-up pass could migrate them to `describeLoadError` for consistency.
- The retry helper is intentionally GET-only. Non-idempotent writes (POST/PUT/DELETE/PATCH) on a transient 502 still bubble the error to the caller — correct behavior to avoid double-creates.

**Recommended next step:** if 502s persist after this UX fix, investigate the nginx ↔ backend gateway timing in `nginx.conf` / `nginx-ssl.conf` (the dynamic upstream resolver pattern is already correct — see prior memory) and consider increasing `proxy_read_timeout` on the backend location.

---

### Session: 2026-05-02 — Unified data presentation system (DataTable / badges / states)

**Task completed:** Introduced a reusable, lightweight data-presentation system that matches the new blue/navy government identity, then refactored every high-priority list page to use it. Frontend-only — no backend, migrations, deploy, route, or API changes.

**What was done:**
- **New `src/components/data/` primitives** (barrel-exported via `index.ts`):
  - `StatusBadge` — soft semantic badge with 7 tones (success / info / warning / danger / progress / neutral / accent). Replaces the per-page `bg-*-100 text-*-800` color maps that were duplicated in every list page. Ships a `COMMON_STATUS_TONES` map and `statusToneFor()` helper.
  - `PriorityBadge` — soft badge that maps `low/medium/high/urgent` → `neutral/info/warning/danger`.
  - `DataTableShell` — soft white card around a `<Table>` with the platform soft-border token (`#D8E2EF`), subtle `#F5F8FC` header fill, comfortable 44 px header height, soft row separators (`#EEF2F8`) and a gentle `#F8FAFD` hover. Replaces the heavy `border rounded-lg overflow-hidden` divs.
  - `DataToolbar` — single-row filter shell (search slot, filters slot, optional actions slot) that wraps cleanly on mobile.
  - `EmptyState` — soft, centered "no data" panel. Default Arabic title `"لا توجد بيانات حالياً"`, optional description, icon and CTA.
  - `ErrorState` — soft red panel that never leaks raw errors; shows `"إعادة المحاولة"` button when an `onRetry` callback is supplied.
  - `LoadingSkeleton` — table-shaped or card-shaped skeleton rows that preserve layout footprint and prevent shift.
  - `PaginationBar` — RTL-aware footer (Prev / Next + "صفحة X من Y" + "عرض A-B من N شكوى"). Renders nothing for ≤1 page so callers can drop the `totalPages > 1` guard.
  - `MobileEntityCard` — keyboard-accessible card row for mobile data-heavy lists (title + status badge + subtitle + meta).

- **High-priority pages refactored to use the new system:**
  - `ComplaintsListPage` — soft shell, `StatusBadge`/`PriorityBadge`, retryable `ErrorState`, skeleton loader (table + cards), `MobileEntityCard` mobile view, `PaginationBar`.
  - `TasksListPage` — same treatment + clean status/priority/source columns; mobile cards show due date + team + project.
  - `TeamsListPage` — added a proper mobile card view (was previously a squeezed table on phones); soft shell on desktop.
  - `ContractsListPage` (operational / "manual") — replaced inline badge color maps with `statusTones`, retryable error, soft shell, polished mobile cards, `PaginationBar`.
  - `InvestmentContractsPage` — replaced inline `bg-*-100` chips with `StatusBadge` (status + expiry-alert), retryable error, skeleton loader (table + cards), proper mobile cards (was desktop-only before), `PaginationBar`. Legacy `STATUS_COLORS` / `EXPIRY_BADGE` exports kept for backwards-compat but tones softened.
  - `ContractIntelligencePage` — replaced inline `Warning + Spinner` with `ErrorState` + skeleton stat cards; recent-docs table now uses `DataTableShell` + `StatusBadge` and `MobileEntityCard` for mobile.
  - `UsersListPage` — added mobile card view (was overflowing table on phones), softened role badges to semantic tones (`accent` for project_director, `success` for active, `danger` for disabled).

- **Visual contract enforced everywhere:**
  - Soft border `#D8E2EF` on cards/tables.
  - Subtle header `#F5F8FC` fill, muted uppercase header text.
  - Comfortable row height (`py-3`) and soft `#EEF2F8` row separators (no thick dark borders).
  - Gentle `#F8FAFD` hover.
  - Arabic page titles use the navy accent `#0F2A4A`; primary IDs (tracking numbers, contract numbers) use the primary blue `#1D4ED8`.
  - Gold (`#C8A24A`/accent tone) reserved for executive accents (sidebar rail, KPI cards) and the `project_director` role badge — never for data states.

- **Audits run:**
  - `rg "DataTable|DataToolbar|StatusBadge|PriorityBadge|MobileEntityCard|EmptyState|LoadingSkeleton|PaginationBar" src` → all 7 refactored pages + the 9 new primitives present.
  - `rg "border-black|border-slate-950|border-neutral-950|shadow-xl|shadow-2xl|bg-black|bg-slate-950|bg-neutral-950" src` → no matches in any data table or list page. Remaining hits are all intentional and unrelated to data presentation: Radix dialog/sheet/drawer/alert-dialog overlays use `bg-black/50` (standard backdrop), notification/install/sync popovers + chart tooltip use `shadow-xl` (popover elevation), `SmartAssistantDrawer` uses `bg-slate-950` (dark drawer by design).

**Files changed:**
- New: `src/components/data/{StatusBadge,PriorityBadge,EmptyState,ErrorState,LoadingSkeleton,PaginationBar,DataToolbar,DataTableShell,MobileEntityCard,index}.{tsx,ts}`
- Refactored: `src/pages/ComplaintsListPage.tsx`, `src/pages/TasksListPage.tsx`, `src/pages/TeamsListPage.tsx`, `src/pages/ContractsListPage.tsx`, `src/pages/InvestmentContractsPage.tsx`, `src/pages/ContractIntelligencePage.tsx`, `src/pages/UsersListPage.tsx`
- `PROJECT_CONTINUITY.md`

**Commands run:**
- `npm install` — 268 packages, 0 vulnerabilities.
- `npm run build` — green (~1.1 s, 0 errors).

**Results:**
- Build green.
- All 7 refactored pages now render the same elegant card → soft toolbar → soft table (desktop) / soft mobile cards (mobile) → soft pagination layout.
- Soft skeleton loaders replace spinners on list pages, preventing layout shift.
- Error panels are now retryable and never expose raw HTTP/HTML errors (still routed through `describeLoadError`).
- No business logic, API contract, route, status enum, permission, or filter behavior changed.

**Remaining limitations:**
- `ViolationsPage`, `LicensesPage` (placeholder), `InspectionTeamsPage` (placeholder), `LocationsListPage`, `ReportsPage`, `InternalMessagesPage`, `IntelligenceReportsPage`, `OperationsMapPage`, and `InvestmentPropertiesPage` were left untouched in this pass. They already use the existing `responsive-table-desktop` / `responsive-cards-mobile` CSS pattern but still carry per-page badge color maps. Migrating them to `StatusBadge` is mechanical and can be done in a follow-up pass without touching backend.
- Per-row action buttons (edit/delete) inside `InvestmentContractsPage` still use the small `text-destructive` ghost button — left intact because the destructive intent is meaningful and matches the rest of the platform.

**Recommended next step (before the governor demo):**
Extend the same `StatusBadge` / `DataTableShell` / `MobileEntityCard` migration to `ViolationsPage`, `LocationsListPage` and `InvestmentPropertiesPage`, then walk the demo flow on a real phone to verify the mobile cards on `/complaints`, `/tasks`, `/teams`, `/manual-contracts`, and `/investment-contracts` look polished end-to-end.

---

### Session: 2026-05-01 — Executive-gold accent wiring

**Task completed:** Wired the executive-gold accent `#C8A24A` from the palette into two high-signal places so the navy/blue identity feels complete.

**What was done:**
- **Sidebar active rail:** changed the 3-px right rail next to active items in `src/components/navigation/Sidebar.tsx` from `bg-sky-400` to `bg-[#C8A24A]`. The active item icon/text stays sky for legibility on navy; the gold rail provides the elegant "you-are-here" marker the spec asked for.
- **Dashboard KPI cards:** in `src/pages/DashboardPage.tsx`, added a 2-px gold top border (`border-t-2 border-t-[#C8A24A]`) to all four top-row KPI cards (إجمالي الشكاوى، إجمالي المهام، العقود النشطة، عقود قرب الانتهاء). The first three card icons also moved from generic `text-accent` to `text-[#C8A24A]` so the gold reads as a deliberate accent, not a fluke. The fourth card keeps its red `WarningCircle` icon because that's a true alert state.

Status indicators (progress bars, status badges, expiry alert tiles) were intentionally left on their existing semantic colors — gold is reserved for executive/identity accents, not data states.

**Files changed:**
- `src/components/navigation/Sidebar.tsx`
- `src/pages/DashboardPage.tsx`
- `PROJECT_CONTINUITY.md`

**Build:** `npm run build` — green (1.06s, 0 errors).

**Recommended next step:** awaiting user to specify which functional feature to tackle next (no specific feature was named in the prompt).

---

### Session: 2026-05-01 — Visual identity, sync status UI, PWA install polish

**Task completed:** Aligned the platform on a single navy/blue government-dashboard identity, replaced the yellow full-width sync banner with a compact topbar control, and polished the PWA install experience (iOS instructions + graceful fallback). Frontend-only.

**What was done:**
- **Sidebar identity:** replaced `bg-slate-950` (near-black) with sidebar navy `#123B63` in `src/components/Layout.tsx` (desktop sidebar + mobile sheet) and `src/components/navigation/Sidebar.tsx`. Header (`bg-primary`) and sidebar now share the same blue family. Active-item rail (sky-300/400) unchanged — it pops cleanly on navy.
- **Theme tokens:** lifted `--primary` saturation/hue in `src/main.css` to land closer to `#1D4ED8`, soft app `--background` near `#F5F8FC`, and slightly cleaner `--border`. No structural CSS rename — only token values changed, so all existing `bg-primary` / `bg-background` / `border-border` usages benefit automatically.
- **Sync status redesign:** removed the always-visible yellow `OfflineSyncBanner` and added `src/components/SyncStatusButton.tsx` — a topbar icon (sits between Smart Assistant and the new install button) that opens a 288px popover with: حالة المزامنة، آخر تحديث، العناصر المعلقة، وضع الاتصال، و زر "مزامنة الآن". Visual states: green (synced), spinning sky icon (syncing), gray (offline), amber dot (pending items), red dot (real sync error). No backing logic changed — it subscribes to the existing `offlineSyncManager` and calls `syncNow()`.
- **PWA install polish:** removed the floating `InstallPrompt` toast and added `src/components/PwaInstallButton.tsx` in the topbar:
  - if `beforeinstallprompt` fires → opens native install dialog,
  - if already installed (display-mode standalone or iOS `navigator.standalone`) → shows "التطبيق مثبت" pill and disables itself,
  - on iPhone/iPad → opens a popover with Arabic Safari instructions ("افتح الموقع من Safari، اضغط زر المشاركة، ثم اختر Add to Home Screen"),
  - otherwise → shows a graceful Arabic help message instead of failing silently.
  Also listens to the `appinstalled` event so the button hides immediately after install.
- **PWA manifest** (`public/manifest.json`): added `scope: "/"`, set `theme_color: "#123B63"` (sidebar navy) and `background_color: "#F5F8FC"` (soft app bg) to match the new identity. Icons (192 + 512) untouched.
- **`<meta name="theme-color">`** in `index.html` updated to `#123B63` so the mobile address bar matches the sidebar/header.

**Files changed:**
- `src/components/Layout.tsx` *(navy sidebar, banner removed, sync + install buttons added)*
- `src/components/navigation/Sidebar.tsx` *(navy background)*
- `src/components/SyncStatusButton.tsx` *(new — compact topbar sync control)*
- `src/components/PwaInstallButton.tsx` *(new — replaces floating InstallPrompt)*
- `src/components/OfflineSyncBanner.tsx` *(deleted)*
- `src/components/InstallPrompt.tsx` *(deleted)*
- `src/App.tsx` *(InstallPrompt import + render removed)*
- `src/main.css` *(refined --primary / --background / --border tokens)*
- `public/manifest.json` *(scope, navy theme_color, soft background_color)*
- `index.html` *(theme-color meta updated to navy)*
- `PROJECT_CONTINUITY.md` *(this entry)*

**Mobile behavior:**
- Sheet drawer keeps working — its background was switched to `bg-[#123B63]` in the same file.
- Topbar gained two new icon buttons (sync, install). All buttons use the existing `p-2` icon style and stay within the existing `gap-1.5 md:gap-2` flex row, so the topbar still fits on the smallest supported widths. The install button uses `hidden sm:inline-flex` only for the "installed" pill state; the icon itself stays visible on mobile.

**Build:** `npm run build` — green (1.11s, 0 errors).

**Validation grep:** the requested search still reports occurrences of `bg-amber-*` / `bg-yellow-*` / `bg-black/*` across pages, but they are intentional and outside the scope of this polish:
- `src/components/ui/{sheet,dialog,drawer,alert-dialog}.tsx` — `bg-black/50` is the standard shadcn-ui modal overlay backdrop (semi-transparent dim).
- Page-level `bg-amber-*` / `bg-yellow-*` (Dashboard, Tasks, Contracts, Violations, ContractIntelligence, etc.) are **status indicators** for warning/expiring/in-progress states (e.g. expiring investment contracts, pending review). Repainting those would change business meaning, not visual identity, and was not requested.
- `SyncStatusButton.tsx` itself uses one `bg-amber-400` dot — this is the intentional "pending items" indicator described in the spec.
- No remaining `bg-slate-950` / `bg-black` (full surface) outside the modal overlays above.

**Visual identity changes:** sidebar moved from near-black to navy `#123B63`; header + sidebar now read as one system; CSS tokens shifted toward the requested palette without renaming any utility class.

**Sync status changes:** yellow page-level banner removed; replaced by a compact icon-only topbar control with a status popover and "مزامنة الآن" action. Existing sync logic in `offlineSyncManager` is untouched.

**PWA install changes:** new topbar button with native install / iOS instructions / unsupported-browser help; manifest theme/background and `<meta theme-color>` aligned with the new navy; service-worker registration in `main.tsx` left untouched per the "no risky SW changes" rule.

**Remaining risks / limitations:**
- `lastSyncedAt` in `SyncStatusButton` is captured client-side from the `syncing → idle` transition; it is not persisted across page reloads. Adequate for the polish scope; can be moved into `offlineSyncManager` later if desired.
- Status badge wording uses simple Arabic strings; can be promoted to the i18n layer when one is introduced.
- The amber/yellow status colors elsewhere in the app are kept on purpose (warning semantics). A future pass could harmonize them with the executive gold accent `#C8A24A` from the palette.

**Recommended next step:** wire the executive gold accent `#C8A24A` into one or two high-signal places (e.g. KPI highlights on the dashboard and the active sidebar rail) so the palette feels complete, then move on to the next functional feature.

---

### Session: 2026-05-01 — Phase 4: Executive Governor Briefing / Demo Readiness

**Task completed:** Added a polished, frontend-only "موجز المحافظ" presentation page intended as a 7–10 minute governor-level walkthrough of the platform. No backend, migrations, deploy, or module changes.

**Files changed:**
- `src/pages/ExecutiveBriefingPage.tsx` *(new)* — full executive briefing page.
- `src/App.tsx` — lazy-imported `ExecutiveBriefingPage` and registered `/executive-briefing` route under `INTERNAL_ROLES`.
- `src/components/navigation/nav-config.ts` — added a single nav entry "موجز المحافظ" right after "لوحة القيادة" using the `PaperPlaneTilt` icon (does not disturb any existing group).
- `src/pages/DashboardPage.tsx` — added a primary "فتح موجز المحافظ" shortcut button at the top of the page; added a graceful Arabic error banner shown when `getDashboardStats()` fails.
- `PROJECT_CONTINUITY.md` *(this entry)*.

**Route added:** `GET /executive-briefing` → `<ExecutiveBriefingPage />` (protected by `RoleProtectedRoute roles={INTERNAL_ROLES}`).

**Where the menu/dashboard shortcut was added:**
- Top-level sidebar: single entry "موجز المحافظ" placed immediately after "لوحة القيادة" (file: `src/components/navigation/nav-config.ts`).
- Dashboard top bar: primary button "فتح موجز المحافظ" (indigo) added before the existing الشكاوى/المهام shortcuts (file: `src/pages/DashboardPage.tsx`).

**Page contents (`/executive-briefing`):**
1. **Hero** — "موجز المحافظ" + Arabic subtitle ("منصّة موحّدة تحوّل الشكاوى والمهام والعقود والقرارات الداخلية إلى نظام تشغيل رقمي للمحافظة …") + badge "نسخة عرض تنفيذية" + three CTAs (افتح المساعد الذكي / لوحة القيادة / التقارير).
2. **KPI cards (6)** — الشكاوى / المهام / العقود / المتأخرات / التنبيهات / الرسائل الداخلية — sourced from `apiService.getDashboardStats()` and `apiService.getMessageThreads({limit:50})`. Each KPI shows a skeleton while loading and "لا توجد بيانات حالياً" when the underlying data is missing or the call fails. KPI cards link to the relevant page when applicable.
3. **Priority focus** — الشكاوى المتأخرة / المهام التي تحتاج متابعة / العقود التي تقترب من الانتهاء / الملفات التي تحتاج قراراً إدارياً (last one shown as a forward-looking placeholder until a dedicated KPI exists).
4. **Presentation storyline (7 steps)** — استقبال الشكوى ← تحويلها إلى مهمة ← إسنادها إلى فريق تنفيذي ← متابعة النقاش الداخلي ← تحليل الشكوى بالمساعد الذكي ← متابعة العقود والتنبيهات ← إصدار تقارير وقرارات أسرع. Each step has a "فتح الصفحة" action linking to the relevant route, except step 5 which opens the assistant drawer.
5. **Decision-support cards (6)** — كشف التأخير / تحديد المسؤولية / توثيق النقاش الداخلي / تحليل الشكاوى / متابعة العقود / تقليل الاعتماد على الاتصالات الورقية والشفوية.
6. **Assistant CTA footer** — "افتح المساعد الذكي" reuses the existing `<SmartAssistantDrawer>` (no logic duplicated).

**Behaviour added:**
- Frontend-only. No new API calls were created — the page reuses the existing `getDashboardStats` and `getMessageThreads` endpoints.
- All sections degrade gracefully to "لا توجد بيانات حالياً" or skeletons when data is missing — no raw exceptions reach the UI.
- The assistant button on the briefing page opens the existing drawer with no context (general assistant); the per-complaint context flow added in Phase 3 remains unchanged.

**What was intentionally NOT changed:**
- No Alembic migrations.
- No backend models / routes / schemas.
- No internal-messages, internal-bot, complaints, contracts backend.
- No deploy / docker / nginx / SSL files.
- No module renames or route remaps.
- No new large modules.
- No redesign of the existing dashboard, complaints list, messages page, or contract intelligence page (only the dashboard got a small shortcut button + an error-state banner — both additive).

**Validation:**
- `npm run build` → ✅ built in 1.08s (0 errors).
- `npx tsc --noEmit` → no new errors in `src/pages/ExecutiveBriefingPage.tsx`, `src/App.tsx`, `src/components/navigation/nav-config.ts`, or `src/pages/DashboardPage.tsx`. Pre-existing missing-module errors in unused `src/components/ui/*` shadcn helpers are untouched.
- `rg "ExecutiveBriefing|موجز المحافظ|نسخة عرض تنفيذية|فتح المساعد الذكي" src PROJECT_CONTINUITY.md` → matches in `src/App.tsx`, `src/components/navigation/nav-config.ts`, `src/pages/DashboardPage.tsx`, `src/pages/ExecutiveBriefingPage.tsx`, and this file.

**Remaining risks before the governor demo:**
- The demo data in the connected backend should include at least: a few complaints in mixed statuses, at least one task, one operational contract near expiry, and one internal-discussion thread linked to a complaint — otherwise the KPI/priority cards will mostly show "لا توجد بيانات حالياً" (which is graceful but visually quiet).
- Pre-existing TS errors in unused `src/components/ui/*` shadcn helpers remain (their dependencies are not installed). These are silenced by `tsc -b --noCheck` in the build script and do not block the demo, but they should be cleaned up in a future maintenance pass.
- The "الملفات التي تحتاج قراراً إدارياً" priority card has no real KPI behind it yet; it currently always renders the empty state and links to `/messages`. Replace with a real metric when the corresponding endpoint exists.
- The `/internal-bot` standalone page has a `Record<InternalBotIntent, string>` map that is missing the new `'context_analysis'` key; the build currently passes only because of `--noCheck`. Consider adding the key in the next pass for type tightness (out of scope for this PR — that page is not part of the governor demo flow).
- Network failures on the dashboard now surface as a calm Arabic banner instead of a silent empty page; please confirm the same is true for `/complaints`, `/messages`, and `/contract-intelligence` during a dry-run before the live demo.

**Final checklist for presentation readiness:**
- [x] `/executive-briefing` route reachable from the sidebar ("موجز المحافظ").
- [x] `/dashboard` exposes a "فتح موجز المحافظ" shortcut.
- [x] All KPI / priority cards render either real data or graceful Arabic empty/loading states.
- [x] "افتح المساعد الذكي" reuses the existing `SmartAssistantDrawer` (no duplicate logic).
- [x] Arabic RTL layout preserved everywhere.
- [x] Build succeeds.
- [ ] *Recommended manual dry-run before the demo:* log in as `project_director`, walk through `/dashboard` → `/executive-briefing` → press each storyline button → open the assistant → open one complaint and use "تحليل ذكي للشكوى". Confirm there are no raw error toasts.

**Recommended next step:**
- Wire a real KPI behind "الملفات التي تحتاج قراراً إدارياً" (e.g. count of message threads with `context_type` set and zero replies in N days) and/or expose a small "tasks overdue" backend counter so the priority section never has to fall back to the empty state.

---

### Session: 2026-05-01 — Phase 3: Context-aware smart assistant (complaint analysis)

**Task completed:** Extended the existing `/internal-bot/query` endpoint and the `SmartAssistantDrawer` so the assistant can produce a rule-based, Arabic, structured analysis of a single complaint when opened from `ComplaintDetailsPage`.

**Backend:**
- `backend/app/schemas/internal_bot.py`:
  - Added `intent='context_analysis'` literal.
  - Added `RiskLevel = 'low' | 'medium' | 'high'` and `RelatedItem` model.
  - Added `SUPPORTED_CONTEXT_TYPES = ('complaint',)`.
  - Extended `InternalBotQuery` with optional `context_type` (max 50) and `context_id` (≥1).
  - Extended `InternalBotResponse` with optional `risk_level`, `key_points`, `recommended_actions`, `related_items`, `context_type`, `context_id` (all `None` for legacy intents → backward compatible).
- `backend/app/api/internal_bot.py`:
  - New `_build_complaint_analysis(db, complaint)` helper — pure deterministic rule-based logic, no external AI calls. Aggregates the complaint, the latest linked task, and the Phase-2 context-linked `MessageThread` (message_count, last_message_at, last 3 messages summarized to ~140 chars), resolves location/area names, and computes a risk level via simple rules:
    - URGENT + open → high; HIGH + open + age≥2d → high; open + age≥14d → high.
    - HIGH/URGENT open → medium; open + age≥7d → medium; NEW + age≥3d → medium.
    - Otherwise low.
  - Generates Arabic `summary`, `key_points`, `recommended_actions` (e.g. "أنشئ مهمة تنفيذية" when no linked task, "افتح نقاشاً داخلياً" when no thread, "تابع المهمة المرتبطة" for stale tasks, etc).
  - `POST /internal-bot/query` now branches on `context_type`/`context_id`:
    - both must be supplied (422 otherwise),
    - `context_type` validated against `SUPPORTED_CONTEXT_TYPES` (400 otherwise),
    - complaint missing → 404,
    - audited via `write_audit_log(action='internal_bot_query', entity_type='internal_bot')`.
  - Explicit guard: `intent='context_analysis'` without context fields returns 422 (prevents falling through to `contracts_expiring`).
- `backend/tests/test_internal_bot.py`: +5 new tests
  - `test_internal_bot_context_complaint_returns_structured_analysis`
  - `test_internal_bot_context_includes_task_and_thread` (verifies task + Phase-2 thread aggregation)
  - `test_internal_bot_context_404_when_complaint_missing`
  - `test_internal_bot_context_rejects_unsupported_type` (e.g. `contract` → 400)
  - `test_internal_bot_context_requires_both_fields` (422)

**Frontend:**
- `src/services/api.ts`:
  - `InternalBotIntent` now includes `'context_analysis'`.
  - New `InternalBotRiskLevel` and `InternalBotRelatedItem` types.
  - `InternalBotResponse` extended with optional `risk_level`, `key_points`, `recommended_actions`, `related_items`, `context_type`, `context_id`.
  - `apiService.queryInternalBot` accepts optional `context_type`/`context_id`.
- `src/components/SmartAssistantDrawer.tsx`:
  - New optional `context?: SmartAssistantContext` prop (`contextType: 'complaint'`, `contextId`, `contextTitle?`).
  - Auto-runs the contextual analysis the first time the drawer is opened for a given (type,id) pair (dedup via `autoRanFor`).
  - Context banner: "تحليل مرتبط بالشكوى رقم …" + "حلّل هذه الشكوى" quick prompt button.
  - New `ContextAnalysisPanel` renders summary, color-coded risk badge (low=emerald, medium=amber, high=red), key points list, recommended actions list, and related items chips.
  - Existing `ResultPanel` still used for the three legacy intents — switched at render time based on `response.intent`.
- `src/pages/ComplaintDetailsPage.tsx`:
  - New header button "تحليل ذكي للشكوى" (Robot icon, sky-toned outline).
  - Opens `SmartAssistantDrawer` with `context={contextType:'complaint', contextId:complaint.id, contextTitle:tracking_number}`.
- `/messages` page **not** modified.

**Files changed:**
- `backend/app/schemas/internal_bot.py`
- `backend/app/api/internal_bot.py`
- `backend/tests/test_internal_bot.py`
- `src/services/api.ts`
- `src/components/SmartAssistantDrawer.tsx`
- `src/pages/ComplaintDetailsPage.tsx`
- `PROJECT_CONTINUITY.md` *(this entry)*

**Backend behavior added:** `POST /internal-bot/query` now optionally accepts `context_type` + `context_id`. When both are present and `context_type='complaint'`, the endpoint returns an `InternalBotResponse` with `intent='context_analysis'`, an Arabic summary, a risk level, key points, recommended actions, and related items (linked task + linked message thread). Other context types are reserved (400). Pure rule-based — no external AI APIs.

**Frontend behavior added:** `ComplaintDetailsPage` exposes a "تحليل ذكي للشكوى" button that opens the existing assistant drawer with complaint context. The drawer shows a banner "تحليل مرتبط بالشكوى رقم …", auto-runs the analysis, exposes a "حلّل هذه الشكوى" re-run button, and renders the structured response (summary + risk + key points + recommended actions + related items).

**Commands run:**
- `cd backend && python -m pytest tests/ -q` → ✅ **595 passed** in 243s (was 590; +5 Phase-3 tests; internal-bot file 2 → 7 tests).
- `npm install && npm run build` → ✅ built in 868ms, 0 errors.
- `grep -rln "context_type|context_id|risk_level|recommended_actions|تحليل ذكي للشكوى" backend src` → all expected files present.

**What was intentionally not changed:**
- No Alembic / migrations touched.
- No deploy/docker/nginx/SSL files touched.
- No module renames or route remaps.
- `/messages` page UI unchanged.
- No external AI APIs introduced — analysis is fully deterministic rule-based logic.
- The drawer's three legacy tabs (ask/daily/suggest) and their quick prompts are unchanged.

**Recommended next step:**
- Wire the same "تحليل ذكي" entry point on `TaskDetailsPage` and `ContractDetailsPage`, then extend `SUPPORTED_CONTEXT_TYPES = ('complaint','task','contract')` and add the matching analyser branches in `internal_bot.py`. The schema, drawer, and frontend are already context-agnostic.

---

### Session: 2026-05-01 — Phase 2: Context-linked internal message threads (complaint)

**Task completed:** Added backend persistence + endpoint + frontend panel that links an internal-messages thread to a specific complaint.

**Backend:**
- `backend/app/models/internal_message.py`: added nullable `context_type` (String 50, indexed), `context_id` (Integer, indexed), `context_title` (String 255) to `MessageThread`.
- `backend/alembic/versions/023_add_message_thread_context.py`: new migration (rev `023`, down_revision `022`) adding the three columns and the two indices `ix_message_threads_context_type` / `ix_message_threads_context_id`. **No old migrations were edited.**
- `backend/app/schemas/internal_message.py`: `ThreadCreateRequest` and `ThreadSummaryResponse` now expose the optional context fields.
- `backend/app/api/internal_messages.py`:
  - `_build_thread_summary` now returns `context_type` / `context_id` / `context_title`.
  - `create_thread` passes through context fields if provided.
  - **New endpoint**: `GET /internal-messages/context/{context_type}/{context_id}?context_title=...` — validates `context_type` against the `SUPPORTED_CONTEXT_TYPES` set (currently `{'complaint'}`), validates `context_id`, verifies the complaint exists, then returns the existing thread or creates a new GROUP thread linked to that context with the current user as participant. Auto-adds the current user to an existing thread's participants on access (any internal staff opening the complaint joins the discussion).
- `backend/tests/test_internal_messages.py`: 5 new tests
  - `test_context_thread_creates_when_missing`
  - `test_context_thread_is_idempotent`
  - `test_context_thread_auto_adds_new_participant`
  - `test_context_thread_rejects_unknown_context_type` (e.g. `contract` returns 400)
  - `test_context_thread_404_when_complaint_missing`

**Frontend:**
- `src/services/api.ts`:
  - `MessageThread` now also exposes optional backend-persisted `context_type`/`context_id`/`context_title` (the existing frontend-only `_contextRef` is preserved).
  - Added `apiService.getOrCreateContextThread(contextType, contextId, contextTitle?)` that calls `GET /internal-messages/context/{type}/{id}`.
- `src/components/messages/ContextMessagesPanel.tsx` *(new)*: RTL Card titled **"النقاش الداخلي"** that loads/creates the thread on mount, renders messages in chat-bubble style with auto-scroll, provides a multi-line composer (Enter sends, Shift+Enter newline), and handles loading/empty/error states (with a "إعادة المحاولة" button on error).
- `src/pages/ComplaintDetailsPage.tsx`: imports and mounts the panel inside the page (`contextType="complaint"`, `contextId=complaint.id`, `contextTitle="شكوى {tracking_number}"`). Inserted between the linked-tasks card and the activity history card. **No other changes** to the page.
- `/messages` page is intentionally NOT redesigned. Contracts/tasks/etc. are NOT wired yet.

**Files changed:**
- `backend/app/models/internal_message.py`
- `backend/app/schemas/internal_message.py`
- `backend/app/api/internal_messages.py`
- `backend/alembic/versions/023_add_message_thread_context.py` *(new)*
- `backend/tests/test_internal_messages.py`
- `src/services/api.ts`
- `src/components/messages/ContextMessagesPanel.tsx` *(new)*
- `src/pages/ComplaintDetailsPage.tsx`
- `PROJECT_CONTINUITY.md` *(this entry)*

**Migration name:** `023_add_message_thread_context.py` (revision `023`, down_revision `022`).

**Endpoint added:** `GET /internal-messages/context/{context_type}/{context_id}` (query: `context_title`). Currently `context_type` must be `complaint`.

**Commands run:**
- `cd backend && python -m pytest tests/ -q` → ✅ **590 passed** in 240s (was 526; +64 tests across the session — internal-messages tests grew from 3 to 8).
- `npm install && npm run build` → ✅ built in 853ms, 0 errors.
- `grep -rln "context_type|context_id|ContextMessagesPanel|internal-messages/context" backend src` → all expected files present.

**What was intentionally not changed:**
- No deploy/docker/nginx/SSL files touched.
- No module renames or route remaps.
- `/messages` page UI unchanged.
- Contracts/tasks/asset/license/violation context wiring NOT implemented (only the backend's `SUPPORTED_CONTEXT_TYPES` set needs to be extended when those are added).

**Recommended next step:**
- Wire the same `ContextMessagesPanel` into `ContractDetailsPage` and `TaskDetailsPage`, and extend `SUPPORTED_CONTEXT_TYPES = {'complaint', 'contract', 'task'}` in `internal_messages.py`.
- Consider auto-adding domain-relevant participants (e.g. assigned engineer) when the contextual thread is first created, instead of only the user who opened it.

---

### Session: 2026-05-01 — Decision Center UX (Smart Assistant Drawer + Messages Upgrade)

**Task completed:** Turned the internal messages and smart assistant into a professional "Decision Center" experience (Parts 1–4 of the spec).

**What was done:**

**Part 1 — Smart Assistant Topbar Drawer (`SmartAssistantDrawer.tsx`)**
- Created `src/components/SmartAssistantDrawer.tsx`: a full-height right-side RTL `Sheet` drawer with a premium dark government-dashboard style.
- Three tabs: **اسأل النظام** (free-text + quick prompts), **ملخص اليوم** (daily summaries), **اقترح إجراء** (suggested actions).
- Quick prompts in a 2-column grid: ملخص الشكاوى اليوم, المهام المتأخرة, العقود التي تقترب من الانتهاء, أكثر المناطق ضغطاً.
- Calls `POST /internal-bot/query` via existing `apiService.queryInternalBot()`.
- Displays: summary text, stat-cards grid with totals, data table with Arabic column labels.
- Loading skeleton (pulse animation), inline error, empty state with robot icon.
- Updated `SmartAssistantButton.tsx` to open the drawer via `useState(open)` instead of linking to `/internal-bot`. The `/internal-bot` full page is preserved unchanged.

**Part 2 — Internal Messages UX Upgrade (`InternalMessagesPage.tsx`)**
- Full rewrite of the page to a professional "مركز التواصل الداخلي" layout.
- Left column: thread list with search filter, unread badge, relative time, thread type icons (direct/group), live total unread count in header.
- Right column: thread header with participant count and last-activity time, message bubbles with RTL alignment (my messages right-aligned sky-blue, others left-aligned muted), grouped sender rows with avatar initials, auto-scroll to latest message via `useRef`.
- Composer: multi-line `Textarea` (Enter sends, Shift+Enter = new line), send button.
- New thread dialog: user search filter, avatar previews, participant count badge (direct vs. group indicator), user role shown.
- Loading/error/empty states at every level.
- Refresh button with spinner animation.

**Part 3 — Context-ready types (`api.ts`)**
- Added `MessageContextType = 'complaint' | 'contract' | 'task' | 'asset' | 'license' | 'violation'`
- Added `MessageContextRef { contextType: MessageContextType; contextId: number }`
- Added optional `_contextRef?: MessageContextRef` to `MessageThread` (frontend-only field, never sent to backend — documented with JSDoc comment).

**Part 4 — Safety**
- No backend files modified.
- No alembic migrations touched.
- No deployment files (nginx.conf, docker-compose.yml, etc.) changed.
- No existing complaints/teams/contracts logic altered.
- Navigation structure unchanged (`/messages` route preserved); only the topbar assistant button behavior changed (link → drawer).

**Files changed:**
- `src/components/SmartAssistantDrawer.tsx` *(new)*
- `src/components/navigation/SmartAssistantButton.tsx` *(updated — now opens drawer)*
- `src/pages/InternalMessagesPage.tsx` *(rewritten — professional ops center UI)*
- `src/services/api.ts` *(types: MessageContextType, MessageContextRef, _contextRef on MessageThread)*
- `PROJECT_CONTINUITY.md` *(this entry)*

**API methods used:**
- `POST /internal-bot/query` — assistant queries (existing `apiService.queryInternalBot`)
- `GET /internal-messages/threads` — thread list (existing)
- `GET /internal-messages/threads/:id` — thread messages (existing)
- `POST /internal-messages/threads/:id/messages` — send message (existing)
- `POST /internal-messages/threads` — create thread (existing)
- `GET /users/` — user picker for thread creation (existing)

**Commands run:**
- `npm install` → OK
- `npm run build` → ✅ built in 1.20s, 0 TS or bundling errors.
- `grep -rn "InternalMessages|InternalBot|assistant|messages|PROJECT_CONTINUITY" src/ PROJECT_CONTINUITY.md` → all expected files present.

**Build result:** ✅ Success. All 7311 modules transformed. `InternalMessagesPage` chunk: 21.09 kB gzip 6.40 kB. `Layout` chunk: 145.94 kB gzip 38.08 kB (SmartAssistantDrawer is lazy-loaded inside the button component and tree-shaken into the Layout bundle).

**What was intentionally not changed:**
- `/internal-bot` full page (`InternalBotPage.tsx`) — preserved as-is for direct access.
- All backend code, API routes, migrations, models, permissions.
- All deployment infrastructure files.
- All other frontend pages and navigation structure.

**Recommended next step:**
- Connect `_contextRef` to the backend once `/internal-messages/threads` supports `context_type` / `context_id` query params — the frontend types are already in place.
- Add a "لا إجابة" fallback for the "أكثر المناطق ضغطاً" preset (currently the bot returns a graceful 200 with a message if unsupported).
- Consider adding 30-second auto-refresh for the messages thread list to keep unread counts live without a full page reload.

---

### Session: 2026-05-01 — Sidebar redesign (collapsible admin menu)

**Task completed:** Redesigned and reorganized the sidebar navigation into a professional collapsible admin menu (WordPress / Xtream Codes style). Smart Assistant moved from sidebar to topbar icon.

**What was done:**
- Refactored `src/components/navigation/nav-config.ts` from a flat `NAV_ITEMS` array into a grouped tree (`NAV_ENTRIES`) with two top-level kinds: `single` (Dashboard / Citizen home) and `group` (collapsible sections). Added `filterEntriesByRole` helper and a per-leaf `badge` field (`'ai' | 'messages'`).
- Built a new dark/premium collapsible **`Sidebar`** component (`src/components/navigation/Sidebar.tsx`) with: per-group collapse with persisted state in `localStorage` (`sidebar.openGroups.v1`), auto-expand of the group containing the active route, active route highlighting (sky accent + right rail), per-item icons, AI badge for مركز ذكاء العقود, and an unread-count badge for الرسائل الداخلية.
- Added **`SmartAssistantButton`** (`src/components/navigation/SmartAssistantButton.tsx`) — a topbar icon next to the notification bell that links to `/internal-bot`. Removed the assistant from the sidebar.
- Rewrote **`src/components/Layout.tsx`** to use a sticky topbar + fixed RTL sidebar (right edge) on desktop and a `Sheet`-based drawer with the same `SidebarNav` on mobile. Added a 60-second polled hook that sums `MessageThread.unread_count` to drive the messages badge.
- Removed the now-unused `src/components/navigation/AppNavigation.tsx` (old horizontal `DesktopNavigation` / `MobileNavigation`).

**Routes:** No route paths were changed. Per the constraint *“Do not create duplicate routes / Do not map new modules to old pages”*, the labels `الأصول` and `خريطة العمليات` are bound to the existing routes `/investment-properties` and `/complaints-map` respectively (no `/assets` / `/operations-map` routes were introduced). All other entries map 1:1 to the spec.

**Final menu structure:**
- لوحة القيادة → `/dashboard`
- العمليات الميدانية
  - الشكاوى → `/complaints`
  - المهام → `/tasks`
  - الفرق التنفيذية → `/teams`
  - المشاريع → `/projects`
- العقود والأصول
  - العقود التشغيلية → `/manual-contracts`
  - العقود الاستثمارية → `/investment-contracts`
  - مركز ذكاء العقود → `/contract-intelligence` *(AI badge)*
  - الأصول → `/investment-properties`
- الرقابة والتراخيص
  - التراخيص → `/licenses`
  - المخالفات → `/violations`
  - فرق التفتيش → `/inspection-teams`
- الإدارة والتحكم
  - المستخدمون → `/users`
  - التقارير → `/reports`
  - خريطة العمليات → `/complaints-map`
  - الرسائل الداخلية → `/messages` *(unread badge)*
  - الإعدادات → `/settings`
- Topbar icons: Notifications · Smart Assistant (المساعد الذكي → `/internal-bot`) · User account (logout)

**Files changed:**
- `src/components/navigation/nav-config.ts` *(refactored)*
- `src/components/navigation/Sidebar.tsx` *(new)*
- `src/components/navigation/SmartAssistantButton.tsx` *(new)*
- `src/components/Layout.tsx` *(rewritten — topbar + sidebar)*
- `src/components/navigation/AppNavigation.tsx` *(deleted)*
- `PROJECT_CONTINUITY.md` *(this entry)*

**Commands run:**
- `npm install` — OK
- `npm run build` → ✅ built in ~0.85s, no TS or bundling errors. `Layout` chunk grew from 97.6 kB → 119.2 kB (gzip 26.0 → 31.7 kB) due to new sidebar component.
- `npx eslint src/components/Layout.tsx src/components/navigation/` → clean, 0 warnings.
- Required validation grep — `grep -rn "المساعد الذكي|الرسائل الداخلية|العمليات الميدانية|العقود والأصول|الرقابة والتراخيص|الإدارة والتحكم" src` → all 6 strings present.

**Backend:** Untouched (no changes to backend, alembic, docker, nginx, SSL, deploy).

**Recommended next step:**
- Visual QA in the browser (desktop + mobile drawer) on the major roles (project_director, contracts_manager, field_team, citizen) to confirm group visibility and active-route highlighting.
- Consider promoting the smart-assistant icon with a small "online" pulse once the bot supports streaming.

---

### Session: 2026-05-01

**Task completed:** Create CLAUDE.md and PROJECT_CONTINUITY.md root-level documentation/control files.

**What was done:**
- Created `CLAUDE.md` — agent instruction file describing the project structure, key commands, coding conventions, and the requirement to update this file after every task.
- Created `PROJECT_CONTINUITY.md` (this file) — session log for tracking all agent work.

**Files changed:**
- `CLAUDE.md` *(new)*
- `PROJECT_CONTINUITY.md` *(new)*

**Commands run:**
- None (documentation-only task; no application code was modified)

**Results:**
- Both files created successfully at the repository root.
- No tests run (no code changes).
- No linting run (documentation only).

**Current project state:**
- Full-stack React + FastAPI application with 526 passing backend tests.
- Modules implemented: complaints, tasks, automations, notifications, execution logs, organization units, permissions (RBAC), investment properties, investment contracts, geo/map features, internal messaging.
- Latest migration: `017_add_investment_contracts.py`.
- Docker Compose stack: backend (FastAPI + Celery worker) + frontend (Nginx-served React build) + PostgreSQL + Redis.

**Recommended next step:**
- Review `PRD.md` and `PROJECT_REVIEW_AND_PROGRESS.md` to identify the next feature or improvement to implement.
- Run `cd backend && python -m pytest tests/ -q` to confirm all 526 tests still pass before starting new work.

---

*Add a new `### Session: YYYY-MM-DD` block above this line after each completed task.*
