import { useMemo } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Plus, SignOut } from '@phosphor-icons/react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { NotificationBell } from '@/components/NotificationBell';
import { OfflineSyncBanner } from '@/components/OfflineSyncBanner';
import type { UserRole } from '@/hooks/useAuth';
import { DesktopNavigation, MobileNavigation } from '@/components/navigation/AppNavigation';
import { NAV_ITEMS, filterNavByRole, formatRoleLabel } from '@/components/navigation/nav-config';

interface LayoutProps {
  children: React.ReactNode;
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
  const { role, loading, user } = useAuth();

  const handleLogout = () => {
    apiService.logout();
    localStorage.removeItem('cached_user');
    navigate('/login');
  };

  const effectiveRole: UserRole | null = role ?? readCachedRole();

  const navItems = useMemo(() => filterNavByRole(NAV_ITEMS, effectiveRole), [effectiveRole]);

  const canSubmitInternalComplaint = Boolean(effectiveRole && ['project_director', 'contracts_manager', 'complaints_officer', 'area_supervisor'].includes(effectiveRole));

  if (!loading && !effectiveRole && !apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-background" dir="rtl">
      <header className="sticky top-0 z-50 border-b border-primary/70 bg-primary text-primary-foreground shadow-[0_2px_12px_rgba(15,23,42,0.18)]">
        <div className="container mx-auto px-3 md:px-4 py-2.5 md:py-3 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base md:text-lg font-semibold tracking-tight text-primary-foreground truncate">إدارة التجمع - مشروع دمر</h1>
            {effectiveRole && (
              <p className="hidden sm:block text-[11px] md:text-xs text-primary-foreground/75">{user?.full_name || 'مستخدم النظام'} • {formatRoleLabel(effectiveRole)}</p>
            )}
          </div>

          <div className="flex items-center gap-1.5 md:gap-2 shrink-0">
            {canSubmitInternalComplaint && (
              <a
                href="/complaints/new"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 rounded-xl text-xs md:text-sm border border-primary-foreground/30 bg-primary-foreground/10 hover:bg-primary-foreground/20 transition-colors"
                title="فتح نموذج تقديم شكوى داخلية في تبويب جديد"
              >
                <Plus size={15} />
                <span className="hidden md:inline">تقديم شكوى داخلية</span>
                <span className="md:hidden">شكوى داخلية</span>
              </a>
            )}
            <NotificationBell />
            <Button variant="ghost" onClick={handleLogout} className="hidden sm:inline-flex text-primary-foreground hover:bg-primary-foreground/20 px-2 md:px-3 rounded-xl">
              <SignOut size={18} />
              <span className="mr-1 text-sm">تسجيل الخروج</span>
            </Button>
            <MobileNavigation
              navItems={navItems}
              pathname={location.pathname}
              onLogout={handleLogout}
              showInternalComplaintAction={canSubmitInternalComplaint}
            />
          </div>
        </div>
        <DesktopNavigation navItems={navItems} pathname={location.pathname} />
      </header>

      <OfflineSyncBanner />

      <div className="container mx-auto px-3 md:px-4 py-4 md:py-6">
        <main className="min-w-0">{children}</main>
      </div>

      <footer className="bg-muted mt-8 md:mt-12 py-4 md:py-6">
        <div className="container mx-auto px-4 text-center text-muted-foreground text-xs md:text-sm">
          <p>© 2024 إدارة التجمع - مشروع دمر - دمشق | جميع الحقوق محفوظة</p>
        </div>
      </footer>
    </div>
  );
}
