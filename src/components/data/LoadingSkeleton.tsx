import { Skeleton } from '@/components/ui/skeleton';

export interface LoadingSkeletonProps {
  /** Number of skeleton rows to render. Defaults to 6. */
  rows?: number;
  /** Number of cells per row (desktop). Defaults to 5. */
  columns?: number;
  /** Whether to render the mobile-card skeleton variant instead. */
  variant?: 'table' | 'cards';
}

/**
 * LoadingSkeleton — table-shaped or card-shaped placeholder rows.
 *
 * Lightweight (uses the existing `<Skeleton>` primitive). Avoid using a
 * spinner for list pages — the skeleton preserves the table footprint and
 * prevents layout shift when data arrives.
 */
export function LoadingSkeleton({
  rows = 6,
  columns = 5,
  variant = 'table',
}: LoadingSkeletonProps) {
  if (variant === 'cards') {
    return (
      <div
        className="space-y-3"
        data-slot="loading-skeleton-cards"
        role="status"
        aria-busy="true"
        aria-label="جارٍ التحميل"
      >
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border border-[#D8E2EF] bg-white p-3"
          >
            <div className="flex items-center justify-between mb-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-16 rounded-md" />
            </div>
            <Skeleton className="h-4 w-3/4 mb-2" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className="space-y-2 px-2 py-1.5"
      data-slot="loading-skeleton-table"
      role="status"
      aria-busy="true"
      aria-label="جارٍ التحميل"
    >
      {/* header line */}
      <div className="flex gap-3 pb-2">
        {Array.from({ length: columns }).map((_, c) => (
          <Skeleton key={`h-${c}`} className="h-3 flex-1 max-w-[120px]" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3 py-2">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton key={`${r}-${c}`} className="h-4 flex-1 max-w-[160px]" />
          ))}
        </div>
      ))}
    </div>
  );
}
