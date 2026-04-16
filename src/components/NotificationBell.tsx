import { useState, useEffect, useRef } from 'react';
import { Bell } from '@phosphor-icons/react';
import { apiService } from '@/services/api';
import { formatDistanceToNow } from 'date-fns';
import { ar } from 'date-fns/locale';

interface NotificationItem {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  entity_type?: string;
  entity_id?: number;
  is_read: number;
  created_at: string;
}

export function NotificationBell() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const data = await apiService.getNotifications({ limit: 10 });
      setNotifications(data.items);
      setUnreadCount(data.unread_count);
    } catch {
      // silent fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Poll every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await apiService.markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: 1 })));
    } catch {
      // silent fail
    }
  };

  const handleToggle = () => {
    if (!open) fetchNotifications();
    setOpen(!open);
  };

  const entityLinks: Record<string, (id: number) => string> = {
    complaint: (id) => `/complaints/${id}`,
    task: (id) => `/tasks/${id}`,
    contract: (id) => `/contracts/${id}`,
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={handleToggle}
        className="relative p-2 text-primary-foreground hover:bg-primary/80 rounded-lg transition-colors"
        aria-label="الإشعارات"
      >
        <Bell size={22} weight={unreadCount > 0 ? 'fill' : 'regular'} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 w-80 max-h-96 bg-white rounded-lg shadow-xl border z-50 overflow-hidden" dir="rtl">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <h3 className="font-bold text-sm text-gray-800">الإشعارات</h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-primary hover:underline"
              >
                تعيين الكل كمقروء
              </button>
            )}
          </div>

          <div className="overflow-y-auto max-h-72">
            {loading && notifications.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">جارِ التحميل...</div>
            ) : notifications.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">لا توجد إشعارات</div>
            ) : (
              notifications.map((n) => {
                const link = n.entity_type && n.entity_id
                  ? entityLinks[n.entity_type]?.(n.entity_id)
                  : undefined;

                return (
                  <a
                    key={n.id}
                    href={link || '#'}
                    onClick={(e) => {
                      if (!link) e.preventDefault();
                    }}
                    className={`block px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 transition-colors ${
                      n.is_read === 0 ? 'bg-blue-50/50' : ''
                    }`}
                  >
                    <p className={`text-sm ${n.is_read === 0 ? 'font-bold text-gray-900' : 'text-gray-700'}`}>
                      {n.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">{n.message}</p>
                    <p className="text-[11px] text-gray-400 mt-1">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true, locale: ar })}
                    </p>
                  </a>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
