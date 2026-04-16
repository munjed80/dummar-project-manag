import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { House, ChatCircleDots, ListChecks, FileText, MapPin, UsersThree, ChartBar, Gear, SignOut } from '@phosphor-icons/react';
import { apiService } from '@/services/api';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    apiService.logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', icon: House, label: 'لوحة التحكم' },
    { path: '/complaints', icon: ChatCircleDots, label: 'الشكاوى' },
    { path: '/tasks', icon: ListChecks, label: 'المهام' },
    { path: '/contracts', icon: FileText, label: 'العقود' },
    { path: '/locations', icon: MapPin, label: 'المواقع' },
    { path: '/users', icon: UsersThree, label: 'المستخدمون' },
    { path: '/reports', icon: ChartBar, label: 'التقارير' },
    { path: '/settings', icon: Gear, label: 'الإعدادات' },
  ];

  return (
    <div className="min-h-screen bg-background" dir="rtl">
      <header className="sticky top-0 z-50 bg-primary text-primary-foreground shadow-md">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl md:text-2xl font-bold">منصة إدارة مشروع دمر</h1>
          <Button variant="ghost" onClick={handleLogout} className="text-primary-foreground hover:bg-primary/90">
            <SignOut className="ml-2" />
            تسجيل الخروج
          </Button>
        </div>
      </header>

      <nav className="bg-secondary text-secondary-foreground shadow-sm">
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

      <main className="container mx-auto px-4 py-6">
        {children}
      </main>

      <footer className="bg-muted mt-12 py-6">
        <div className="container mx-auto px-4 text-center text-muted-foreground text-sm">
          <p>© 2024 مشروع دمر - دمشق | جميع الحقوق محفوظة</p>
        </div>
      </footer>
    </div>
  );
}
