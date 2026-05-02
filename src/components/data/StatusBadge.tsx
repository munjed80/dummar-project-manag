import { ComponentProps } from 'react';
import { cn } from '@/lib/utils';

/**
 * StatusBadge — semantic, soft, consistent badges for data tables.
 *
 * The platform reserves saturated brand colors (primary blue / gold) for
 * actions and identity. Status indicators use a small, fixed palette of
 * soft tones so a row scans cleanly on a white card without competing with
 * the primary action button.
 *
 * Tone mapping (per design spec):
 *   success  — resolved / done / active / completed     → soft green
 *   info     — new / open / submitted                    → soft blue
 *   warning  — pending / under review / near expiry      → soft amber
 *   danger   — high / urgent / expired / rejected        → soft red
 *   progress — in-progress / processing / assigned       → soft indigo
 *   neutral  — default / draft / cancelled / inactive    → soft slate
 *   accent   — executive / VIP highlight (use sparingly) → soft gold
 */
export type StatusTone =
  | 'success'
  | 'info'
  | 'warning'
  | 'danger'
  | 'progress'
  | 'neutral'
  | 'accent';

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200',
  info: 'bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200',
  warning: 'bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200',
  danger: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-200',
  progress: 'bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-200',
  neutral: 'bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-200',
  accent: 'bg-[#FBF3DC] text-[#7A5E1F] ring-1 ring-inset ring-[#E8D397]',
};

export interface StatusBadgeProps extends ComponentProps<'span'> {
  tone?: StatusTone;
  /** Optional text override; otherwise renders children. */
  label?: string;
}

export function StatusBadge({
  tone = 'neutral',
  label,
  className,
  children,
  ...rest
}: StatusBadgeProps) {
  return (
    <span
      data-slot="status-badge"
      className={cn(
        'inline-flex items-center justify-center rounded-md px-2 py-0.5',
        'text-xs font-medium whitespace-nowrap w-fit',
        TONE_CLASSES[tone],
        className,
      )}
      {...rest}
    >
      {label ?? children}
    </span>
  );
}

/** Convenience map: callers can derive a tone from a domain status string. */
export const COMMON_STATUS_TONES: Record<string, StatusTone> = {
  // complaints / tasks
  new: 'info',
  open: 'info',
  submitted: 'info',
  pending: 'warning',
  under_review: 'warning',
  review: 'warning',
  assigned: 'progress',
  in_progress: 'progress',
  processing: 'progress',
  resolved: 'success',
  completed: 'success',
  done: 'success',
  approved: 'success',
  active: 'success',
  rejected: 'danger',
  failed: 'danger',
  expired: 'danger',
  // contracts
  draft: 'neutral',
  suspended: 'warning',
  near_expiry: 'warning',
  cancelled: 'neutral',
};

export function statusToneFor(status: string | null | undefined): StatusTone {
  if (!status) return 'neutral';
  return COMMON_STATUS_TONES[status] ?? 'neutral';
}
