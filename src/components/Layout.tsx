import { useMemo } from 'react';
import { Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { House, ChatCircleDots, ListChecks, FileText, SignOut, UsersThree, ChartBar, GearSix, UserCircle, Brain, FolderOpen, Plus, Buildings, Rows, MapTrifold } from '@phosphor-icons/react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { NotificationBell } from '@/components/NotificationBell';
import { OfflineSyncBanner } from '@/components/OfflineSyncBanner';
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

  const handleLogout = () => {
    apiService.logout();
    localStorage.removeItem('cached_user');
    navigate('/login');
  };

  const effectiveRole: UserRole | null = role ?? readCachedRole();

  const allNavItems: NavItem[] = useMemo(() => [
    // Primary workflow-first order (keep contract experiences grouped).
    { path: '/dashboard', icon: House, label: 'لوحة التحكم', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/citizen', icon: UserCircle, label: 'شكاواي', roles: ['citizen'] },
    { path: '/complaints', icon: ChatCircleDots, label: 'الشكاوى', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/tasks', icon: ListChecks, label: 'المهام', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/investment-contracts', icon: FileText, label: 'العقود الاستثمارية', roles: ['project_director', 'contracts_manager', 'investment_manager', 'property_manager'] },
    { path: '/contract-intelligence', icon: Brain, label: 'تحليل العقود الاستثمارية', roles: ['project_director', 'contracts_manager'] },
    { path: '/manual-contracts', icon: Rows, label: 'العقود التشغيلية', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'investment_manager', 'property_manager'] },
    { path: '/investment-properties', icon: Buildings, label: 'الأصول', roles: ['project_director', 'contracts_manager', 'property_manager', 'investment_manager'] },
    { path: '/teams', icon: UsersThree, label: 'الفرق', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/projects', icon: FolderOpen, label: 'المشاريع', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/complaints-map', icon: MapTrifold, label: 'خريطة العمليات', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/users', icon: UsersThree, label: 'المستخدمون', roles: ['project_director'] },
    { path: '/reports', icon: ChartBar, label: 'التقارير', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor'] },
    { path: '/settings', icon: GearSix, label: 'الإعدادات' },
  ], []);

  const navItems = useMemo(
    () =>
      allNavItems.filter((item) => {
        if (!item.roles || item.roles.length === 0) return true;
        return effectiveRole ? item.roles.includes(effectiveRole) : false;
      }),
    [allNavItems, effectiveRole],
  );

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  const handleHorizontalWheel = (event: React.WheelEvent<HTMLUListElement>) => {
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    event.currentTarget.scrollBy({ left: event.deltaY, behavior: 'smooth' });
    event.preventDefault();
  };

  if (!loading && !effectiveRole && !apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-background" dir="rtl">
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/95 shadow-[0_2px_16px_rgba(0,0,0,0.04)] backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="container mx-auto px-3 md:px-4 py-2 md:py-2.5 flex items-center justify-between gap-2">
          <h1 className="text-sm sm:text-base md:text-lg font-semibold tracking-tight text-foreground/90 truncate">إدارة التجمع - مشروع دمر</h1>
          <div className="flex items-center gap-1 md:gap-2 shrink-0">
            {effectiveRole && ['project_director', 'contracts_manager', 'complaints_officer', 'area_supervisor'].includes(effectiveRole) && (
              <a
                href="/complaints/new"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 rounded-xl text-xs md:text-sm border border-border/80 bg-card/70 hover:bg-accent transition-colors"
                title="فتح نموذج تقديم شكوى للمواطنين في تبويب جديد"
              >
                <Plus size={15} />
                <span className="hidden md:inline">تقديم شكوى نيابة عن مواطن</span>
                <span className="md:hidden">شكوى مواطن</span>
              </a>
            )}
            <NotificationBell />
            <Button variant="ghost" onClick={handleLogout} className="text-foreground hover:bg-accent/80 px-2 md:px-3 rounded-xl">
              <SignOut size={18} />
              <span className="hidden sm:inline mr-1 text-sm">تسجيل الخروج</span>
            </Button>
          </div>
        </div>

        <nav className="border-t border-border/60 bg-muted/20">
          <div className="container mx-auto px-2 md:px-4">
            <ul
              className="flex items-center gap-2 py-2 overflow-x-auto overflow-y-hidden whitespace-nowrap scroll-smooth touch-pan-x overscroll-x-contain [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
              onWheel={handleHorizontalWheel}
            >
              {navItems.map(({ path, icon: Icon, label }) => (
                <li key={path} className="shrink-0">
                  <Link
                    to={path}
                    className={`group inline-flex items-center gap-1.5 md:gap-2 rounded-xl px-3 md:px-3.5 py-1.5 md:py-2 text-xs md:text-sm font-medium transition-all duration-200 border ${
                      isActive(path)
                        ? 'bg-primary/10 text-primary border-primary/30 shadow-[0_1px_6px_rgba(0,0,0,0.06)]'
                        : 'bg-background/60 text-muted-foreground border-transparent hover:border-border/70 hover:bg-background hover:text-foreground'
                    }`}
                  >
                    <Icon size={15} weight={isActive(path) ? 'fill' : 'regular'} className={isActive(path) ? 'opacity-100' : 'opacity-80'} />
                    <span>{label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </nav>
      </header>

      <OfflineSyncBanner />

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
