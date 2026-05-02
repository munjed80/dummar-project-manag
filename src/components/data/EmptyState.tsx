import { ReactNode } from 'react';
import { Tray } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

export interface EmptyStateProps {
  /** Headline shown in muted text. Defaults to the standard Arabic message. */
  title?: string;
  /** Optional secondary line below the title. */
  description?: string;
  /** Optional icon override; defaults to a soft inbox glyph. */
  icon?: ReactNode;
  /** Optional CTA (e.g. "إضافة أول فريق"). */
  action?: ReactNode;
  className?: string;
}

/**
 * EmptyState — the canonical "no data" panel for list pages and empty tables.
 * Soft, centered, low-contrast so it doesn't compete with the page header.
 */
export function EmptyState({
  title = 'لا توجد بيانات حالياً',
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        'py-12 px-4 text-muted-foreground',
        className,
      )}
    >
      <div className="mb-3 text-slate-300">
        {icon ?? <Tray size={40} weight="duotone" />}
      </div>
      <p className="text-sm font-medium text-slate-600">{title}</p>
      {description && (
        <p className="mt-1 text-xs text-slate-500 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
