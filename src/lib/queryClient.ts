import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/services/api';

/**
 * Centralised TanStack Query client configuration for the Dummar app.
 *
 * Defaults are tuned for an internal operations dashboard:
 *  - `staleTime: 60s` — cached data is shown instantly after navigation;
 *    a background refresh refills it without flashing skeletons.
 *  - `gcTime: 10min`  — pages reused within a working session keep their
 *    last-known-good payload for fast re-mounts.
 *  - Smart `retry`     — only safe GET 502/503/504 / network / timeout
 *    errors are retried, with short fixed backoff. 4xx never retries.
 *  - `refetchOnWindowFocus: false` — keeps RTL operator UI calm; users
 *    can pull-to-refresh via the page-level retry buttons.
 */
/**
 * QueryClient retry policy.
 *
 * `fetchWithRetry` in `src/services/api.ts` ALREADY retries safe GET
 * failures for 502/503/504 / network / timeout with short backoff. To
 * avoid multiplicative retries (and very long perceived wait times when
 * the backend is wedged) we keep the query-level retry minimal: a single
 * extra attempt for definitely-retryable errors, never for client errors.
 */
function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= 1) return false;
  if (error instanceof ApiError) {
    // Definitive client errors should never be retried automatically.
    if ([401, 403, 404, 422, 400, 409].includes(error.status)) return false;
    return error.retryable;
  }
  // Non-ApiError (network failure raised by fetch itself) — retry once.
  return true;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 10 * 60_000,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
        retry: shouldRetryQuery,
        retryDelay: (attempt) => (attempt === 0 ? 500 : 1500),
      },
      mutations: {
        // Mutations (POST/PUT/PATCH/DELETE) must never auto-retry — they
        // are not idempotent and could double-create resources.
        retry: false,
      },
    },
  });
}
