import { useState, useEffect, useCallback } from 'react';
import { apiService } from '@/services/api';
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

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(getCachedUser);
  const [loading, setLoading] = useState(!getCachedUser());
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<MePermissionsResponse | null>(null);

  const refresh = useCallback(async () => {
    if (!apiService.isAuthenticated()) {
      setUser(null);
      setCachedUser(null);
      setPermissions(null);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
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
    } catch {
      setUser(null);
      setCachedUser(null);
      setPermissions(null);
      setError('Failed to fetch user');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

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

  return {
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
  };
}
