import { Link, useLocation } from 'react-router-dom';
import { Robot } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

/**
 * Topbar icon that opens the internal smart assistant.  Lives next to the
 * notification bell — it is intentionally NOT a sidebar entry.
 */
export function SmartAssistantButton() {
  const { pathname } = useLocation();
  const active = pathname === '/internal-bot' || pathname.startsWith('/internal-bot/');
  return (
    <Link
      to="/internal-bot"
      title="المساعد الذكي"
      aria-label="المساعد الذكي"
      className={cn(
        'relative inline-flex items-center justify-center rounded-lg border p-2 transition-colors',
        active
          ? 'bg-primary-foreground/20 text-primary-foreground border-primary-foreground/35'
          : 'text-primary-foreground hover:bg-primary-foreground/10 border-transparent hover:border-primary-foreground/25',
      )}
    >
      <Robot size={22} weight={active ? 'fill' : 'regular'} />
    </Link>
  );
}

export default SmartAssistantButton;
