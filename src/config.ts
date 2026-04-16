/**
 * Application configuration loaded from environment variables.
 *
 * Vite exposes env vars prefixed with VITE_ on `import.meta.env`.
 * Fallback to sensible defaults for local development.
 */
export const config = {
  /** Base URL of the backend API (no trailing slash). */
  API_BASE_URL: (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000',
} as const;
