import { Spinner, Warning } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/**
 * Small inline indicator shown while a background refresh is running on a
 * page that already has cached data on screen. Deliberately calm so it
 * doesn't compete with the actual content.
 */
export function RefreshingIndicator({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center gap-2 text-xs text-muted-foreground',
        className,
      )}
    >
      <Spinner size={12} className="animate-spin" aria-hidden="true" />
      <span>جارِ تحديث البيانات…</span>
    </div>
  );
}

/**
 * Soft inline notice shown when a background refresh failed but cached
 * data is still being displayed. The page must keep rendering the cached
 * payload so the operator never loses context.
 */
export function StaleDataNotice({
  onRetry,
  retrying = false,
  className,
}: {
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex flex-wrap items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900',
        className,
      )}
    >
      <Warning size={14} className="text-amber-600 shrink-0" aria-hidden="true" />
      <span className="flex-1">
        تعذر تحديث البيانات حالياً، يتم عرض آخر نسخة متاحة.
      </span>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          className="h-7 border-amber-300 bg-white text-amber-800 hover:bg-amber-100"
          onClick={onRetry}
          disabled={retrying}
        >
          {retrying ? 'جارٍ المحاولة…' : 'إعادة المحاولة'}
        </Button>
      )}
    </div>
  );
}
