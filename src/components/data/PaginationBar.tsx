import { Button } from '@/components/ui/button';
import { CaretLeft, CaretRight } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

export interface PaginationBarProps {
  /** Zero-based current page index. */
  page: number;
  /** Total number of pages (>= 1). */
  totalPages: number;
  /** Total record count, used for the right-aligned counter. */
  totalCount: number;
  /** Page size, used to compute the displayed range. */
  pageSize: number;
  /** Arabic noun for the entity (used in the counter — e.g. "شكوى"). */
  entityLabel?: string;
  /** Called with the next page index. */
  onPageChange: (next: number) => void;
  className?: string;
}

/**
 * PaginationBar — clean, RTL-aware pagination footer for list pages.
 *
 * Visual contract:
 *  - left side  → Prev / Next buttons (in DOM order; RTL flips on screen)
 *  - center     → "صفحة X من Y"
 *  - right side → "عرض A - B من N"
 *
 * The bar renders nothing when there is at most one page; callers can use
 * the {@link PaginationBar} directly without a `totalPages > 1` guard.
 */
export function PaginationBar({
  page,
  totalPages,
  totalCount,
  pageSize,
  entityLabel,
  onPageChange,
  className,
}: PaginationBarProps) {
  if (totalPages <= 1) return null;

  const from = page * pageSize + 1;
  const to = Math.min((page + 1) * pageSize, totalCount);

  return (
    <div
      data-slot="pagination-bar"
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 pt-4 mt-2',
        'border-t border-[#E2EAF4] text-sm text-slate-600',
        className,
      )}
    >
      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          className="h-8 px-2.5 border-[#D8E2EF]"
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
        >
          <CaretRight size={14} className="ml-1" />
          السابق
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8 px-2.5 border-[#D8E2EF]"
          disabled={page >= totalPages - 1}
          onClick={() => onPageChange(page + 1)}
        >
          التالي
          <CaretLeft size={14} className="mr-1" />
        </Button>
      </div>

      <div className="text-xs text-slate-500">
        صفحة <span className="font-medium text-slate-700">{page + 1}</span>{' '}
        من <span className="font-medium text-slate-700">{totalPages}</span>
      </div>

      <div className="text-xs text-slate-500">
        عرض {from} - {to} من {totalCount}
        {entityLabel ? ` ${entityLabel}` : ''}
      </div>
    </div>
  );
}
