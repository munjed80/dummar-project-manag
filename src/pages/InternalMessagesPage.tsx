import { useEffect, useMemo, useState, useCallback } from 'react';
import { Layout } from '@/components/Layout';
import {
  apiService,
  ApiError,
  type MessageItem,
  type MessageThread,
  type User,
} from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  ChatCircleDots, Plus, PaperPlaneRight, Spinner, UsersThree, Warning,
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';

function fmtDateTime(value?: string | null) {
  if (!value) return '';
  try {
    return new Date(value).toLocaleString('ar-SY');
  } catch {
    return value;
  }
}

export default function InternalMessagesPage() {
  const { user: currentUser } = useAuth();
  const [threads, setThreads] = useState<MessageThread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);

  // New thread dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newParticipantIds, setNewParticipantIds] = useState<number[]>([]);

  const userMap = useMemo(() => {
    const map = new Map<number, User>();
    users.forEach((u) => map.set(u.id, u));
    return map;
  }, [users]);

  const selectedThread = useMemo(
    () => threads.find((t) => t.id === selectedThreadId) || null,
    [threads, selectedThreadId],
  );

  const loadThreads = useCallback(async (preselectId?: number) => {
    setLoadingThreads(true);
    setError(null);
    try {
      const data = await apiService.getMessageThreads({ limit: 100 });
      const list = Array.isArray(data) ? data : [];
      setThreads(list);
      setSelectedThreadId((current) => {
        if (preselectId && list.some((t) => t.id === preselectId)) return preselectId;
        if (current && list.some((t) => t.id === current)) return current;
        return list.length > 0 ? list[0].id : null;
      });
    } catch (e) {
      setError(describeLoadError(e, 'المحادثات').message);
      setThreads([]);
    } finally {
      setLoadingThreads(false);
    }
  }, []);

  const loadThread = useCallback(async (threadId: number) => {
    setLoadingMessages(true);
    setError(null);
    try {
      const data = await apiService.getMessageThread(threadId);
      setMessages(Array.isArray(data?.messages) ? data.messages : []);
    } catch (e) {
      setError(describeLoadError(e, 'الرسائل').message);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => { void loadThreads(); }, [loadThreads]);

  useEffect(() => {
    if (selectedThreadId) void loadThread(selectedThreadId);
    else setMessages([]);
  }, [selectedThreadId, loadThread]);

  // Load internal users for thread creation. Failure is non-fatal: the user
  // simply won't be able to start a brand-new thread.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiService.getUsers({ limit: 200 });
        if (cancelled) return;
        const list = Array.isArray(res?.items) ? res.items : [];
        // Hide the current user from the picker to avoid inviting themselves.
        setUsers(list.filter((u) => u.id !== currentUser?.id));
      } catch {
        if (!cancelled) setUsers([]);
      }
    })();
    return () => { cancelled = true; };
  }, [currentUser?.id]);

  const handleSend = async () => {
    if (!selectedThreadId) return;
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    try {
      await apiService.sendMessage(selectedThreadId, { body });
      setDraft('');
      await loadThread(selectedThreadId);
      // Refresh threads list to update last_message preview / order.
      await loadThreads(selectedThreadId);
    } catch (e) {
      const msg = e instanceof ApiError ? (e.detail || e.message) : 'تعذّر إرسال الرسالة';
      toast.error(msg);
    } finally {
      setSending(false);
    }
  };

  const handleCreateThread = async () => {
    if (newParticipantIds.length === 0) {
      toast.error('اختر مشاركاً واحداً على الأقل');
      return;
    }
    setCreating(true);
    try {
      const thread = await apiService.createMessageThread({
        participant_user_ids: newParticipantIds,
        title: newTitle.trim() || undefined,
      });
      setCreateOpen(false);
      setNewTitle('');
      setNewParticipantIds([]);
      await loadThreads(thread.id);
      toast.success('تم إنشاء المحادثة');
    } catch (e) {
      const msg = e instanceof ApiError ? (e.detail || e.message) : 'تعذّر إنشاء المحادثة';
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  };

  const toggleParticipant = (userId: number) => {
    setNewParticipantIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId],
    );
  };

  const senderLabel = (m: MessageItem) => {
    if (currentUser && m.sender_user_id === currentUser.id) return 'أنت';
    const u = userMap.get(m.sender_user_id);
    return u ? u.full_name : `مستخدم #${m.sender_user_id}`;
  };

  const threadTitle = (t: MessageThread): string => {
    if (t.title) return t.title;
    if (t.thread_type === 'group') return 'محادثة جماعية';
    // For direct threads, show the other participant's name when known.
    const other = t.participants?.find((p) => p.user_id !== currentUser?.id);
    if (other) {
      const u = userMap.get(other.user_id);
      if (u) return u.full_name;
      return `مستخدم #${other.user_id}`;
    }
    return `محادثة #${t.id}`;
  };

  return (
    <Layout>
      <div dir="rtl" className="p-4 md:p-6 space-y-4">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <ChatCircleDots size={24} className="text-primary" />
              الرسائل الداخلية
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              قناة تواصل داخلية بين موظفي البلدية والفرق التنفيذية.
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)} className="gap-2">
            <Plus size={16} weight="bold" />
            محادثة جديدة
          </Button>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <Warning size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Thread list */}
          <Card className="lg:col-span-1 min-h-[600px] flex flex-col">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">المحادثات</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto px-2">
              {loadingThreads ? (
                <div className="flex items-center justify-center py-10 text-muted-foreground">
                  <Spinner size={20} className="animate-spin ml-2" />
                  جاري التحميل...
                </div>
              ) : threads.length === 0 ? (
                <div className="text-center py-10 text-sm text-muted-foreground">
                  <ChatCircleDots size={36} className="mx-auto mb-2 opacity-40" />
                  لا توجد محادثات بعد. ابدأ محادثة جديدة.
                </div>
              ) : (
                <ul className="space-y-1">
                  {threads.map((t) => {
                    const isActive = t.id === selectedThreadId;
                    const preview = t.last_message?.body || 'لا توجد رسائل بعد';
                    const time = t.last_message?.created_at || t.updated_at;
                    return (
                      <li key={t.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedThreadId(t.id)}
                          className={`w-full text-right p-3 rounded-md border transition-colors ${
                            isActive
                              ? 'bg-primary/10 border-primary'
                              : 'border-transparent hover:bg-muted/40'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-medium truncate flex items-center gap-1">
                              {t.thread_type === 'group' && (
                                <UsersThree size={14} className="text-muted-foreground" />
                              )}
                              <span className="truncate">{threadTitle(t)}</span>
                            </div>
                            {(t.unread_count ?? 0) > 0 && (
                              <Badge variant="destructive" className="text-[10px] h-5">
                                {t.unread_count}
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1 truncate">
                            {preview}
                          </div>
                          <div className="text-[11px] text-muted-foreground mt-1">
                            {fmtDateTime(time)}
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* Conversation panel */}
          <Card className="lg:col-span-2 min-h-[600px] flex flex-col">
            {selectedThread ? (
              <>
                <CardHeader className="pb-2 border-b">
                  <CardTitle className="text-base flex items-center gap-2">
                    {selectedThread.thread_type === 'group' && (
                      <UsersThree size={16} className="text-muted-foreground" />
                    )}
                    {threadTitle(selectedThread)}
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    {selectedThread.participants?.length || 0} مشاركاً ·{' '}
                    {selectedThread.thread_type === 'group' ? 'جماعية' : 'مباشرة'}
                  </p>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto py-3 space-y-2">
                  {loadingMessages ? (
                    <div className="flex items-center justify-center py-10 text-muted-foreground">
                      <Spinner size={20} className="animate-spin ml-2" />
                      جاري التحميل...
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="text-center py-10 text-sm text-muted-foreground">
                      لا توجد رسائل في هذه المحادثة بعد. اكتب أول رسالة أدناه.
                    </div>
                  ) : (
                    messages.map((m) => {
                      const isMine = currentUser && m.sender_user_id === currentUser.id;
                      return (
                        <div
                          key={m.id}
                          className={`flex ${isMine ? 'justify-start' : 'justify-end'}`}
                        >
                          <div
                            className={`max-w-[80%] rounded-lg p-3 border ${
                              isMine ? 'bg-primary/10 border-primary/30' : 'bg-muted/40'
                            }`}
                          >
                            <div className="text-xs text-muted-foreground mb-1 flex justify-between gap-3">
                              <span className="font-medium">{senderLabel(m)}</span>
                              <span>{fmtDateTime(m.created_at)}</span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap break-words">{m.body}</p>
                          </div>
                        </div>
                      );
                    })
                  )}
                </CardContent>
                <div className="border-t p-3 flex gap-2">
                  <Input
                    placeholder="اكتب رسالة..."
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        void handleSend();
                      }
                    }}
                    disabled={sending}
                    className="flex-1"
                  />
                  <Button onClick={handleSend} disabled={sending || !draft.trim()} className="gap-2">
                    {sending ? <Spinner size={16} className="animate-spin" /> : <PaperPlaneRight size={16} />}
                    إرسال
                  </Button>
                </div>
              </>
            ) : (
              <CardContent className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
                {threads.length === 0
                  ? 'لا توجد محادثات. أنشئ محادثة جديدة لتبدأ.'
                  : 'اختر محادثة من القائمة لعرض الرسائل.'}
              </CardContent>
            )}
          </Card>
        </div>

        {/* Create thread dialog */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent dir="rtl" className="max-w-lg">
            <DialogHeader>
              <DialogTitle>محادثة جديدة</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium block mb-1">
                  عنوان المحادثة (اختياري للمحادثات الجماعية)
                </label>
                <Input
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="مثال: تنسيق فريق المنطقة الشرقية"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">
                  المشاركون ({newParticipantIds.length} مختار)
                </label>
                {users.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    لا توجد قائمة مستخدمين متاحة.
                  </p>
                ) : (
                  <div className="max-h-64 overflow-auto border rounded-md divide-y">
                    {users.map((u) => {
                      const checked = newParticipantIds.includes(u.id);
                      return (
                        <label
                          key={u.id}
                          className="flex items-center gap-2 p-2 cursor-pointer hover:bg-muted/30"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleParticipant(u.id)}
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium">{u.full_name}</div>
                            <div className="text-xs text-muted-foreground">{u.username}</div>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  اختر مستخدماً واحداً لمحادثة مباشرة، أو أكثر لإنشاء محادثة جماعية.
                </p>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={creating}>
                إلغاء
              </Button>
              <Button onClick={handleCreateThread} disabled={creating || newParticipantIds.length === 0}>
                {creating ? <Spinner size={16} className="animate-spin ml-1" /> : null}
                إنشاء
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
