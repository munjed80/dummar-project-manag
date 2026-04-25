import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { apiService, ApiError } from '@/services/api';
import type { User, MePermissionsResponse } from '@/services/api';

// ── Role definitions matching backend UserRole enum ──
export type UserRole =
  | 'project_director'
  | 'contracts_manager'
  | 'engineer_supervisor'
  | 'complaints_officer'
  | 'area_supervisor'
  | 'field_team'
  | 'contractor_user'
  | 'citizen';

// ── Permission helpers ──
const COMPLAINT_MANAGERS: UserRole[] = [
  'project_director',
  'complaints_officer',
  'engineer_supervisor',
  'area_supervisor',
];

const TASK_MANAGERS: UserRole[] = [
  'project_director',
  'engineer_supervisor',
  'area_supervisor',
  'complaints_officer',
];

const CONTRACT_MANAGERS: UserRole[] = [
  'project_director',
  'contracts_manager',
];

const USER_MANAGERS: UserRole[] = [
  'project_director',
];

export interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  /** Convenience getters */
  role: UserRole | null;
  isAuthenticated: boolean;
  /** Permission checks */
  canManageComplaints: boolean;
  canManageTasks: boolean;
  canManageContracts: boolean;
  canCreateContracts: boolean;
  canManageUsers: boolean;
  canViewReports: boolean;
  /** Generic role check */
  hasRole: (...roles: UserRole[]) => boolean;
  /** Fine-grained permission check (resource + action). */
  can: (resource: string, action: string) => boolean;
  /** Permission metadata fetched from /auth/me/permissions */
  permissions: MePermissionsResponse | null;
  /** Refresh user from API */
  refresh: () => Promise<void>;
}

const CACHE_KEY = 'cached_user';

function getCachedUser(): User | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setCachedUser(user: User | null) {
  if (user) {
    localStorage.setItem(CACHE_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(CACHE_KEY);
  }
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * App-level auth provider.
 *
 * One source of truth for the authenticated user across every page. Each
 * page used to mount its own <Layout/>, which called useAuth() independently
 * and re-fetched /auth/me on every navigation. While that fetch was in
 * flight the role briefly became null and the navigation collapsed to only
 * role-less items (Settings + Complaints Map). Hoisting the state to a
 * single provider — and seeding it synchronously from localStorage — keeps
 * the navigation stable across route changes and auth refreshes.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getCachedUser);
  // If we have a cached user we are NOT loading from the user's perspective —
  // the navigation can render immediately. The background refresh runs but
  // does not mark the UI as loading, which avoids a navigation flash.
  const [loading, setLoading] = useState(!getCachedUser() && apiService.isAuthenticated());
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<MePermissionsResponse | null>(null);

  // Track whether a refresh is currently in flight so we don't kick off a
  // duplicate refresh when multiple consumers mount simultaneously.
  const refreshing = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    if (!apiService.isAuthenticated()) {
      setUser(null);
      setCachedUser(null);
      setPermissions(null);
      setLoading(false);
      return;
    }
    refreshing.current = true;
    // Only flip the loading flag when we have NO cached user — otherwise the
    // existing user (and therefore navigation) stays on screen while we
    // silently re-validate in the background.
    const hadCachedUser = !!getCachedUser();
    if (!hadCachedUser) setLoading(true);
    try {
      const u = await apiService.getCurrentUser();
      setUser(u);
      setCachedUser(u);
      setError(null);
      try {
        const p = await apiService.getCurrentUserPermissions();
        setPermissions(p);
      } catch {
        setPermissions(null);
      }
    } catch (err) {
      // 401 => the token is invalid/expired. Clear everything so the next
      // route guard redirects to /login cleanly. Other errors (network blips,
      // 5xx) MUST NOT log the user out — keep the cached user so the UI
      // stays responsive and the user can keep working from cached data.
      if (err instanceof ApiError && err.status === 401) {
        apiService.logout();
        setUser(null);
        setCachedUser(null);
        setPermissions(null);
        setError('Session expired');
      } else {
        setError('Failed to fetch user');
      }
    } finally {
      refreshing.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // We intentionally only run this on mount; subsequent refreshes are
    // triggered explicitly via the returned `refresh` callback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const role = (user?.role as UserRole) ?? null;

  const hasRole = useCallback(
    (...roles: UserRole[]) => (role ? roles.includes(role) : false),
    [role],
  );

  const can = useCallback(
    (resource: string, action: string) => {
      if (!permissions) return false;
      return permissions.permissions.some(
        (p) => p.resource === resource && p.action === action,
      );
    },
    [permissions],
  );

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      error,
      role,
      isAuthenticated: !!user && apiService.isAuthenticated(),
      canManageComplaints: role ? COMPLAINT_MANAGERS.includes(role) : false,
      canManageTasks: role ? TASK_MANAGERS.includes(role) : false,
      canManageContracts: role ? CONTRACT_MANAGERS.includes(role) : false,
      canCreateContracts: role ? CONTRACT_MANAGERS.includes(role) : false,
      canManageUsers: role ? USER_MANAGERS.includes(role) : false,
      canViewReports: role !== 'citizen',
      hasRole,
      can,
      permissions,
      refresh,
    }),
    [user, loading, error, role, permissions, hasRole, can, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (ctx) return ctx;
  // Defensive fallback: if useAuth() is ever called outside the provider
  // (e.g. an isolated test render), return a sensible read-only snapshot
  // derived from localStorage instead of crashing the page.
  const cached = getCachedUser();
  const role = (cached?.role as UserRole) ?? null;
  return {
    user: cached,
    loading: false,
    error: null,
    role,
    isAuthenticated: !!cached && apiService.isAuthenticated(),
    canManageComplaints: role ? COMPLAINT_MANAGERS.includes(role) : false,
    canManageTasks: role ? TASK_MANAGERS.includes(role) : false,
    canManageContracts: role ? CONTRACT_MANAGERS.includes(role) : false,
    canCreateContracts: role ? CONTRACT_MANAGERS.includes(role) : false,
    canManageUsers: role ? USER_MANAGERS.includes(role) : false,
    canViewReports: role !== 'citizen',
    hasRole: (...roles: UserRole[]) => (role ? roles.includes(role) : false),
    can: () => false,
    permissions: null,
    refresh: async () => {},
  };
}
