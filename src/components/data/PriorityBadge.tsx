import { ComponentProps } from 'react';
import { StatusBadge, StatusTone } from './StatusBadge';

/**
 * PriorityBadge — soft, semantic badge for priority/severity values
 * (low / medium / high / urgent). Mirrors {@link StatusBadge} so the visual
 * weight stays consistent across columns in the same row.
 */
export type Priority = 'low' | 'medium' | 'high' | 'urgent' | string;

const PRIORITY_TONES: Record<string, StatusTone> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  urgent: 'danger',
};

export interface PriorityBadgeProps extends ComponentProps<'span'> {
  priority: Priority | null | undefined;
  /** Optional Arabic label override; defaults to {priority} as-is. */
  label?: string;
}

export function PriorityBadge({
  priority,
  label,
  className,
  ...rest
}: PriorityBadgeProps) {
  const key = (priority ?? '').toString();
  const tone = PRIORITY_TONES[key] ?? 'neutral';
  return (
    <StatusBadge tone={tone} className={className} {...rest}>
      {label ?? key ?? '-'}
    </StatusBadge>
  );
}
