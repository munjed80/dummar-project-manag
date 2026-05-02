import { Warning } from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface ErrorStateProps {
  /** Operator-friendly Arabic message. Falls back to the standard line. */
  message?: string;
  /** Optional retry handler — when provided, a "إعادة المحاولة" button is shown. */
  onRetry?: () => void;
  /** Show a small spinner inside the retry button while reload is in flight. */
  retrying?: boolean;
  className?: string;
}

/**
 * ErrorState — soft, non-alarming error panel for list pages.
 *
 * The component never shows raw technical errors; callers are expected to
 * pass a sanitized Arabic message (typically from {@link describeLoadError}).
 */
export function ErrorState({
  message = 'تعذر تحميل البيانات حالياً. يرجى إعادة المحاولة.',
  onRetry,
  retrying = false,
  className,
}: ErrorStateProps) {
  return (
    <div
      data-slot="error-state"
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        'py-10 px-4 rounded-lg bg-red-50/60 ring-1 ring-inset ring-red-100',
        className,
      )}
    >
      <Warning size={32} weight="duotone" className="text-red-400 mb-2" />
      <p className="text-sm text-red-700 max-w-md">{message}</p>
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          className="mt-4 border-red-200 text-red-700 hover:bg-red-50"
          onClick={onRetry}
          disabled={retrying}
        >
          {retrying ? 'جارٍ المحاولة…' : 'إعادة المحاولة'}
        </Button>
      )}
    </div>
  );
}
