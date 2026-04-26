import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowClockwise } from '@phosphor-icons/react';
import { offlineSyncManager, type SyncState } from '@/services/offlineSync';

const initialState: SyncState = {
  isOnline: navigator.onLine,
  pendingCount: 0,
  syncing: false,
  lastMessage: null,
};

export function OfflineSyncBanner() {
  const [state, setState] = useState<SyncState>(initialState);

  useEffect(() => {
    void offlineSyncManager.init();
    const unsub = offlineSyncManager.subscribe((next) => setState(next));
    return unsub;
  }, []);

  return (
    <div className="bg-amber-50 border-b border-amber-200 text-amber-900">
      <div className="container mx-auto px-4 py-2 text-sm flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          {!state.isOnline && <span className="font-semibold">أنت تعمل بدون اتصال</span>}
          <span>عمليات بانتظار المزامنة: {state.pendingCount}</span>
          {state.lastMessage && <span className="text-xs opacity-80">{state.lastMessage}</span>}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => offlineSyncManager.syncNow()}
          disabled={state.syncing || state.pendingCount === 0 || !state.isOnline}
        >
          <ArrowClockwise className={state.syncing ? 'animate-spin ml-1' : 'ml-1'} size={14} />
          مزامنة الآن
        </Button>
      </div>
    </div>
  );
}
