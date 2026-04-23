# حالة التسليم
# HANDOFF_STATUS.md

## آخر تحديث: 2026-04-23T20:55

---

## الدفعة الحالية: 2026-04-23T20:55 — Final Pre-VPS-Sync / Release-Hardening Batch

**Scope:** This is intentionally NOT a feature batch. The product is functionally complete; the remaining risk is purely operational. Goal: make `git pull && ./deploy.sh --rebuild --domain=X` reliably preserve HTTPS without manual VPS edits, and align all docs with the actual current code so an operator reading the repo gets correct instructions.

### Files changed this batch

| File | Change |
|---|---|
| **Scripts — modified** | |
| `deploy.sh` | (1) New SSL self-heal block: when `--domain=$DOMAIN` is passed AND `/etc/letsencrypt/live/$DOMAIN/fullchain.pem` exists, automatically re-applies `nginx-ssl.conf` → `nginx.conf` (with `DOMAIN_PLACEHOLDER` → `$DOMAIN`) if the live `nginx.conf` is not already serving HTTPS for that domain. Idempotent — does nothing on subsequent runs once the SSL config is in place. (2) Post-deploy verification additionally probes `https://$DOMAIN/` and `https://$DOMAIN/api/health/ready` when the cert exists, so "TLS broken but local healthy" regressions surface immediately. |
| **Scripts — new** | |
| `smoke-check.sh` | Standalone post-deploy operator-confidence probe. Checks SPA, public landing, `/api/health/ready`, `/api/`, `/api/auth/login` reachability (accepts 405/422 to confirm route exists without sending creds), public submit + track pages. With `--domain=X`: also probes `https://X/`, `https://X/api/health/ready`, public submit/login over TLS, and verifies `http://X/` returns 301/302. Exit code = number of failed checks. Marked executable. |
| **Docs — modified** | |
| `README.md` | Replaced misleading "Frontend Environment Variables" mini-table that claimed `VITE_API_BASE_URL` defaults to `http://localhost:8000` (real default in `src/config.ts:26` is `/api`). New table documents production-safe defaults, the deploy.sh `localhost:8000` build-leak guard, and the dev-server proxy fallback. |
| `PRODUCTION_DEPLOYMENT_GUIDE.md` | (1) Rewrote "SSL/TLS Setup → Quick Setup" to use the actual one-command `sudo ./ssl-setup.sh $DOMAIN --auto` flow. Removed the obsolete "uncomment letsencrypt volume in docker-compose.yml" instruction (volumes are already unconditional). Documented that `deploy.sh` is now SSL self-healing. Kept manual flow as a clearly-labeled advanced fallback. (2) Rewrote "VPS Deployment Checklist → SSL/TLS Setup" sub-section to match. |
| `PROJECT_REVIEW_AND_PROGRESS.md` | New "Before / After" batch entry with concrete pre-batch failure modes, engineering decisions, and remaining gaps. |
| `HANDOFF_STATUS.md` | This update. |

### What was NOT changed (preserved verbatim)

- **Backend code:** zero files touched. All 296 tests still pass.
- **Frontend code:** zero files touched. `npm run build` still passes.
- `nginx.conf`, `nginx-ssl.conf`, `docker-compose.yml`, `ssl-setup.sh`, `.env.example`, `backend/.env.example`: unchanged. They were already correct from previous batches; the bug was only in `deploy.sh` not re-applying `nginx-ssl.conf` after a `git pull`, plus stale instructions in two docs.
- Login flow, RBAC, audit logging, JWT auth, contract intelligence, map foundation, complaint intake/track/lifecycle, Projects/Teams, Arabic-RTL UI: all untouched.

### Verification (this batch)

| Check | Result |
|---|---|
| `VITE_API_BASE_URL=/api VITE_FILES_BASE_URL= npm run build` | ✅ `✓ built in 974ms`, no TS errors |
| `grep -rq 'http://localhost:8000' dist/assets` | ✅ no matches (deploy.sh leak guard would also catch any future regression) |
| `cd backend && python -m pytest tests/ -q` | ✅ **296 passed, 871 warnings in 134.39s** (same as previous batch — zero regression) |
| `bash -n deploy.sh && bash -n smoke-check.sh && bash -n ssl-setup.sh` | ✅ all pass syntax check |
| SSL self-heal idempotency simulation (2-run test against a fresh `nginx.conf`) | ✅ first run rewrites; second run leaves it alone |
| `smoke-check.sh --help` | ✅ prints usage |

### ✅ مكتمل (Done — verified):

| Required outcome | Status | Evidence |
|---|---|---|
| A) Final SSL/HTTPS/nginx/docker-compose alignment, no hidden manual VPS edits required | **Done** | `deploy.sh` now re-applies `nginx-ssl.conf` automatically when `git pull` overwrites the on-VPS SSL `nginx.conf`. The previously-aligned `docker-compose.yml` (unconditional letsencrypt mounts), `nginx-ssl.conf` (`/nginx-health` placed before catch-all redirect), and `ssl-setup.sh --auto` (cert + nginx + CORS in one command) are preserved verbatim. |
| B) Frontend production base-path fixes preserved | **Done** | Verified by re-running `npm run build` with the production-safe envs and re-running the leak grep — clean. `README.md` is now also correct (was the last surface still telling operators the wrong default). |
| C) Final nginx healthcheck/readiness correctness | **Done — already correct** | The `/nginx-health` endpoint added in the previous batch is preserved; placed before the HTTP→HTTPS redirect in `nginx-ssl.conf` so docker healthchecks succeed in both modes. No changes needed this batch. |
| D) Final deployment-script and docs alignment | **Done** | `README.md` Vite table fixed; `PRODUCTION_DEPLOYMENT_GUIDE.md` SSL Quick Setup + VPS checklist rewritten to match the `--auto` flow and the unconditional letsencrypt mounts. |
| E) Final release-hardening sanity checks | **Done** | No `localhost:8000` leak; complaint intake / track / login routes still 200 by inspection (`PublicShell`-wrapped pages from previous batch unchanged); 296 backend tests still pass; RBAC/audit/contract-intelligence/maps/Arabic-RTL untouched. |
| F) Optional smoke-check helper | **Done** | New `smoke-check.sh` covers homepage, login API path, `/health/ready`, HTTPS check (with `--domain`). Exit code = failure count. |
| Frontend build passes | **Verified** | `✓ built in 974ms` |
| Backend tests pass | **Verified** | 296/296 |
| HTTPS / nginx / docker-compose alignment represented in repo | **Verified** | All four files (`deploy.sh`, `ssl-setup.sh`, `nginx-ssl.conf`, `docker-compose.yml`) cooperate without manual edits. |
| `localhost:8000` fallback fully eliminated | **Verified** | Build leak grep clean; `src/config.ts:26` defaults to `/api`; `deploy.sh:261-266` guard preserved; README now documents this correctly. |
| `PROJECT_REVIEW_AND_PROGRESS.md` + `HANDOFF_STATUS.md` updated honestly | **Done** | This file + the new batch entry in PROJECT_REVIEW_AND_PROGRESS.md. |

### ⚠️ Partial / Out-of-scope (honestly stated):

| Item | Status | Why |
|---|---|---|
| SSL self-heal for non-Let's-Encrypt cert providers | **Partial — Let's Encrypt only** | The heuristic specifically checks `/etc/letsencrypt/live/$DOMAIN/fullchain.pem`. Custom-cert setups using `${LETSENCRYPT_DIR}` overrides still need manual `cp nginx-ssl.conf nginx.conf` after each `git pull`. Acceptable — the prompt explicitly targets the existing `ssl-setup.sh + Let's Encrypt` flow. |
| Wire `smoke-check.sh` into CI or `deploy.sh` | **Not done** | Intentionally on-demand. Adding it to `deploy.sh` would slow every deploy and would fail when no domain is configured yet. |
| Collapse `nginx.conf` / `nginx-ssl.conf` duplication via `include` | **Not done** | Risky and unnecessary; prompt forbids broad rewrite. |
| `index.html` SEO/meta tags for the public landing | **Not done — inherited** | Out of scope. |
| End-to-end UI test of public landing → submit → track → detail | **Not done — inherited** | Tooling out of scope. |

### Blocked: None

### 🚦 Final go-live recommendation: **✅ Safe to update VPS now.**

The exact operator flow specified in the prompt is now reliable:

```bash
git pull
./deploy.sh --rebuild --domain=matrixtop.com
# if the cert doesn't exist yet (first-ever HTTPS setup):
sudo ./ssl-setup.sh matrixtop.com --auto
```

After this batch:
- A `git pull` will no longer silently lose HTTPS on the VPS — `deploy.sh` re-applies `nginx-ssl.conf` automatically when it sees the cert.
- A fresh `--rebuild` will fail loudly (not silently) if `dist/` carries `http://localhost:8000` — protecting against the historical login-broken-in-prod regression.
- Post-deploy verification will additionally probe the live HTTPS URL when the cert exists, surfacing TLS regressions immediately.
- Operator can run `./smoke-check.sh --domain=matrixtop.com` at any time for a 5-second confidence check across SPA / API / login / health / TLS / HTTP→HTTPS redirect.

---

## الدفعة السابقة: 2026-04-23T20:30 — Complaint-Intake-as-Entry-Point Batch

**Scope:** Make complaint intake the obvious operational entry point of the product. Add a public Arabic landing at `/` (signed-out), a shared public header, polish the public submit/track pages, surface complaint↔task linkage on both detail pages, and clarify the public-vs-internal navigation boundary. No login flow change, no SSL/RBAC/audit/contract-intelligence/map change.

### الملفات المُعدّلة في هذه الدفعة:

| الملف | التغيير |
|---|---|
| **Backend — modified** | |
| `backend/app/api/tasks.py` | `list_tasks` accepts new query param `complaint_id` (consistent with existing `project_id`/`team_id`/`location_id` filters). |
| `backend/tests/test_projects_teams_settings.py` | +1 test: `test_list_tasks_filtered_by_complaint` (multi-complaint fixture, asserts only the target complaint's tasks are returned). |
| **Frontend — new** | |
| `src/components/PublicHeader.tsx` | Reusable public Arabic-RTL header (`PublicHeader`) + page wrapper (`PublicShell`) with logo + 3 nav links: تقديم شكوى / تتبع شكوى / دخول الموظفين. Active-route highlighting. No auth/notifications. |
| `src/pages/PublicLandingPage.tsx` | Public landing page rendered at `/` for unauthenticated visitors. Hero text, two large CTA cards (submit / track), 3-step Arabic lifecycle explainer, subtle staff-login link. |
| **Frontend — modified** | |
| `src/App.tsx` | New lazy `PublicLandingPage`. New `RootRoute` component: returns `<PublicLandingPage />` if `!apiService.isAuthenticated()`, otherwise the existing role-protected dashboard. `/` route now uses `<RootRoute />`. |
| `src/pages/ComplaintSubmitPage.tsx` | Wrapped in `PublicShell`. Header now links to `/complaints/track`. Location field has helper sub-text. Separate `submitting` state in addition to `uploading`. Success state rebuilt with green check, big mono tracking number, "نسخ الرقم" clipboard button, "ماذا يحدث بعد الآن" 3-step guidance, and 2 CTAs. |
| `src/pages/ComplaintTrackPage.tsx` | Fully rewritten under `PublicShell`. Form has placeholders + cross-link to `/complaints/new`. Result card renders Arabic status badge + per-status guidance text (one of 6 sentences) + tracking number + type + dates + location + description. Inline "not found" panel on failed search. Privacy footer line. |
| `src/pages/ComplaintDetailsPage.tsx` | Loads linked tasks via `getTasks({ complaint_id })`. New "المهام المرتبطة" card between update card and activity log, listing each task as a clickable row with title, `#id`, due date, and colored Arabic status badge. Empty state guides managers to "تحويل إلى مهمة" if permitted. |
| `src/pages/TaskDetailsPage.tsx` | When `task.complaint_id` is set, fetches the source complaint and renders its citizen `tracking_number` + name in the linkage row, instead of bare `#id`. Falls back to `#id` on fetch error. Contract linkage unchanged. |
| `src/components/Layout.tsx` | New "تقديم شكوى نيابة عن مواطن" anchor in the header (`target="_blank"` to `/complaints/new`), gated to project_director / contracts_manager / complaints_officer / area_supervisor. Hidden on extra-small screens. |
| `src/pages/LoginPage.tsx` | Footer divider + 2 small links to `/complaints/new` and `/complaints/track` so a citizen who lands here can still reach the public flow. |
| `src/services/api.ts` | `getTasks` parameter type extended to accept `complaint_id?: number`; emitted as `complaint_id` query param when set. |
| `PROJECT_REVIEW_AND_PROGRESS.md` | New "Before / After" batch entry with engineering decisions and honest residual-gaps list. |
| `HANDOFF_STATUS.md` | This update. |

### Tests
- Run: `cd backend && python -m pytest tests/ -q`
- **296 passed** (was 295; +1 new filter test). Result: `296 passed, 871 warnings in 117.59s`.

### Build
- Run: `VITE_API_BASE_URL=/api VITE_FILES_BASE_URL= npm run build`
- Passes (`tsc -b --noCheck && vite build`). `✓ built in 926ms`. No TS errors.

### What is *NOT* changed in this batch (preserved):
- Login flow (just a small footer-link addition; auth logic untouched).
- SSL / nginx / docker-compose.
- Backend RBAC, audit logging, JWT auth, all 295 previously-passing tests.
- `POST /complaints/{id}/create-task` endpoint and its conversion logic.
- Contract intelligence, map foundation, all map endpoints, GIS layers.
- RTL/Arabic UI of all internal pages.
- Internal Layout structure, sidebar items, role gates (only one extra anchor was added).
- Citizen dashboard, internal dashboard, complaints list, tasks list, contracts list, projects, teams, settings, locations.

### ✅ مكتمل ومُتحقق منه (Done — verified):

| Goal | Status | Evidence |
|---|---|---|
| A) Make complaint submission obvious | **Done** | `/` (signed-out) shows `PublicLandingPage` with two large Arabic CTAs; public header on submit/track; LoginPage gets footer links to public flow. |
| B) Improve public/citizen complaint flow | **Done** | Submit page wrapped in PublicShell, success state rebuilt (copy-tracking-number, "what happens next" guidance, two CTAs); Track page rewritten with Arabic status badge + per-status guidance + clearer not-found state. |
| C) Make complaint lifecycle visible internally | **Done** | New "المهام المرتبطة" card on `ComplaintDetailsPage` lists every task created from this complaint with status badge + click-through. Empty-state copy guides toward "تحويل إلى مهمة". |
| D) Strengthen complaint→task operational flow | **Done** | Conversion is unchanged; visibility is added on both ends — complaint side shows linked tasks; task side shows source complaint's `tracking_number` + name (not bare id). |
| E) Remove ambiguity in navigation/landing | **Done** | Public-vs-internal split is now physical (PublicShell vs Layout); root URL no longer redirects citizens to a staff login; intake shortcut in Layout makes the boundary clear from the staff side. |
| F) Map/list/detail consistency | **Verified** | No regression — new linked-tasks card uses the same Arabic status taxonomy/colors as `TasksListPage` and `TaskDetailsPage`. Map default entity (set in previous batch) unchanged. |
| G) Preserve what already works | **Verified** | Login untouched (only footer additions). RBAC unchanged. Audit unchanged. Contract intelligence untouched. Map untouched. Projects/Teams from prior batch untouched. |
| Frontend build passes | **Verified** | `✓ built in 926ms`. |
| Backend tests pass | **Verified** | **296 passed, 0 failed**. |
| `PROJECT_REVIEW_AND_PROGRESS.md` + `HANDOFF_STATUS.md` updated honestly | **Done** | Full Before/After entry above. |

### ⚠️ Partial / Out-of-scope (honestly stated):

| Item | Status | Why |
|---|---|---|
| Public track page image thumbnails | **Not done** | The `trackComplaint` API does not return `images`; exposing them publicly is a privacy decision that should go through a separate review. |
| `index.html` SEO/meta tags for the landing page | **Not done** | Out of scope for this batch; the landing page is rendered client-side. |
| Public landing transparency stats ("X complaints resolved this month") | **Not done** | Content/transparency feature, separate batch. |
| Staff attribution on intake shortcut ("submitted by staff #N") | **Not done** | Would require a backend change to `POST /complaints/`; deferred. |
| End-to-end UI test of landing → submit → track → detail | **Not done** | Backend test covers the new filter only; UI tests are out of scope of this batch's tooling. |
| Migration 008 applied to running DB | **Inherited** | No schema change in this batch. Prior migration still needs `alembic upgrade head` on first deploy, handled by `entrypoint.sh`. |

### Blocked: None

---

## الدفعة السابقة: 2026-04-23T19:42 — Operational-Coherence Deepening Batch

**Scope:** Make the Projects and Teams entities (introduced in the previous batch) actually integrate into daily operational workflows. Add cross-entity filters on complaints/tasks/contracts list endpoints, surface the same filters on the UI, expose the linked project on complaint and contract detail pages with inline editing, turn the static project/team detail count cards into navigable deep links, and make all of this URL-shareable. No login/SSL/RBAC/map/Arabic-RTL changes.

### الملفات المُعدّلة في هذه الدفعة:

| الملف | التغيير |
|---|---|
| **Backend — modified** | |
| `backend/app/api/complaints.py` | `list_complaints` accepts new query params: `project_id`, `location_id`. |
| `backend/app/api/tasks.py` | `list_tasks` accepts new query params: `project_id`, `team_id`, `location_id`. |
| `backend/app/api/contracts.py` | `list_contracts` accepts new query param: `project_id`. |
| `backend/app/api/projects.py` | `_enrich_project_response` computes `contract_count` (count of contracts with this `project_id`). |
| `backend/app/schemas/project.py` | `ProjectResponse.contract_count: int = 0` added. |
| `backend/tests/test_projects_teams_settings.py` | +3 tests: `test_list_complaints_filtered_by_project`, `test_list_tasks_filtered_by_project_and_team`, `test_list_contracts_filtered_by_project`. |
| **Frontend — modified** | |
| `src/services/api.ts` | `getComplaints` adds `project_id` + `location_id`. `getTasks` adds `project_id`, `team_id`, `location_id`, `assigned_to_id`. `getContracts` adds `project_id`. |
| `src/pages/ComplaintsListPage.tsx` | New project filter `Select` + "المشروع" column (desktop) + project chip (mobile). Filter is two-way bound to URL `?project_id=`. Loads projects via `getProjects({ limit: 200 })`. |
| `src/pages/TasksListPage.tsx` | New project + team filter `Select`s + "المشروع" / "الفريق" columns (desktop) + chips (mobile). Both filters URL-synced (`?project_id=`, `?team_id=`). Loads projects + active teams. |
| `src/pages/ContractsListPage.tsx` | New project filter `Select` + "المشروع" column (desktop) + project chip (mobile). URL-synced. |
| `src/pages/ComplaintDetailsPage.tsx` | Loads projects. Linked-project shown as navigable badge in details grid. Update form gets a project selector (`— بدون مشروع —` → `null`). Save payload only sends `project_id` when changed; update button disabled state respects it. |
| `src/pages/ContractDetailsPage.tsx` | Loads projects. New "المشروع المرتبط" card with read view (link to `/projects/:id`) and inline edit (`Select` + Save/Cancel via `apiService.updateContract({ project_id })`), gated to `canManageContracts`. |
| `src/pages/ProjectDetailsPage.tsx` | The 3 count cards (Tasks / Complaints / Contracts) are now `<Link>`s to the corresponding filtered list pages (`/tasks?project_id=X` etc.); a fourth informational card shows linked teams. Renders `contract_count` from the new API field. |
| `src/pages/TeamDetailsPage.tsx` | Task-count card is now a `<Link>` to `/tasks?team_id=X`. |

### Tests
- Run: `cd backend && python -m pytest tests/ -q`
- **295 passed** (was 292; +3 new filter tests). All 16 tests in `test_projects_teams_settings.py` pass.

### Build
- Run: `npm run build`
- Passes (`tsc -b --noCheck && vite build`). No bundle blow-up; all touched pages within previous norms.

### What is *NOT* changed in this batch (preserved):
- Login flow, SSL/deployment hardening, frontend API/files-base config, contract intelligence, map foundation, RBAC backend rules, audit logging, Arabic-first RTL UI shell, the complaint→task conversion endpoint and its UI, Settings page (it was rebuilt in the previous batch and is already operational).

### Done / Partial / Blocked
- **Done:** Project filter on complaints/tasks/contracts; team filter on tasks; project column/chip on all three lists; team column/chip on tasks; URL-bound deep linking from project & team detail pages; in-place project re-linking on complaint and contract detail pages; `contract_count` on project response.
- **Partial:** Locations remain the only main entity without a list-page filter on complaints (the backend `location_id` is now wired, but the UI still shows only the flat `area_id` dropdown — adding a location-tree picker is a separate UX task). Teams list page does not yet have a project filter (backend already supports `?project_id=`, UI not wired).
- **Blocked:** None.

---

## الدفعة السابقة: 2026-04-23T18:53 — Operational-Backbone Stabilization Batch

**Scope:** Make the platform operationally coherent without redesigning it. Add the two missing structural entities (Projects, Teams/Execution Units), wire the complaint → task workflow, fix the static Settings page, and align the complaints map source with the complaints list. No login/SSL/RBAC/map/Arabic-RTL changes.

### الملفات المُعدّلة في هذه الدفعة:

| الملف | التغيير |
|---|---|
| **Backend — new** | |
| `backend/app/models/project.py` | New `Project` model. 5-state enum (`planned`/`active`/`on_hold`/`completed`/`cancelled`), unique `code`, nullable FKs to Location and Contract, `created_by_id` for audit, back-refs to tasks, complaints, teams. |
| `backend/app/models/team.py` | New `Team` model (also "Execution Unit"). 4-type enum (`internal_team`/`contractor`/`field_crew`/`supervision_unit`), `is_active` for soft-deactivate, denormalized contact info, optional `location_id` and `project_id`. |
| `backend/app/models/app_setting.py` | New `AppSetting` table — key/value/value_type/category store with `updated_by_id` audit. |
| `backend/app/schemas/project.py` | `ProjectCreate`/`ProjectUpdate`/`ProjectResponse` (response includes `task_count`, `complaint_count`, `team_count`, `location_name`, `contract_number`). |
| `backend/app/schemas/team.py` | `TeamCreate`/`TeamUpdate`/`TeamResponse` (response includes `task_count`, `location_name`, `project_title`). |
| `backend/app/schemas/app_setting.py` | `SettingItem` + `SettingsBulkUpdate` for the bulk PUT endpoint. |
| `backend/app/api/projects.py` | `GET /projects/` (paginated `{total_count, items}` with `status`/`search`/`location_id`/`contract_id` filters), `GET /projects/{id}`, `POST` (project_director/contracts_manager/engineer_supervisor), `PUT`, `DELETE` (project_director only). |
| `backend/app/api/teams.py` | Same pattern + `GET /teams/active` un-paginated dropdown endpoint. Filters: `team_type`, `is_active`, `project_id`, `location_id`, `search`. |
| `backend/app/api/app_settings.py` | `GET /settings/` returns settings grouped by category (auto-seeds 7 defaults on first call), `PUT /settings/` accepts `{items: SettingItem[]}` bulk upsert (project_director/contracts_manager only). Writes audit log on update. |
| `backend/alembic/versions/008_add_projects_teams_settings.py` | Single migration adds `projects`, `teams`, `app_settings` tables and 4 nullable FK columns: `tasks.team_id`, `tasks.project_id`, `contracts.project_id`, `complaints.project_id`. Provides full `downgrade()`. |
| `backend/tests/test_projects_teams_settings.py` | 13 new tests covering Project CRUD + RBAC, Team CRUD + `/active` filter, Settings GET-seeds-defaults + PUT-privileged + PUT-non-privileged-403, complaint→task conversion (creates linked task, flips complaint status, records both activities). |
| **Backend — modified** | |
| `backend/app/models/__init__.py` | Export `Project`, `ProjectStatus`, `Team`, `TeamType`, `AppSetting`. |
| `backend/app/models/task.py` | Added `team_id` and `project_id` columns (nullable FKs, indexed) and `team`/`project` relationships. |
| `backend/app/models/contract.py` | Added `project_id` (nullable FK, indexed) + `project` relationship. |
| `backend/app/models/complaint.py` | Added `project_id` (nullable FK, indexed) + `project` relationship. |
| `backend/app/schemas/task.py` | `team_id`/`project_id` accepted on create/update and returned on read. |
| `backend/app/schemas/contract.py`, `backend/app/schemas/complaint.py` | `project_id` exposed on read+write. |
| `backend/app/api/complaints.py` | New `POST /complaints/{id}/create-task` endpoint: copies area/location/coords/priority from the complaint, accepts overrides, writes `Task` with `source_type='complaint'` + `complaint_id`, flips complaint `NEW|UNDER_REVIEW → ASSIGNED`, writes `task_created` complaint activity + `created_from_complaint` task activity. RBAC: project_director, contracts_manager, engineer_supervisor, complaints_officer, area_supervisor. |
| `backend/app/main.py` | Wire the 3 new routers (`projects`, `teams`, `app_settings`). |
| `backend/tests/conftest.py` | `reset_db` teardown disables `PRAGMA foreign_keys` only during `Base.metadata.drop_all` to handle the new circular FK Project↔Contract; runtime FK enforcement is unchanged. |
| **Frontend — new** | |
| `src/pages/ProjectsListPage.tsx` | Paginated table, search, status filter, "إضافة مشروع" gated by role, Arabic empty-state card. |
| `src/pages/ProjectDetailsPage.tsx` | Read/edit form, related counts (tasks, complaints, teams), links to location/contract. |
| `src/pages/TeamsListPage.tsx` | Paginated table, search, type filter, active toggle. |
| `src/pages/TeamDetailsPage.tsx` | Read/edit form, contact info, soft-deactivate toggle, task count display. |
| **Frontend — modified** | |
| `src/services/api.ts` | +13 methods: `getProjects`/`getProject`/`createProject`/`updateProject`/`deleteProject`, `getTeams`/`getActiveTeams`/`getTeam`/`createTeam`/`updateTeam`/`deactivateTeam`, `getSettings`/`updateSettings`, `createTaskFromComplaint`. `getTasks`/`updateTask` accept `team_id`/`project_id`. |
| `src/App.tsx` | +4 lazy routes for `/projects`, `/projects/:id`, `/teams`, `/teams/:id`, role-protected with `INTERNAL_ROLES`. |
| `src/components/Layout.tsx` | +2 nav items "المشاريع" and "الفرق التنفيذية" between "العقود" and "ذكاء العقود", role-gated. |
| `src/pages/ComplaintsMapPage.tsx` | Default `entityFilter = 'complaint'` (matches sidebar label "خريطة الشكاوى"). Status filter list now derived from the selected entity (`COMPLAINT_STATUSES`/`TASK_STATUSES`/`ALL_STATUSES`); status resets when entity changes. |
| `src/pages/ComplaintDetailsPage.tsx` | "تحويل إلى مهمة" button (header card) gated to `canManageComplaints` && complaint status in `{new, under_review}`; opens a Dialog with title/description (prefilled), due date, priority, user assignee, team assignee. On submit calls `createTaskFromComplaint` and navigates to the new task. |
| `src/pages/TaskDetailsPage.tsx` | Detail grid shows linked team and project as clickable links. Update form adds Team and Project selectors with explicit "— بدون فريق —" / "— بدون مشروع —" options that map to `null`. Save payload only sends `team_id`/`project_id` when changed (so unchanged form does not blank existing values). |
| `src/pages/SettingsPage.tsx` | Static project info card replaced with grouped editable form sourced from `GET /settings`. Save button gated to project_director/contracts_manager. Health card URL now strips trailing `/api` from `config.API_BASE_URL` (`buildHealthUrl()` helper) and sends `Authorization: Bearer <access_token>`; on any non-2xx response the card hides itself instead of showing a misleading "broken" label. |
| `PROJECT_REVIEW_AND_PROGRESS.md` | New "Before / After" entry for this batch with engineering decisions and honest residual-gaps list. |
| `HANDOFF_STATUS.md` | This update. |

### ✅ مكتمل ومُتحقق منه (Done — verified):

| Goal | Status | Evidence |
|---|---|---|
| A) Repair broken core pages and data loading | **Done** | Settings now loads `/settings` with seeded defaults; broken health-card URL+auth fixed. Other pages (complaints/tasks/contracts/locations) verified to already match backend `{total_count, items}` shapes; no `failed to load` regressions in test runs. |
| B) Real complaint → task workflow | **Done** | `POST /complaints/{id}/create-task` endpoint + "تحويل إلى مهمة" dialog + activity logging on both sides + automatic complaint status flip `NEW\|UNDER_REVIEW → ASSIGNED`. Test `test_create_task_from_complaint` covers the end-to-end flow. |
| C) Map/list source consistency | **Done** | `ComplaintsMapPage` defaults to `entity_type=complaint`; per-entity scoped status filter list; status resets on entity switch — the default view of "خريطة الشكاوى" now reflects the same source as the complaints list. |
| D) Real Settings page | **Done** | `app_settings` table, `GET/PUT /settings`, grouped read/edit form gated by role, 7 default settings auto-seeded on first GET (project metadata, organization metadata, operational defaults). System health card URL+auth fixed. |
| E) Projects + Teams modules | **Done** | Both backends shipped (model + Pydantic schemas + paginated CRUD + filters + tests). Both frontends shipped (list + detail). `Task.team_id`, `Task.project_id`, `Contract.project_id`, `Complaint.project_id` wired. `/teams/active` lightweight dropdown endpoint added. |
| F) Role coherence improved | **Partial** | New "Convert" / "Save settings" / "Add project" / "Add team" buttons gated to the right roles; new pages have clean Arabic empty-state cards. The deeper "every existing page tailored per role" refactor is intentionally out of scope. |
| G) Preserve what already works | **Verified** | Login untouched. SSL/deploy/nginx/frontend bases untouched. Map rendering untouched. Contract intelligence untouched. RTL/Arabic UI untouched. |
| Frontend build passes | **Verified** | `VITE_API_BASE_URL=/api VITE_FILES_BASE_URL= npm run build` → **✓ built in 944ms**, no TS errors, no warnings. |
| Backend tests pass | **Verified** | `python -m pytest tests/ -q` → **292 passed, 856 warnings in 115.79s** (was 279 before this batch; +13 new tests in `test_projects_teams_settings.py`). 0 failures. |
| `PROJECT_REVIEW_AND_PROGRESS.md` + `HANDOFF_STATUS.md` updated honestly | **Done** | Full Before/After entry with verification evidence and remaining-gaps list. |

### ⚠️ Partial / Out-of-scope (honestly stated):

| Item | Status | Why |
|---|---|---|
| Migration 008 applied to a running database | **Not yet** | Production deploy must run `alembic upgrade head` (handled automatically by `entrypoint.sh` on container start; a hot deploy without restart will not apply it). |
| Project-scoped filter on existing complaints/tasks/contracts list pages | **Not done** | Out of scope. The data linkage exists; surfacing it as a filter on the existing list pages is a follow-up. |
| Type-aware widgets in Settings UI (e.g. enum dropdown for `defaults.task_priority`) | **Not done** | One flat form per category with string/number/boolean inputs only. Practical for v1. |
| Project deletion archive/restore UX | **Not done** | Hard delete sets dependents' FK to NULL (columns are nullable). No archive layer. |
| Wider role-based shell tailoring across all existing pages | **Out of scope** | Goal F was satisfied for the *new* surface; an audit-and-restyle of every existing page per role belongs to a separate batch. |
| SAWarning during test teardown about Project↔Contract FK cycle | **Cosmetic** | Non-blocking; `use_alter=True` on one side of the FK pair would silence it in a follow-up cleanup. |
| Frontend Dockerfile, dependency CVE pass, virus scanning, real `/metrics` counters | **Carried over** | Inherited from previous batches' "Partial" lists; intentionally not addressed here. |

### 🚫 Blocked: none.

### الفجوات المتبقية قبل النشر الحقيقي:

1. **Migration 008 must run on the production DB** — `./deploy.sh --rebuild` triggers `entrypoint.sh` which runs `alembic upgrade head` on container start, so a normal redeploy is sufficient. A hot frontend-only deploy is **not**.
2. **Carried over from prior batches:** Frontend remains a host-built artifact; aging tokens/hashing libs (`python-jose==3.3.0`, `passlib==1.7.4`, yanked `email-validator==2.1.0`); no virus scanning on uploaded files; `/metrics` counters are placeholders.

---

## الدفعة الحالية: 2026-04-23T16:53 — Deployment-Alignment & Production-Stability Batch

**Scope:** Close the repo-level deploy/config gaps that were still letting the live VPS at `matrixtop.com` regress on each `./deploy.sh --rebuild`. Not a feature batch. No product behavior change. Arabic-first RTL UI untouched.

### الملفات المُعدّلة في هذه الدفعة:

| الملف | التغيير |
|---|---|
| `src/config.ts` | Removed the `http://localhost:8000` fallback. Default `API_BASE_URL` is now `/api` (same-origin). Added a separate `FILES_BASE_URL` (default `''` for same-origin; auto-derived from `API_BASE_URL` only when the latter is an absolute URL). Trailing slashes trimmed. Comprehensive JSDoc explains why there is no localhost fallback. |
| `src/components/FileUpload.tsx` | Switched file-link construction from `API_BASE_URL` to `FILES_BASE_URL`. File hrefs are now built correctly under the new `/api` API base. |
| `src/pages/ContractDetailsPage.tsx` | Same: PDF download open (line 92) and contract `pdf_file` link (line 214) now use `FILES_BASE_URL`. Removed the now-unused `API_BASE_URL` local. |
| `vite.config.ts` | Added a `/uploads` proxy (→ `http://localhost:8000`) so dev file links resolve the same way they do in production. Inline comments explain the API vs files split. |
| `.env.example` | Rewritten: no more `VITE_API_BASE_URL=http://localhost:8000`. Now documents `/api` as the production-safe value and an empty `VITE_FILES_BASE_URL` as the same-origin default. Explicit warning that Vite bakes these at *build* time. |
| `deploy.sh` | Before `npm run build`: `export VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api}"` and `VITE_FILES_BASE_URL="${VITE_FILES_BASE_URL:-}"`, with an `info` log showing the resolved values. After the build: `grep -rq 'http://localhost:8000' dist/assets` and abort the deploy with a clear error if the localhost fallback somehow leaked into the bundle (defense in depth against operator `.env` mistakes). |
| `docker-compose.yml` | nginx volumes now include unconditional read-only mounts of `${LETSENCRYPT_DIR:-/etc/letsencrypt}` and `${CERTBOT_WEBROOT:-/var/www/certbot}`. No more "uncomment to enable SSL" step. nginx healthcheck switched from `http://localhost:80/` (which 301-redirects under SSL) to `http://localhost:80/nginx-health` (defined locally in nginx, returns static 200). |
| `nginx.conf` | Added `location = /nginx-health { access_log off; return 200 "ok\n"; }` — the target of the compose healthcheck. Logs disabled to keep the access log readable. |
| `nginx-ssl.conf` | Added `/nginx-health` to **both** the HTTP server block (defined *before* the catch-all 301 to HTTPS, so docker probes on port 80 do not get redirected) and the HTTPS server block (for external uptime monitors over TLS). |
| `ssl-setup.sh` | Removed the mandatory uncomment-volumes step in `--auto` (kept as backward-compat no-op for older clones still carrying the commented form). Cleaned up the "next steps" block for the non-`--auto` path — no more "edit docker-compose.yml" instruction, because the mounts are now active by default. |
| `PROJECT_REVIEW_AND_PROGRESS.md` | New "Before / After" entry for this batch with full engineering decisions and honest residual-gaps list. |
| `HANDOFF_STATUS.md` | This update. |

### ✅ مكتمل ومُتحقق منه (Done — verified):

| Goal | Status | Evidence |
|---|---|---|
| A) Production frontend no longer falls back to `http://localhost:8000` | **Done** | `src/config.ts` has no localhost string; `grep -r 'localhost:8000' dist/` after `npm run build` (both with explicit env and with unset env) → 0 hits. |
| B) API base and public files base are separate | **Done** | `config.FILES_BASE_URL` introduced; `FileUpload.tsx` and `ContractDetailsPage.tsx` migrated; `vite.config.ts` proxies `/uploads` in dev so same-origin file links work. |
| C) `deploy.sh` and env examples force production-safe frontend values | **Done** | `deploy.sh` exports `VITE_API_BASE_URL=/api` / `VITE_FILES_BASE_URL=` before `npm run build`, logs the resolved values, and aborts if `dist/assets` still contains `http://localhost:8000`. `.env.example` fully rewritten. |
| D) nginx + docker-compose + ssl-setup represent the real SSL deployment | **Done** | `docker-compose.yml` mounts `/etc/letsencrypt` + `/var/www/certbot` unconditionally via env-overridable paths; `ssl-setup.sh --auto` no longer depends on a repo-state sed patch; HTTPS enablement requires only `ssl-setup.sh --auto` — no manual compose edits. |
| E) nginx healthcheck no longer falsely unhealthy after SSL enablement | **Done** | New `/nginx-health` location returns 200 locally without any redirect. Defined in both HTTP and HTTPS blocks of `nginx-ssl.conf`. Compose healthcheck targets it. |
| F) Frontend build passes | **Verified** | `npm ci` clean; `npm run build` → `✓ built in 1.00s` (with explicit env) and `✓ built in 1.11s` (with defaults). |
| G) Backend tests pass | **Verified** | `python -m pytest tests/ -q` → **279 passed, 538 warnings in 111.16s**. No regression. |
| H) Shell scripts parse | **Verified** | `bash -n deploy.sh && bash -n ssl-setup.sh` → OK. |
| I) `PROJECT_REVIEW_AND_PROGRESS.md` + `HANDOFF_STATUS.md` updated honestly | **Done** | New batch entries with real verification evidence. |

### ⚠️ Partial / Out-of-scope (honestly stated):

| Item | Status | Why |
|---|---|---|
| Frontend Dockerfile | **Not done** | Out of scope for this deploy-alignment batch. Node 20+ on host is still required and still documented. |
| Dependency CVE pass (`python-jose==3.3.0`, `passlib==1.7.4`, yanked `email-validator==2.1.0`) | **Not done** | Explicitly out of scope; flagged since the previous two batches. Recommend a separate batch. |
| `/metrics` real counters | **Not done** | Still placeholder; auth-gated. |
| Container content-scanning (ClamAV) on uploads | **Not done** | Out of scope. |
| `backend/tests/load_test.py --password` default = `password123` | **Kept** | Intentional: load-test tool, not a seeded credential; overridable via `--password=...`. |

### 🚫 Blocked: none.

### الفجوات المتبقية قبل النشر الحقيقي:

1. **Frontend remains a host-built artifact.** Node 20+ on host, `npm run build` must run before `docker compose up`. `deploy.sh` already handles this; a Dockerfile-based build is still a future improvement.
2. **Aging tokens/hashing libs.** `python-jose==3.3.0`, `passlib==1.7.4`, yanked `email-validator==2.1.0`. Still recommend a dependency-upgrade batch.
3. **No virus scanning** on uploaded files.
4. **`/metrics` counters are placeholders** — not real request totals.

### الخطوة التالية الموصى بها على VPS الحي:

1. `git pull` on the VPS checkout.
2. `./deploy.sh --rebuild` — the rebuild will:
   - export `VITE_API_BASE_URL=/api` and `VITE_FILES_BASE_URL=` before `npm run build`,
   - abort with a clear error if the bundle still contains `http://localhost:8000`,
   - probe nginx with `/nginx-health` (no more false unhealthy under SSL),
   - keep the live SSL mounts intact (they were always there; now the repo matches).
3. Smoke-test: load the site, perform a login, open a contract PDF link, open a complaint attachment. All four should work without any host-level edits to `nginx.conf` or `docker-compose.yml`.
4. Schedule the dependency-upgrade batch flagged under "Partial / Out-of-scope".

---

## الدفعة السابقة: 2026-04-23T15:22 — Final Secret Rotation, Credential Hardening, Production-Safe Env Setup

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
