import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { House, ChatCircleDots, ListChecks, FileText, SignOut, UsersThree, ChartBar, GearSix, MapTrifold, UserCircle, List, X, Brain, FolderOpen, Plus, Buildings } from '@phosphor-icons/react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { NotificationBell } from '@/components/NotificationBell';
import type { UserRole } from '@/hooks/useAuth';

interface LayoutProps {
  children: React.ReactNode;
}

interface NavItem {
  path: string;
  icon: React.ElementType;
  label: string;
  /** If set, only these roles see this item. Empty/undefined = everyone. */
  roles?: UserRole[];
}

// Read the cached role straight from localStorage as a synchronous fallback
// for the first render of a freshly-mounted Layout. Even though the
// AuthProvider seeds its initial state from the same cache, this fallback
// guarantees the navigation NEVER renders without a role on a hard refresh
// where the cached_user JSON parse and the React render race.
function readCachedRole(): UserRole | null {
  try {
    const raw = localStorage.getItem('cached_user');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { role?: string };
    return (parsed?.role as UserRole) ?? null;
  } catch {
    return null;
  }
}

export function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { role, loading } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    apiService.logout();
    localStorage.removeItem('cached_user');
    navigate('/login');
  };

  // Effective role: prefer the live auth role, but fall back to the cached
  // role from localStorage whenever the live role is momentarily null. This
  // is what stops the nav from collapsing during route changes / /auth/me
  // refreshes — the cached value remains valid until an explicit 401 clears
  // the cache (handled centrally in AuthProvider).
  const effectiveRole: UserRole | null = role ?? readCachedRole();

  const allNavItems: NavItem[] = useMemo(() => [
    { path: '/dashboard', icon: House, label: 'لوحة التحكم', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/citizen', icon: UserCircle, label: 'شكاواي', roles: ['citizen'] },
    { path: '/complaints', icon: ChatCircleDots, label: 'الشكاوى', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/tasks', icon: ListChecks, label: 'المهام', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/contracts', icon: FileText, label: 'العقود', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/projects', icon: FolderOpen, label: 'المشاريع', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/teams', icon: UsersThree, label: 'الفرق التنفيذية', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/contract-intelligence', icon: Brain, label: 'ذكاء العقود', roles: ['project_director', 'contracts_manager'] },
    // Single consolidated geographic entry. The Locations list and Geo
    // Dashboard pages are still routable directly, and surfaced as internal
    // tabs from inside the Complaints Map page.
    { path: '/complaints-map', icon: MapTrifold, label: 'خريطة الشكاوى', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/investment-properties', icon: Buildings, label: 'الأملاك الاستثمارية', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'property_manager', 'investment_manager'] },
    { path: '/users', icon: UsersThree, label: 'المستخدمون', roles: ['project_director'] },
    { path: '/reports', icon: ChartBar, label: 'التقارير', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/settings', icon: GearSix, label: 'الإعدادات' },
  ], []);

  // Filter nav items by the EFFECTIVE role. When effectiveRole is null we
  // intentionally show only the always-visible items (Settings) — but in
  // practice this branch is only reached on the very first mount before any
  // auth state exists, which is also the only situation where the user has
  // no cached identity to filter against.
  const navItems = useMemo(
    () =>
      allNavItems.filter((item) => {
        if (!item.roles || item.roles.length === 0) return true;
        return effectiveRole ? item.roles.includes(effectiveRole) : false;
      }),
    [allNavItems, effectiveRole],
  );

  // If the user is truly unauthenticated (no token AND no cached identity)
  // on a protected page, send them to /login instead of rendering a partial
  // menu. We only redirect once auth has finished loading so that an
  // in-flight refresh doesn't bounce a legitimately-authenticated user out.
  // Placed after all hook calls to keep hook order stable across renders.
  if (!loading && !effectiveRole && !apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-background" dir="rtl">
      <header className="sticky top-0 z-50 bg-primary text-primary-foreground shadow-md">
        <div className="container mx-auto px-4 py-3 md:py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Mobile menu toggle */}
            <button
              className="md:hidden p-1.5 rounded-md hover:bg-primary/80 transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="القائمة"
            >
              {mobileMenuOpen ? <X size={24} /> : <List size={24} />}
            </button>
            <h1 className="text-lg md:text-2xl font-bold truncate">إدارة التجمع - مشروع دمر</h1>
          </div>
          <div className="flex items-center gap-1 md:gap-2">
            {/* Intake shortcut for staff who help walk-in / phone citizens.
                Opens the public submit form in a new tab so the staff session
                stays intact. Visible only to roles that actually do intake. */}
            {effectiveRole && ['project_director', 'contracts_manager', 'complaints_officer', 'area_supervisor'].includes(effectiveRole) && (
              <a
                href="/complaints/new"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:inline-flex items-center gap-1 px-2 md:px-3 py-1.5 rounded-md text-sm bg-primary-foreground/15 hover:bg-primary-foreground/25 transition-colors"
                title="فتح نموذج تقديم شكوى للمواطنين في تبويب جديد"
              >
                <Plus size={16} />
                <span className="hidden md:inline">تقديم شكوى نيابة عن مواطن</span>
                <span className="md:hidden">شكوى مواطن</span>
              </a>
            )}
            <NotificationBell />
            <Button variant="ghost" onClick={handleLogout} className="text-primary-foreground hover:bg-primary/90 px-2 md:px-4">
              <SignOut size={20} />
              <span className="hidden sm:inline mr-1">تسجيل الخروج</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Desktop nav — horizontal bar */}
      <nav className="hidden md:block bg-secondary text-secondary-foreground shadow-sm">
        <div className="container mx-auto px-4">
          <ul className="flex gap-1 overflow-x-auto">
            {navItems.map(({ path, icon: Icon, label }) => (
              <li key={path}>
                <Link
                  to={path}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold transition-colors whitespace-nowrap ${
                    location.pathname === path || location.pathname.startsWith(path + '/')
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-primary/10'
                  }`}
                >
                  <Icon size={20} />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* Mobile nav — slide-down panel */}
      {mobileMenuOpen && (
        <nav className="md:hidden bg-secondary text-secondary-foreground shadow-lg border-b border-border">
          <ul className="flex flex-col">
            {navItems.map(({ path, icon: Icon, label }) => (
              <li key={path}>
                <Link
                  to={path}
                  className={`flex items-center gap-3 px-4 py-3 text-sm font-semibold transition-colors border-b border-border/50 ${
                    location.pathname === path || location.pathname.startsWith(path + '/')
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-primary/10'
                  }`}
                >
                  <Icon size={20} />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      <main className="container mx-auto px-3 md:px-4 py-4 md:py-6">
        {children}
      </main>

      <footer className="bg-muted mt-8 md:mt-12 py-4 md:py-6">
        <div className="container mx-auto px-4 text-center text-muted-foreground text-xs md:text-sm">
          <p>© 2024 إدارة التجمع - مشروع دمر - دمشق | جميع الحقوق محفوظة</p>
        </div>
      </footer>
    </div>
  );
}
