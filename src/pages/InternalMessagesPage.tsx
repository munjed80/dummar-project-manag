import { useEffect, useMemo, useState } from 'react';
import { apiService, type MessageItem, type MessageThread, type User } from '@/services/api';

function fmtDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('ar-SY');
}

export default function InternalMessagesPage() {
  const [threads, setThreads] = useState<MessageThread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);
  const [threadTitle, setThreadTitle] = useState('');
  const [error, setError] = useState<string | null>(null);

  const selectedThread = useMemo(
    () => threads.find((t) => t.id === selectedThreadId) || null,
    [threads, selectedThreadId],
  );

  const loadThreads = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getMessageThreads();
      setThreads(Array.isArray(data) ? data : []);
      if (!selectedThreadId && data.length > 0) setSelectedThreadId(data[0].id);
    } catch (e: any) {
      setError(e?.message || 'تعذر تحميل المحادثات');
    } finally {
      setLoading(false);
    }
  };

  const loadThread = async (threadId: number) => {
    setError(null);
    try {
      const data = await apiService.getMessageThread(threadId);
      setMessages(Array.isArray(data?.messages) ? data.messages : []);
    } catch (e: any) {
      setError(e?.message || 'تعذر تحميل الرسائل');
      setMessages([]);
    }
  };

  useEffect(() => { void loadThreads(); }, []);
  useEffect(() => {
    if (selectedThreadId) void loadThread(selectedThreadId);
  }, [selectedThreadId]);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiService.getUsers({ limit: 200 });
        setUsers(res.items || []);
      } catch {
        setUsers([]);
      }
    })();
  }, []);

  const handleSend = async () => {
    if (!selectedThreadId || !draft.trim()) return;
    await apiService.sendMessage(selectedThreadId, { content: draft });
    setDraft('');
    await loadThread(selectedThreadId);
    await loadThreads();
  };

  const handleCreateThread = async () => {
    if (selectedUsers.length === 0) return;
    const isGroup = selectedUsers.length > 1;
    const thread = await apiService.createMessageThread({
      participant_ids: selectedUsers,
      is_group: isGroup,
      title: isGroup ? threadTitle || 'محادثة جماعية' : undefined,
    });
    setSelectedUsers([]);
    setThreadTitle('');
    await loadThreads();
    setSelectedThreadId(thread.id);
  };

  return (
    <div className="p-4 md:p-6" dir="rtl">
      <h1 className="text-2xl font-bold mb-4">الرسائل الداخلية</h1>
      {error && <div className="mb-3 rounded bg-red-50 p-2 text-red-700 text-sm">{error}</div>}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="border rounded-lg p-3 space-y-3">
          <h2 className="font-semibold">المحادثات</h2>
          {loading && <p className="text-sm text-gray-500">جاري التحميل...</p>}
          {!loading && threads.length === 0 && (
            <p className="text-sm text-gray-500">لا توجد محادثات بعد. ابدأ محادثة جديدة.</p>
          )}
          <div className="space-y-2 max-h-[420px] overflow-auto">
            {threads.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedThreadId(t.id)}
                className={`w-full text-right p-2 rounded border ${selectedThreadId === t.id ? 'bg-primary/10 border-primary' : ''}`}
              >
                <div className="font-medium">{t.title || `محادثة #${t.id}`}</div>
                <div className="text-xs text-gray-500">{t.last_message_preview || 'لا توجد رسائل'}</div>
                <div className="text-xs text-gray-400 flex justify-between">
                  <span>{fmtDate(t.last_message_at)}</span>
                  <span>غير مقروء: {t.unread_count || 0}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="pt-2 border-t">
            <h3 className="text-sm font-semibold mb-2">إنشاء محادثة</h3>
            <input
              className="w-full border rounded px-2 py-1 mb-2 text-sm"
              placeholder="عنوان المحادثة الجماعية (اختياري)"
              value={threadTitle}
              onChange={(e) => setThreadTitle(e.target.value)}
            />
            <select
              multiple
              className="w-full border rounded p-2 text-sm min-h-28"
              value={selectedUsers.map(String)}
              onChange={(e) => setSelectedUsers(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name} ({u.username})</option>
              ))}
            </select>
            <button className="mt-2 w-full bg-primary text-white rounded px-3 py-2 text-sm" onClick={handleCreateThread}>
              إنشاء محادثة مباشرة/جماعية
            </button>
          </div>
        </div>
        <div className="lg:col-span-2 border rounded-lg p-3 flex flex-col min-h-[520px]">
          {selectedThread ? (
            <>
              <div className="border-b pb-2 mb-2">
                <h2 className="font-semibold">{selectedThread.title || `محادثة #${selectedThread.id}`}</h2>
              </div>
              <div className="flex-1 space-y-2 overflow-auto">
                {messages.length === 0 ? (
                  <p className="text-sm text-gray-500">لا توجد رسائل في هذه المحادثة حتى الآن.</p>
                ) : messages.map((m) => (
                  <div key={m.id} className="border rounded p-2">
                    <div className="text-xs text-gray-500">{m.sender?.full_name || `مستخدم #${m.sender_id}`} • {fmtDate(m.created_at)}</div>
                    <p className="text-sm mt-1 whitespace-pre-wrap">{m.content}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-2">
                <input className="flex-1 border rounded px-3 py-2" placeholder="اكتب رسالة..." value={draft} onChange={(e) => setDraft(e.target.value)} />
                <button className="bg-primary text-white rounded px-4" onClick={handleSend}>إرسال</button>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">اختر محادثة من القائمة لبدء المراسلة.</div>
          )}
        </div>
      </div>
    </div>
  );
}
