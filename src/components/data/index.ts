/**
 * Reusable data-presentation primitives for list pages.
 *
 * Import via the barrel:
 *   import {
 *     DataTableShell, DataToolbar, StatusBadge, PriorityBadge,
 *     EmptyState, ErrorState, LoadingSkeleton, PaginationBar,
 *     MobileEntityCard,
 *   } from '@/components/data';
 */
export { StatusBadge, statusToneFor, COMMON_STATUS_TONES } from './StatusBadge';
export type { StatusBadgeProps, StatusTone } from './StatusBadge';

export { PriorityBadge } from './PriorityBadge';
export type { PriorityBadgeProps, Priority } from './PriorityBadge';

export { EmptyState } from './EmptyState';
export type { EmptyStateProps } from './EmptyState';

export { ErrorState } from './ErrorState';
export type { ErrorStateProps } from './ErrorState';

export { LoadingSkeleton } from './LoadingSkeleton';
export type { LoadingSkeletonProps } from './LoadingSkeleton';

export { PaginationBar } from './PaginationBar';
export type { PaginationBarProps } from './PaginationBar';

export { DataToolbar } from './DataToolbar';
export type { DataToolbarProps } from './DataToolbar';

export { DataTableShell } from './DataTableShell';
export type { DataTableShellProps } from './DataTableShell';

export { MobileEntityCard } from './MobileEntityCard';
export type { MobileEntityCardProps } from './MobileEntityCard';
