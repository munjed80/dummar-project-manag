import { useEffect, useRef, useState } from 'react';
import { ArrowsClockwise, CloudSlash, CheckCircle, WarningCircle } from '@phosphor-icons/react';
import { offlineSyncManager, type SyncState } from '@/services/offlineSync';
import { formatDistanceToNow } from 'date-fns';
import { ar } from 'date-fns/locale';
import { cn } from '@/lib/utils';

const initialState: SyncState = {
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  pendingCount: 0,
  syncing: false,
  lastMessage: null,
};

type Status = 'syncing' | 'offline' | 'pending' | 'error' | 'synced';

function deriveStatus(state: SyncState, hasError: boolean): Status {
  if (state.syncing) return 'syncing';
  if (!state.isOnline) return 'offline';
  if (hasError) return 'error';
  if (state.pendingCount > 0) return 'pending';
  return 'synced';
}

/**
 * Compact sync status control for the topbar — replaces the previous
 * full-width yellow `OfflineSyncBanner`.  Click to open a small popover
 * with status, last update time, pending count, connection mode, and a
 * "sync now" action.  Visual states are intentionally subtle: green for
 * synced, spinner for syncing, gray for offline, amber dot only when
 * there are pending items, red dot only on a real sync error.
 */
export function SyncStatusButton() {
  const [state, setState] = useState<SyncState>(initialState);
  const [open, setOpen] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const wasSyncing = useRef(false);

  useEffect(() => {
    void offlineSyncManager.init();
    const unsub = offlineSyncManager.subscribe((next) => {
      // Capture the moment we transition out of syncing — that's the
      // most meaningful "last update" for the user.
      if (wasSyncing.current && !next.syncing) {
        setLastSyncedAt(new Date());
      }
      wasSyncing.current = next.syncing;
      setState(next);
    });
    return unsub;
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const hasError = Boolean(state.lastMessage && /فشل/.test(state.lastMessage));
  const status = deriveStatus(state, hasError);

  const indicator = (() => {
    switch (status) {
      case 'syncing':
        return <span className="absolute -top-0.5 -right-0.5 inline-block h-2 w-2 rounded-full bg-sky-300 ring-2 ring-[#123B63]" />;
      case 'offline':
        return <span className="absolute -top-0.5 -right-0.5 inline-block h-2 w-2 rounded-full bg-slate-400 ring-2 ring-[#123B63]" />;
      case 'pending':
        return <span className="absolute -top-0.5 -right-0.5 inline-block h-2 w-2 rounded-full bg-amber-400 ring-2 ring-[#123B63]" />;
      case 'error':
        return <span className="absolute -top-0.5 -right-0.5 inline-block h-2 w-2 rounded-full bg-red-500 ring-2 ring-[#123B63]" />;
      case 'synced':
      default:
        return <span className="absolute -top-0.5 -right-0.5 inline-block h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-[#123B63]" />;
    }
  })();

  const label = (() => {
    switch (status) {
      case 'syncing': return 'جارٍ المزامنة...';
      case 'offline': return 'غير متصل';
      case 'pending': return `عناصر معلقة: ${state.pendingCount}`;
      case 'error':   return 'فشل في المزامنة';
      case 'synced':
      default:        return 'متزامن';
    }
  })();

  const Icon = status === 'offline' ? CloudSlash
             : status === 'error'   ? WarningCircle
             : status === 'synced'  ? CheckCircle
             : ArrowsClockwise;

  const lastUpdateText = lastSyncedAt
    ? formatDistanceToNow(lastSyncedAt, { addSuffix: true, locale: ar })
    : '—';

  const canSyncNow = state.isOnline && !state.syncing && state.pendingCount > 0;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'relative inline-flex items-center justify-center rounded-lg border p-2 transition-colors',
          open
            ? 'bg-primary-foreground/20 text-primary-foreground border-primary-foreground/35'
            : 'text-primary-foreground hover:bg-primary-foreground/10 border-transparent hover:border-primary-foreground/25',
        )}
        title={label}
        aria-label={`حالة المزامنة: ${label}`}
      >
        <Icon
          size={22}
          weight={status === 'synced' ? 'fill' : 'regular'}
          className={status === 'syncing' ? 'animate-spin' : ''}
        />
        {indicator}
      </button>

      {open && (
        <div
          className="absolute left-0 top-full mt-2 w-72 bg-white rounded-lg shadow-xl border z-50 overflow-hidden text-slate-800"
          dir="rtl"
        >
          <div className="px-4 py-3 border-b bg-slate-50">
            <h3 className="font-bold text-sm">حالة المزامنة</h3>
          </div>
          <div className="px-4 py-3 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">الحالة</span>
              <span className="font-semibold">{label}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">آخر تحديث</span>
              <span>{lastUpdateText}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">العناصر المعلقة</span>
              <span>{state.pendingCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">وضع الاتصال</span>
              <span>{state.isOnline ? 'متصل' : 'غير متصل'}</span>
            </div>
            {state.lastMessage && (
              <p className="text-xs text-slate-500 pt-1 border-t mt-2">
                {state.lastMessage}
              </p>
            )}
          </div>
          <div className="px-4 py-3 border-t bg-slate-50">
            <button
              type="button"
              onClick={() => offlineSyncManager.syncNow()}
              disabled={!canSyncNow}
              className={cn(
                'w-full inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors',
                canSyncNow
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed',
              )}
            >
              <ArrowsClockwise size={16} className={state.syncing ? 'animate-spin' : ''} />
              مزامنة الآن
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default SyncStatusButton;
