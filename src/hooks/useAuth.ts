// Backwards-compatible re-export. All auth state now lives in a single
// AuthProvider mounted at the App root (see src/contexts/AuthContext.tsx),
// which prevents per-page Layout components from re-fetching /auth/me on
// every navigation and collapsing the role-filtered nav while in flight.
export { useAuthContext as useAuth, AuthProvider } from '@/contexts/AuthContext';
export type { AuthState, UserRole } from '@/contexts/AuthContext';
