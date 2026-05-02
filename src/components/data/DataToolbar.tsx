import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface DataToolbarProps {
  /** Slot for the search input (typically the first child). */
  search?: ReactNode;
  /** Slot for filter controls (selects). They wrap responsively. */
  filters?: ReactNode;
  /** Optional right-aligned action area (extra buttons / hints). */
  actions?: ReactNode;
  className?: string;
  /**
   * Children take precedence over the slot props when provided so callers can
   * use the toolbar as a generic flex shell without restructuring existing
   * markup. Useful for pages that mix legacy and new patterns.
   */
  children?: ReactNode;
}

/**
 * DataToolbar — the filter-bar shell for list pages.
 *
 * Provides a single, consistent layout: search input grows to fill, filter
 * controls wrap to a second row on narrow viewports, and any right-aligned
 * actions stay anchored. Spacing matches the rest of the data-shell card so
 * tables sit flush below it.
 */
export function DataToolbar({
  search,
  filters,
  actions,
  className,
  children,
}: DataToolbarProps) {
  if (children) {
    return (
      <div
        data-slot="data-toolbar"
        className={cn(
          'flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-3',
          className,
        )}
      >
        {children}
      </div>
    );
  }

  return (
    <div
      data-slot="data-toolbar"
      className={cn(
        'flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-3',
        className,
      )}
    >
      {search && <div className="flex-1 min-w-0 sm:min-w-[220px]">{search}</div>}
      {filters && (
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">{filters}</div>
      )}
      {actions && (
        <div className="flex flex-wrap gap-2 sm:ms-auto">{actions}</div>
      )}
    </div>
  );
}
