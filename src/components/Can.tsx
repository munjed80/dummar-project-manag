import type { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';

interface CanProps {
  /** Resource name (matches backend ResourceType enum value, e.g. "contract"). */
  resource: string;
  /** Action name (matches backend Action enum value, e.g. "approve"). */
  action: string;
  /** Optional fallback rendered when permission is missing. */
  fallback?: ReactNode;
  children: ReactNode;
}

/**
 * Hides children when the current user does not have the
 * (resource, action) permission according to /auth/me/permissions.
 *
 * The backend remains the source of truth — this only prevents the UI from
 * showing actions the user can't perform anyway.
 */
export function Can({ resource, action, fallback = null, children }: CanProps) {
  const { can, permissions } = useAuth();
  // While permissions are still loading, render nothing rather than flashing
  // a button that may immediately disappear.
  if (permissions === null) return null;
  if (!can(resource, action)) return <>{fallback}</>;
  return <>{children}</>;
}
