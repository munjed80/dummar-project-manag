import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { List, Plus, SignOut } from '@phosphor-icons/react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { NotificationBell } from '@/components/NotificationBell';
import { OfflineSyncBanner } from '@/components/OfflineSyncBanner';
import type { UserRole } from '@/hooks/useAuth';
import { SidebarNav } from '@/components/navigation/Sidebar';
import { SmartAssistantButton } from '@/components/navigation/SmartAssistantButton';
import {
  NAV_ENTRIES,
  filterEntriesByRole,
  formatRoleLabel,
} from '@/components/navigation/nav-config';

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

/** Roles that have access to the internal-messages module. */
const MESSAGES_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user',
  'property_manager', 'investment_manager',
];

/**
 * Lightweight unread-message counter used by the sidebar badge for
 * "الرسائل الداخلية".  Polls every 60 seconds and silently degrades on
 * error.  Citizens and unauthenticated visitors get 0.
 */
function useUnreadMessagesCount(role: UserRole | null): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!role || !MESSAGES_ROLES.includes(role)) {
      setCount(0);
      return;
    }
    let cancelled = false;
    const fetchUnread = async () => {
      try {
        const threads = await apiService.getMessageThreads({ limit: 50 });
        if (cancelled) return;
        const total = threads.reduce(
          (acc, t) => acc + (typeof t.unread_count === 'number' ? t.unread_count : 0),
          0,
        );
        setCount(total);
      } catch {
        // silent fail — badge stays at last known value
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [role]);
  return count;
}

export function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { role, loading, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    apiService.logout();
    localStorage.removeItem('cached_user');
    navigate('/login');
  };

  const effectiveRole: UserRole | null = role ?? readCachedRole();

  const navEntries = useMemo(
    () => filterEntriesByRole(NAV_ENTRIES, effectiveRole),
    [effectiveRole],
  );

  const messagesUnread = useUnreadMessagesCount(effectiveRole);

  const canSubmitInternalComplaint = Boolean(
    effectiveRole &&
      ['project_director', 'contracts_manager', 'complaints_officer', 'area_supervisor'].includes(
        effectiveRole,
      ),
  );

  // The smart-assistant icon is only meaningful for internal staff
  // (the /internal-bot route requires an internal role).
  const canUseSmartAssistant = Boolean(
    effectiveRole && effectiveRole !== 'citizen',
  );

  if (!loading && !effectiveRole && !apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-background" dir="rtl">
      <header className="sticky top-0 z-40 border-b border-primary/70 bg-primary text-primary-foreground shadow-[0_2px_12px_rgba(15,23,42,0.18)]">
        <div className="mx-auto flex w-full items-center justify-between gap-2 px-3 py-2.5 md:px-4 md:py-3">
          <div className="flex min-w-0 items-center gap-2">
            {/* Mobile drawer trigger */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  className="rounded-xl px-2.5 text-primary-foreground hover:bg-primary-foreground/15 lg:hidden"
                  aria-label="فتح القائمة الرئيسية"
                >
                  <List size={22} />
                </Button>
              </SheetTrigger>
              <SheetContent
                side="right"
                className="w-full max-w-none border-0 bg-slate-950 p-0 text-slate-100 sm:max-w-sm"
                dir="rtl"
              >
                <SheetHeader className="border-b border-white/10 px-5 py-4">
                  <SheetTitle className="text-right text-base text-white">
                    إدارة التجمع - مشروع دمر
                  </SheetTitle>
                </SheetHeader>
                <div className="flex h-[calc(100vh-64px)] flex-col">
                  <SidebarNav
                    entries={navEntries}
                    pathname={location.pathname}
                    badges={{ messages: messagesUnread }}
                    onNavigate={() => setMobileOpen(false)}
                    compact
                  />
                  <div className="border-t border-white/10 p-4">
                    <Button
                      onClick={handleLogout}
                      className="w-full justify-center rounded-xl bg-white/10 text-white hover:bg-white/20"
                      variant="ghost"
                    >
                      <SignOut size={18} />
                      <span className="mr-1">تسجيل الخروج</span>
                    </Button>
                  </div>
                </div>
              </SheetContent>
            </Sheet>

            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold tracking-tight text-primary-foreground sm:text-base md:text-lg">
                إدارة التجمع - مشروع دمر
              </h1>
              {effectiveRole && (
                <p className="hidden text-[11px] text-primary-foreground/75 sm:block md:text-xs">
                  {user?.full_name || 'مستخدم النظام'} • {formatRoleLabel(effectiveRole)}
                </p>
              )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1.5 md:gap-2">
            {canSubmitInternalComplaint && (
              <a
                href="/complaints/new"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden items-center gap-1.5 rounded-xl border border-primary-foreground/30 bg-primary-foreground/10 px-2.5 py-1.5 text-xs transition-colors hover:bg-primary-foreground/20 sm:inline-flex md:px-3 md:text-sm"
                title="فتح نموذج تقديم شكوى داخلية في تبويب جديد"
              >
                <Plus size={15} />
                <span className="hidden md:inline">تقديم شكوى داخلية</span>
                <span className="md:hidden">شكوى داخلية</span>
              </a>
            )}
            <NotificationBell />
            {canUseSmartAssistant && <SmartAssistantButton />}
            <Button
              variant="ghost"
              onClick={handleLogout}
              className="hidden rounded-xl px-2 text-primary-foreground hover:bg-primary-foreground/20 sm:inline-flex md:px-3"
            >
              <SignOut size={18} />
              <span className="mr-1 text-sm">تسجيل الخروج</span>
            </Button>
          </div>
        </div>
      </header>

      <OfflineSyncBanner />

      <div className="mx-auto flex w-full">
        {/* Desktop sidebar (RTL: visually on the right edge of the viewport) */}
        {effectiveRole && navEntries.length > 0 && (
          <aside
            className="sticky top-[var(--app-header-h,57px)] hidden h-[calc(100vh-57px)] w-64 shrink-0 border-l border-white/10 bg-slate-950 text-slate-100 lg:block"
          >
            <SidebarNav
              entries={navEntries}
              pathname={location.pathname}
              badges={{ messages: messagesUnread }}
            />
          </aside>
        )}

        <main className="min-w-0 flex-1">
          <div className="container mx-auto px-3 py-4 md:px-4 md:py-6">{children}</div>
          <footer className="mt-8 bg-muted py-4 md:mt-12 md:py-6">
            <div className="container mx-auto px-4 text-center text-xs text-muted-foreground md:text-sm">
              <p>© 2024 إدارة التجمع - مشروع دمر - دمشق | جميع الحقوق محفوظة</p>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}
