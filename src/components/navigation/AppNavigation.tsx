import { Link } from 'react-router-dom';
import { List, Plus, SignOut } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import { NotificationBell } from '@/components/NotificationBell';
import { type NavItem } from '@/components/navigation/nav-config';

interface AppNavigationProps {
  navItems: NavItem[];
  pathname: string;
  onLogout: () => void;
  showInternalComplaintAction: boolean;
}

interface MobileNavigationProps extends AppNavigationProps {
  title?: string;
}

function isActive(pathname: string, path: string) {
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function DesktopNavigation({ navItems, pathname }: Pick<AppNavigationProps, 'navItems' | 'pathname'>) {
  return (
    <nav className="hidden lg:block border-t border-primary-foreground/20 bg-primary/95">
      <div className="container mx-auto px-4">
        <div className="overflow-x-auto py-3 [scrollbar-width:thin]">
          <ul className="flex min-w-max items-center gap-2 whitespace-nowrap">
            {navItems.map(({ path, icon: Icon, label }) => {
              const active = isActive(pathname, path);
              return (
                <li key={path}>
                  <Link
                    to={path}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors border',
                      active
                        ? 'bg-white/18 text-white border-white/35 shadow-sm'
                        : 'bg-transparent text-primary-foreground/85 border-transparent hover:bg-white/10 hover:text-white',
                    )}
                  >
                    <Icon size={17} weight={active ? 'fill' : 'regular'} />
                    <span>{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </nav>
  );
}

export function MobileNavigation({ navItems, pathname, onLogout, showInternalComplaintAction, title = 'إدارة التجمع - مشروع دمر' }: MobileNavigationProps) {
  return (
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
            <SheetTitle className="text-right text-lg text-white">{title}</SheetTitle>
          </SheetHeader>

          <div className="border-b border-white/10 px-5 py-4">
            <div className="grid grid-cols-1 gap-2">
              <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-100">
                <span>الإشعارات</span>
                <NotificationBell />
              </div>
              {showInternalComplaintAction && (
                <a
                  href="/complaints/new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-100 hover:bg-white/[0.09] transition-colors"
                >
                  <Plus size={18} />
                  <span>تقديم شكوى داخلية</span>
                </a>
              )}
            </div>
          </div>

          <div className="px-5 pb-8 pt-4 overflow-y-auto">
            <ul className="space-y-1.5">
              {navItems.map(({ path, icon: Icon, label }) => {
                const active = isActive(pathname, path);
                return (
                  <li key={`drawer-${path}`}>
                    <SheetClose asChild>
                      <Link
                        to={path}
                        className={cn(
                          'flex items-center gap-3 rounded-xl px-4 py-3 text-base transition-colors border',
                          active
                            ? 'bg-blue-500/20 border-blue-300/35 text-white'
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
  );
}
