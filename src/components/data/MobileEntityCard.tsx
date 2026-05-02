import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface MobileEntityCardProps {
  /** Primary identifier for the row — usually a tracking number or title. */
  title: ReactNode;
  /** Optional status badge slot, rendered top-trailing for quick scanning. */
  badge?: ReactNode;
  /** Optional secondary line (e.g. full name, contractor, owner). */
  subtitle?: ReactNode;
  /**
   * Bottom meta row — typically a list of small spans with `•` separators
   * (type, area, date, etc). Keep to the most important fields only.
   */
  meta?: ReactNode;
  /** Click/tap handler. The card gets cursor-pointer and an accessible role. */
  onClick?: () => void;
  className?: string;
}

/**
 * MobileEntityCard — the mobile-only counterpart to a desktop table row.
 *
 * Used on phones to render data-heavy lists (complaints, tasks, contracts)
 * as scannable cards. Soft borders, comfortable padding, and a clear tap
 * target. No shadow — the platform avoids heavy elevation.
 */
export function MobileEntityCard({
  title,
  badge,
  subtitle,
  meta,
  onClick,
  className,
}: MobileEntityCardProps) {
  const interactive = typeof onClick === 'function';
  return (
    <div
      data-slot="mobile-entity-card"
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={cn(
        'rounded-lg border border-[#D8E2EF] bg-white p-3.5',
        'transition-colors',
        interactive && 'cursor-pointer hover:bg-[#F8FAFD] active:bg-[#F1F5FB]',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1D4ED8]/40',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="text-sm font-semibold text-slate-800 flex-1 min-w-0 break-words">
          {title}
        </div>
        {badge && <div className="shrink-0">{badge}</div>}
      </div>
      {subtitle && (
        <p className="text-sm text-slate-700 mb-2 break-words">{subtitle}</p>
      )}
      {meta && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
          {meta}
        </div>
      )}
    </div>
  );
}
