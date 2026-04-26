import { Link, useLocation } from 'react-router-dom';
import { Plus, MagnifyingGlass, House, SignIn } from '@phosphor-icons/react';

/**
 * Lightweight public header for citizen-facing pages
 * (landing, complaint submit, complaint track).
 *
 * Intentionally separate from the internal `Layout` so unauthenticated
 * visitors never see the internal admin shell, sidebar, or notifications.
 */
export function PublicHeader() {
  const { pathname } = useLocation();

  const navLinkClass = (active: boolean) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      active
        ? 'bg-primary-foreground/20 text-primary-foreground'
        : 'text-primary-foreground/85 hover:bg-primary-foreground/10'
    }`;

  return (
    <header className="sticky top-0 z-40 bg-primary text-primary-foreground shadow-md" dir="rtl">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <Link to="/" className="flex items-center gap-2 min-w-0">
          <House size={22} weight="fill" />
          <h1 className="text-base md:text-lg font-bold truncate">إدارة التجمع - مشروع دمر</h1>
        </Link>
        <nav className="flex items-center gap-1 md:gap-2">
          <Link to="/complaints/new" className={navLinkClass(pathname === '/complaints/new')}>
            <Plus size={16} />
            <span className="hidden sm:inline">تقديم طلب / شكوى</span>
            <span className="sm:hidden">طلب / شكوى</span>
          </Link>
          <Link to="/complaints/track" className={navLinkClass(pathname === '/complaints/track')}>
            <MagnifyingGlass size={16} />
            <span className="hidden sm:inline">تتبع طلب / شكوى</span>
            <span className="sm:hidden">تتبع</span>
          </Link>
          <Link to="/login" className={navLinkClass(pathname === '/login')}>
            <SignIn size={16} />
            <span className="hidden sm:inline">دخول الموظفين</span>
            <span className="sm:hidden">دخول</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col" dir="rtl">
      <PublicHeader />
      <main className="flex-1">{children}</main>
      <footer className="bg-muted py-4 mt-8">
        <div className="container mx-auto px-4 text-center text-muted-foreground text-xs md:text-sm">
          <p>© 2024 إدارة التجمع - مشروع دمر - دمشق | جميع الحقوق محفوظة</p>
        </div>
      </footer>
    </div>
  );
}
