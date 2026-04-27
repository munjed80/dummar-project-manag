import { Link } from 'react-router-dom';
import { List } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import type { UserRole } from '@/hooks/useAuth';
import { DESKTOP_GROUP_LABELS, MOBILE_GROUP_LABELS, type NavItem, formatRoleLabel } from '@/components/navigation/nav-config';

interface AppNavigationProps {
  navItems: NavItem[];
  pathname: string;
  userName?: string;
  role: UserRole | null;
}

function isActive(pathname: string, path: string) {
  return pathname === path || pathname.startsWith(`${path}/`);
}

const DESKTOP_GROUP_ORDER: NavItem['section'][] = ['home', 'work', 'contracts', 'assets', 'admin'];
const MOBILE_GROUP_ORDER: NavItem['mobileSection'][] = ['dashboard', 'operations', 'contracts', 'assets_admin'];

export function AppNavigation({ navItems, pathname, userName, role }: AppNavigationProps) {
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
      <nav className="hidden xl:block border-t border-primary-foreground/20 bg-primary/95">
        <div className="container mx-auto px-4 py-3">
          <div className="flex flex-wrap items-start gap-3">
            {groupedDesktop.map((group) => (
              <section key={group.group} className="rounded-2xl border border-primary-foreground/20 bg-primary-foreground/8 px-2.5 py-2.5 backdrop-blur-sm">
                <h3 className="px-2 pb-2 text-[11px] font-semibold text-primary-foreground/75">{group.label}</h3>
                <ul className="flex flex-wrap gap-1.5">
                  {group.items.map(({ path, icon: Icon, label }) => {
                    const active = isActive(pathname, path);
                    return (
                      <li key={path}>
                        <Link
                          to={path}
                          className={cn(
                            'inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200 border',
                            active
                              ? 'border-amber-200/45 bg-primary-foreground/20 text-primary-foreground shadow-[0_2px_10px_rgba(15,23,42,0.18)]'
                              : 'border-transparent text-primary-foreground/85 hover:text-primary-foreground hover:bg-primary-foreground/12',
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

      <div className="xl:hidden">
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
                                'flex items-center gap-3 rounded-2xl px-4 py-3 text-base transition-all duration-200 border',
                                active
                                  ? 'bg-blue-500/20 border-blue-300/35 text-white shadow-[0_8px_24px_rgba(37,99,235,0.18)]'
                                  : 'border-transparent text-slate-200 hover:bg-white/8 hover:text-white',
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
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
