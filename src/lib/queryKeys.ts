/**
 * Centralised TanStack Query keys.
 *
 * Stable, structured keys are critical for two reasons:
 *  1. **Deduplication** — multiple pages requesting the same resource
 *     (e.g. selector projects/teams/areas) share a single in-flight
 *     request and a single cached payload.
 *  2. **Targeted invalidation** — mutations can invalidate a precise
 *     subtree (`['complaints']`) without globally clearing the cache.
 *
 * Keep these helpers thin; do not embed pagination defaults so callers
 * always pass the actual params used in the request.
 */
export const queryKeys = {
  dashboard: {
    stats: () => ['dashboard', 'stats'] as const,
    activity: () => ['dashboard', 'activity'] as const,
  },
  complaints: {
    list: (params: Record<string, unknown>) => ['complaints', 'list', params] as const,
    citizen: (params: Record<string, unknown>) => ['complaints', 'citizen', params] as const,
  },
  tasks: {
    list: (params: Record<string, unknown>) => ['tasks', 'list', params] as const,
  },
  teams: {
    list: (params: Record<string, unknown>) => ['teams', 'list', params] as const,
    active: () => ['teams', 'active'] as const,
  },
  projects: {
    selector: () => ['projects', 'selector'] as const,
  },
  areas: {
    all: () => ['areas', 'all'] as const,
  },
  investmentContracts: {
    list: (params: Record<string, unknown>) => ['investment-contracts', 'list', params] as const,
  },
  investmentProperties: {
    selector: () => ['investment-properties', 'selector'] as const,
  },
  contractIntelligence: {
    dashboard: () => ['contract-intelligence', 'dashboard'] as const,
    queue: (params: Record<string, unknown>) => ['contract-intelligence', 'queue', params] as const,
  },
  internalMessages: {
    threads: () => ['internal-messages', 'threads'] as const,
    thread: (id: number) => ['internal-messages', 'thread', id] as const,
  },
  users: {
    selector: () => ['users', 'selector'] as const,
  },
} as const;
