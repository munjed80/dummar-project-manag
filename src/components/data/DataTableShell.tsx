import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface DataTableShellProps {
  children: ReactNode;
  className?: string;
}

/**
 * DataTableShell — soft, government-blue card around a `<Table>`.
 *
 * Replaces the heavier `border rounded-lg overflow-hidden` divs that were
 * scattered across list pages. Borders use the platform soft-border token
 * (#D8E2EF), the corners are slightly rounded, and the wrapper provides
 * horizontal scroll on narrow desktop widths without forcing the parent
 * card to scroll.
 */
export function DataTableShell({ children, className }: DataTableShellProps) {
  return (
    <div
      data-slot="data-table-shell"
      className={cn(
        'rounded-lg border border-[#D8E2EF] bg-white overflow-hidden',
        // Header row gets a subtle fill via descendant selector so we don't
        // have to touch the shared <TableHeader> primitive.
        '[&_thead]:bg-[#F5F8FC] [&_thead_th]:text-slate-600',
        '[&_thead_th]:font-medium [&_thead_th]:text-xs [&_thead_th]:uppercase [&_thead_th]:tracking-wide',
        '[&_thead_th]:h-11',
        // Comfortable row height + subtle separators.
        '[&_tbody_tr]:border-b [&_tbody_tr]:border-[#EEF2F8]',
        '[&_tbody_tr:last-child]:border-b-0',
        '[&_tbody_tr:hover]:bg-[#F8FAFD]',
        '[&_tbody_td]:py-3 [&_tbody_td]:text-sm [&_tbody_td]:text-slate-700',
        // Scroll horizontally only when truly necessary.
        'overflow-x-auto',
        className,
      )}
    >
      {children}
    </div>
  );
}
