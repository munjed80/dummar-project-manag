import { defineConfig, devices } from '@playwright/test';

/**
 * Minimal Playwright config for the Dummar project-management frontend.
 *
 * Target a *live* deployment by setting `E2E_BASE_URL` (e.g.
 * `https://dummar.example.com`). Defaults to `http://localhost:5173` for local
 * `npm run dev` use. The suite expects the director seed account and reads
 * the password from `E2E_DIRECTOR_PASSWORD` (falls back to the documented
 * fixed seed password from `backend/app/scripts/seed_data.py`).
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
    locale: 'ar',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
