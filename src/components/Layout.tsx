import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { House, ChatCircleDots, ListChecks, FileText, MapPin, SignOut, UsersThree, ChartBar, GearSix, MapTrifold, UserCircle, List, X, Brain, Globe, FolderOpen } from '@phosphor-icons/react';
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
  /** If set, only these roles see this item. Empty = everyone. */
  roles?: UserRole[];
}

export function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { role } = useAuth();
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

  const allNavItems: NavItem[] = [
    { path: '/dashboard', icon: House, label: 'لوحة التحكم', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/citizen', icon: UserCircle, label: 'شكاواي', roles: ['citizen'] },
    { path: '/complaints', icon: ChatCircleDots, label: 'الشكاوى', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/complaints-map', icon: MapTrifold, label: 'خريطة الشكاوى' },
    { path: '/tasks', icon: ListChecks, label: 'المهام', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/contracts', icon: FileText, label: 'العقود', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/projects', icon: FolderOpen, label: 'المشاريع', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/teams', icon: UsersThree, label: 'الفرق التنفيذية', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/contract-intelligence', icon: Brain, label: 'ذكاء العقود', roles: ['project_director', 'contracts_manager'] },
    { path: '/locations', icon: MapPin, label: 'المواقع', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/locations/geo-dashboard', icon: Globe, label: 'لوحة جغرافية', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor'] },
    { path: '/users', icon: UsersThree, label: 'المستخدمون', roles: ['project_director'] },
    { path: '/reports', icon: ChartBar, label: 'التقارير', roles: ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user'] },
    { path: '/settings', icon: GearSix, label: 'الإعدادات' },
  ];

  const navItems = allNavItems.filter((item) => {
    if (!item.roles || item.roles.length === 0) return true;
    return role ? item.roles.includes(role) : false;
  });

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
            <h1 className="text-lg md:text-2xl font-bold truncate">منصة إدارة مشروع دمّر</h1>
          </div>
          <div className="flex items-center gap-1 md:gap-2">
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
          <p>© 2024 مشروع دمر - دمشق | جميع الحقوق محفوظة</p>
        </div>
      </footer>
    </div>
  );
}
