import { Link } from 'react-router-dom';
import { List, Plus, SignOut } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import { NotificationBell } from '@/components/NotificationBell';
import type { UserRole } from '@/hooks/useAuth';
import { DESKTOP_GROUP_LABELS, MOBILE_GROUP_LABELS, type NavItem, formatRoleLabel } from '@/components/navigation/nav-config';

interface AppNavigationProps {
  navItems: NavItem[];
  pathname: string;
  userName?: string;
  role: UserRole | null;
  onLogout: () => void;
  showInternalComplaintAction: boolean;
}

function isActive(pathname: string, path: string) {
  return pathname === path || pathname.startsWith(`${path}/`);
}

const DESKTOP_GROUP_ORDER: NavItem['section'][] = ['home', 'work', 'contracts', 'assets', 'admin'];
const MOBILE_GROUP_ORDER: NavItem['mobileSection'][] = ['home', 'work', 'contracts', 'assets', 'admin'];

export function AppNavigation({ navItems, pathname, userName, role, onLogout, showInternalComplaintAction }: AppNavigationProps) {
  const groupedDesktop = DESKTOP_GROUP_ORDER.map((group) => ({
    group,
    label: DESKTOP_GROUP_LABELS[group],
    items: navItems.filter((item) => item.section === group),
  })).filter((group) => group.items.length > 0);

  const groupedMobile = MOBILE_GROUP_ORDER.map((group) => ({
    group,
    label: MOBILE_GROUP_LABELS[group],
    items: navItems.filter((item) => item.mobileSection === group),
  })).filter((group) => group.items.length > 0);

  return (
    <>
      <nav className="hidden lg:block border-t border-primary-foreground/20 bg-primary/90">
        <div className="container mx-auto px-4 py-3">
          <div className="flex flex-wrap items-start gap-3">
            {groupedDesktop.map((group) => (
              <section key={group.group} className="min-w-[220px] rounded-2xl border border-primary-foreground/20 bg-primary-foreground/[0.07] p-3 backdrop-blur-sm shadow-[0_6px_22px_rgba(15,23,42,0.12)]">
                <h3 className="px-1 pb-2 text-[11px] font-semibold tracking-wide text-primary-foreground/70">{group.label}</h3>
                <ul className="flex flex-wrap gap-2">
                  {group.items.map(({ path, icon: Icon, label }) => {
                    const active = isActive(pathname, path);
                    return (
                      <li key={path}>
                        <Link
                          to={path}
                          className={cn(
                            'inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200 border shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/65',
                            active
                              ? 'border-white/35 bg-white/22 text-white shadow-[0_8px_20px_rgba(15,23,42,0.24)]'
                              : 'border-white/10 bg-white/[0.03] text-primary-foreground/95 hover:border-white/25 hover:bg-white/[0.11] hover:text-white',
                          )}
                        >
                          <Icon size={18} weight={active ? 'fill' : 'regular'} />
                          <span>{label}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        </div>
      </nav>

      <div className="lg:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              className="text-primary-foreground hover:bg-primary-foreground/15 rounded-xl px-2.5"
              aria-label="فتح القائمة الرئيسية"
            >
              <List size={22} />
            </Button>
          </SheetTrigger>
          <SheetContent
            side="right"
            className="w-full max-w-none sm:max-w-md border-0 bg-slate-950/96 text-slate-100 p-0"
            dir="rtl"
          >
            <SheetHeader className="border-b border-white/10 px-6 py-5">
              <SheetTitle className="text-right text-lg text-white">إدارة التجمع - مشروع دمر</SheetTitle>
              <div className="pt-1 text-sm text-slate-300">
                <p className="font-medium text-slate-100">{userName || 'مستخدم النظام'}</p>
                <p>{formatRoleLabel(role)}</p>
              </div>
            </SheetHeader>

            <div className="border-b border-white/10 px-5 py-4">
              <div className="grid grid-cols-1 gap-2">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-100">
                  <span>مركز الإشعارات</span>
                  <NotificationBell />
                </div>
                {showInternalComplaintAction && (
                  <a
                    href="/complaints/new"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-100 hover:bg-white/[0.09] transition-colors"
                  >
                    <Plus size={18} />
                    <span>تقديم شكوى داخلية</span>
                  </a>
                )}
              </div>
            </div>

            <div className="px-5 pb-8 pt-4 overflow-y-auto">
              {groupedMobile.map((group) => (
                <section key={group.group} className="mb-5">
                  <h3 className="px-3 pb-2 text-xs font-semibold text-slate-400">{group.label}</h3>
                  <ul className="space-y-1.5">
                    {group.items.map(({ path, icon: Icon, label }) => {
                      const active = isActive(pathname, path);
                      return (
                        <li key={`drawer-${path}`}>
                          <SheetClose asChild>
                            <Link
                              to={path}
                              className={cn(
                                'flex items-center gap-3 rounded-2xl px-4 py-3 text-base transition-all duration-200 border shadow-sm',
                                active
                                  ? 'bg-blue-500/20 border-blue-300/35 text-white shadow-[0_8px_24px_rgba(37,99,235,0.18)]'
                                  : 'border-white/10 bg-white/[0.02] text-slate-200 hover:bg-white/[0.08] hover:text-white',
                              )}
                            >
                              <Icon size={20} weight={active ? 'fill' : 'regular'} />
                              <span>{label}</span>
                            </Link>
                          </SheetClose>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              ))}
            </div>

            <div className="mt-auto border-t border-white/10 p-4">
              <Button onClick={onLogout} className="w-full justify-center rounded-xl bg-white/10 text-white hover:bg-white/20" variant="ghost">
                <SignOut size={18} />
                <span className="mr-1">تسجيل الخروج</span>
              </Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
