# Playwright E2E tests

Minimal end-to-end smoke suite for the Dummar project-management frontend.
Runs against a **live deployment** — no servers are spun up by the test runner.

## What it covers

A single spec, `e2e/dummar.spec.ts`, runs in this order:

1. Logs in as the seeded `director` account and verifies the dashboard renders.
2. Visits Users, Projects, Teams, Tasks, Complaints, Contracts via the SPA
   and asserts every page loads (header present, non-empty `<main>`, no raw
   FastAPI/HTML error text).
3. Creates one test user, project, team, and task via the authenticated REST
   API (token reused from the browser's `localStorage`). Records are tagged
   with a per-run prefix (`e2e-…`) and **cleaned up in `afterAll`** even when
   assertions fail.
4. Verifies each created record appears in its list page.
5. Logs out via the header button and verifies the redirect to `/login`.
6. Visits a protected route while unauthenticated and verifies the redirect
   to `/login`.

## Running

```bash
npm install                              # already includes @playwright/test
npx playwright install chromium          # one-time browser download

# Against a local dev stack (vite dev + backend on :8000):
npm run dev &                            # in another shell
npm run test:e2e

# Against a live deployment:
E2E_BASE_URL=https://your-domain.example \
  E2E_DIRECTOR_PASSWORD='…' \
  npm run test:e2e
```

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:5173` | Frontend origin under test. |
| `E2E_DIRECTOR_USER` | `director` | Username of the seeded director. |
| `E2E_DIRECTOR_PASSWORD` | `Dummar-Test@2026!` | Director password (matches the fixed seed value in `backend/app/scripts/seed_data.py`). Override on real deployments. |

## Production safety

* Created records are prefixed with `e2e-<base36-timestamp>-` and deleted in
  `afterAll`. Cleanup failures are logged but do not fail the suite.
* The seeded `director` user, roles, settings, and pre-existing records are
  never modified.
* No file uploads, no PDF generation, no email — strictly read + create +
  delete on a small, clearly-named set.
