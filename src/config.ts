/**
 * Application configuration loaded from environment variables.
 *
 * Vite exposes env vars prefixed with VITE_ on `import.meta.env`.
 *
 * Defaults are deliberately *production-safe*:
 *   - API_BASE_URL defaults to `/api` (same-origin; nginx proxies /api/* to the backend).
 *   - FILES_BASE_URL defaults to `''`   (same-origin; nginx serves /uploads/* directly
 *     or proxies sensitive categories to the backend).
 *
 * There is intentionally NO `http://localhost:8000` fallback here — that value
 * used to leak into production bundles when the build was run without the env
 * var set, which broke login/auth on the VPS after every rebuild.
 *
 * For local development against a directly-exposed backend, either:
 *   a) rely on the Vite dev-server proxy (vite.config.ts already proxies
 *      /api and /uploads to http://localhost:8000), which is the recommended
 *      path and keeps these defaults working, OR
 *   b) set VITE_API_BASE_URL / VITE_FILES_BASE_URL in a local .env file.
 */

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

const rawApiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api';
const API_BASE_URL = trimTrailingSlash(rawApiBase) || '/api';

// The public files base URL is deliberately *separate* from the API base URL.
// API lives under /api (rewritten by nginx to the backend), while file URLs
// returned by the backend are root-relative paths like "/uploads/foo/bar.pdf".
// Concatenating the API base onto those would produce "/api/uploads/..." which
// nginx does NOT route. If VITE_FILES_BASE_URL is unset we fall back to:
//   - the API base URL when it is an absolute URL (dev against a remote backend),
//   - the empty string otherwise (same-origin: nginx serves /uploads/* directly).
function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

const rawFilesBase = import.meta.env.VITE_FILES_BASE_URL as string | undefined;
const FILES_BASE_URL = rawFilesBase !== undefined
  ? trimTrailingSlash(rawFilesBase)
  : (isAbsoluteUrl(API_BASE_URL) ? API_BASE_URL : '');

export const config = {
  /** Base URL of the backend API (no trailing slash). Production default: `/api`. */
  API_BASE_URL,
  /**
   * Base URL for publicly-served files returned by the API as root-relative
   * paths (e.g. `/uploads/complaints/abc.jpg`). Production default: `''`
   * (same-origin). NEVER concatenate API_BASE_URL with these paths.
   */
  FILES_BASE_URL,
} as const;
