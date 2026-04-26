import { test, expect, request as playwrightRequest, type APIRequestContext, type Page } from '@playwright/test';

/**
 * Minimal end-to-end smoke suite for the Dummar project-management frontend.
 *
 * Strategy:
 *   - Drive auth + navigation + logout through the real UI.
 *   - Create the test records (user / project / team / task) via the
 *     authenticated REST API using the same access token the SPA stores in
 *     localStorage. This keeps the suite robust against UI dialog changes
 *     and gives us a reliable cleanup path.
 *   - Tag every created record with a per-run prefix so collisions and
 *     accidental deletion of pre-existing rows are impossible.
 *   - Always run cleanup in `afterAll`, even if assertions failed.
 */

const DIRECTOR_USER = process.env.E2E_DIRECTOR_USER || 'director';
// Matches _DIRECTOR_FIXED_PASSWORD in backend/app/scripts/seed_data.py.
const DIRECTOR_PASSWORD = process.env.E2E_DIRECTOR_PASSWORD || 'Dummar-Test@2026!';

// Per-run tag — short, sortable, unique enough for parallel CI runs.
const RUN_TAG = `e2e-${Date.now().toString(36)}`;

interface CreatedIds {
  userId?: number;
  projectId?: number;
  teamId?: number;
  taskId?: number;
}
const created: CreatedIds = {};

/** Strings that, if present in a "loaded" page body, indicate a hard failure
 *  (raw FastAPI error JSON, nginx default error pages, blank SPA shells…). */
const RAW_ERROR_FRAGMENTS = [
  '{"detail"',
  'Internal Server Error',
  '502 Bad Gateway',
  '503 Service Unavailable',
  '504 Gateway Time-out',
  'Cannot GET /',
  'Not Found</title>',
];

async function login(page: Page): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/اسم المستخدم|username/i).fill(DIRECTOR_USER);
  await page.getByLabel(/كلمة المرور|password/i).fill(DIRECTOR_PASSWORD);
  await page.getByRole('button', { name: /تسجيل الدخول|sign in|log in/i }).click();
  // Successful login lands on /dashboard (or /change-password if forced).
  await page.waitForURL(/\/(dashboard|change-password)/, { timeout: 20_000 });
  if (page.url().includes('/change-password')) {
    test.skip(true, 'Director must change password before E2E can proceed; rotate it manually first.');
  }
}

async function assertPageRendered(page: Page, label: string): Promise<void> {
  // Layout header is the SPA's "I am alive" signal.
  await expect(page.locator('header').first(), `header missing on ${label}`).toBeVisible({ timeout: 15_000 });
  // <main> must exist and have at least some non-whitespace content.
  const main = page.locator('main').first();
  await expect(main, `main missing on ${label}`).toBeVisible();
  const text = (await main.innerText()).trim();
  expect(text.length, `blank main on ${label}`).toBeGreaterThan(0);

  // No raw error payloads should bleed through to the user.
  const body = await page.locator('body').innerText();
  for (const fragment of RAW_ERROR_FRAGMENTS) {
    expect(body, `raw error fragment "${fragment}" visible on ${label}`).not.toContain(fragment);
  }
}

async function getApi(page: Page): Promise<{ api: APIRequestContext; headers: Record<string, string> }> {
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token, 'no access_token in localStorage after login').toBeTruthy();
  const baseURL = new URL(page.url()).origin;
  const api = await playwrightRequest.newContext({
    baseURL,
    ignoreHTTPSErrors: true,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  });
  return { api, headers: { Authorization: `Bearer ${token}` } };
}

test.describe.configure({ mode: 'serial' });

test.describe('Dummar minimal E2E', () => {
  let page: Page;
  let api: APIRequestContext;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await login(page);
    ({ api } = await getApi(page));
  });

  test.afterAll(async () => {
    // Best-effort cleanup. Order matters: task → team/project → user.
    const safeDelete = async (path: string) => {
      try {
        const res = await api.delete(path);
        if (!res.ok() && res.status() !== 404) {
          console.warn(`cleanup ${path} → HTTP ${res.status()}`);
        }
      } catch (err) {
        console.warn(`cleanup ${path} threw`, err);
      }
    };
    if (created.taskId)    await safeDelete(`/api/tasks/${created.taskId}`);
    if (created.teamId)    await safeDelete(`/api/teams/${created.teamId}`);
    if (created.projectId) await safeDelete(`/api/projects/${created.projectId}`);
    if (created.userId)    await safeDelete(`/api/users/${created.userId}`);
    await api?.dispose();
    await page?.close();
  });

  test('1. login + dashboard renders', async () => {
    expect(page.url()).toMatch(/\/dashboard$/);
    await assertPageRendered(page, 'dashboard');
  });

  test('2. navigate to all main sections (no blank, no raw errors)', async () => {
    const sections: Array<[string, string]> = [
      ['/users',      'Users'],
      ['/projects',   'Projects'],
      ['/teams',      'Teams'],
      ['/tasks',      'Tasks'],
      ['/complaints', 'Complaints'],
      ['/contracts',  'Contracts'],
    ];
    for (const [path, label] of sections) {
      await page.goto(path);
      await assertPageRendered(page, label);
    }
  });

  test('3. create one test user via API and verify it appears on /users', async () => {
    const username = `${RUN_TAG}-user`;
    const res = await api.post('/api/users/', {
      data: {
        username,
        full_name: `E2E Test User ${RUN_TAG}`,
        role: 'engineer_supervisor',
        password: 'E2E-Test-Pass-2026!',
        must_change_password: false,
      },
    });
    expect(res.ok(), `create user failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    const body = await res.json();
    created.userId = body.id;
    await page.goto('/users');
    await assertPageRendered(page, 'Users (after create)');
    await expect(page.getByText(username, { exact: false }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('4. create one test project via API and verify it appears on /projects', async () => {
    const title = `E2E Project ${RUN_TAG}`;
    const code = `${RUN_TAG.toUpperCase().slice(0, 16)}`;
    const res = await api.post('/api/projects/', {
      data: { title, code, status: 'active' },
    });
    expect(res.ok(), `create project failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    const body = await res.json();
    created.projectId = body.id;
    await page.goto('/projects');
    await assertPageRendered(page, 'Projects (after create)');
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('5. create one test team via API and verify it appears on /teams', async () => {
    const name = `E2E Team ${RUN_TAG}`;
    const res = await api.post('/api/teams/', {
      data: { name, team_type: 'internal_team', is_active: true },
    });
    expect(res.ok(), `create team failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    const body = await res.json();
    created.teamId = body.id;
    await page.goto('/teams');
    await assertPageRendered(page, 'Teams (after create)');
    await expect(page.getByText(name, { exact: false }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('6. create one test task via API and verify it appears on /tasks', async () => {
    const title = `E2E Task ${RUN_TAG}`;
    const res = await api.post('/api/tasks/', {
      data: {
        title,
        description: 'Created by Playwright minimal E2E suite. Safe to delete.',
        source_type: 'internal',
        priority: 'medium',
        project_id: created.projectId,
        team_id: created.teamId,
      },
    });
    expect(res.ok(), `create task failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    const body = await res.json();
    created.taskId = body.id;
    await page.goto('/tasks');
    await assertPageRendered(page, 'Tasks (after create)');
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('7. logout via header button redirects to /login', async () => {
    await page.goto('/dashboard');
    await assertPageRendered(page, 'dashboard (pre-logout)');
    await page.getByRole('button', { name: /تسجيل الخروج|logout|sign out/i }).click();
    await page.waitForURL(/\/login(\?|$)/, { timeout: 15_000 });
    await expect(page.getByLabel(/اسم المستخدم|username/i)).toBeVisible();
  });

  test('8. protected route redirects to /login when unauthenticated', async ({ browser }) => {
    // Fresh context = no token, no cached_user.
    const ctx = await browser.newContext();
    const fresh = await ctx.newPage();
    await fresh.goto('/users');
    await fresh.waitForURL(/\/login(\?|$)/, { timeout: 15_000 });
    await expect(fresh.getByLabel(/اسم المستخدم|username/i)).toBeVisible();
    await ctx.close();
  });
});
