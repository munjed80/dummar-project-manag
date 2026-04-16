import type { UserRole } from '@/hooks/useAuth';
import { useAuth } from '@/hooks/useAuth';

interface RoleGuardProps {
  /** Allowed roles – user must have at least one of these */
  roles: UserRole[];
  /** Content shown when the user has the required role */
  children: React.ReactNode;
  /** Optional fallback when the user does NOT have the role */
  fallback?: React.ReactNode;
}

/**
 * Conditionally renders children based on the current user's role.
 *
 * ```tsx
 * <RoleGuard roles={['project_director']}>
 *   <AdminPanel />
 * </RoleGuard>
 * ```
 */
export function RoleGuard({ roles, children, fallback = null }: RoleGuardProps) {
  const { role, loading } = useAuth();

  // While loading, render nothing to avoid flash of wrong content
  if (loading) return null;

  if (role && roles.includes(role)) {
    return <>{children}</>;
  }

  return <>{fallback}</>;
}
