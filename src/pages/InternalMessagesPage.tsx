import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Layout } from '@/components/Layout';
import {
  apiService,
  ApiError,
  type MessageItem,
  type MessageThread,
  type User,
} from '@/services/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  ChatCircleDots,
  Plus,
  PaperPlaneRight,
  Spinner,
  UsersThree,
  Warning,
  MagnifyingGlass,
  ArrowClockwise,
  UserCircle,
  ChatTeardropDots,
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';

function fmtDateTime(value?: string | null) {
  if (!value) return '';
  try {
    return new Date(value).toLocaleString('ar-SY', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return value;
  }
}

function fmtRelative(value?: string | null): string {
  if (!value) return '';
  try {
    const diff = Date.now() - new Date(value).getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return 'الآن';
    if (mins < 60) return `منذ ${mins} د`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `منذ ${hrs} س`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `منذ ${days} ي`;
    return new Date(value).toLocaleDateString('ar-SY');
  } catch {
    return value;
  }
}

function AvatarIcon({ name, mine }: { name: string; mine?: boolean }) {
  const initials = name
    .split(' ')
    .map((w) => w[0] ?? '')
    .slice(0, 2)
    .join('');
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
        mine
          ? 'bg-sky-600 text-white'
          : 'bg-slate-600 text-slate-200'
      }`}
      title={name}
    >
      {initials || <UserCircle size={16} />}
    </div>
  );
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
  const [mobileShowThread, setMobileShowThread] = useState(false);

  const [threadSearch, setThreadSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newParticipantIds, setNewParticipantIds] = useState<number[]>([]);
  const [userSearch, setUserSearch] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Counter for generating unique negative temporary IDs for optimistic messages.
  const optimisticIdCounterRef = useRef(0);

  const userMap = useMemo(() => {
    const map = new Map<number, User>();
    users.forEach((u) => map.set(u.id, u));
    return map;
  }, [users]);

  const selectedThread = useMemo(
    () => threads.find((t) => t.id === selectedThreadId) || null,
    [threads, selectedThreadId],
  );

  const filteredThreads = useMemo(() => {
    if (!threadSearch.trim()) return threads;
    const q = threadSearch.trim().toLowerCase();
    return threads.filter((t) => {
      const title = t.title ?? '';
      const preview = t.last_message?.body ?? '';
      return title.toLowerCase().includes(q) || preview.toLowerCase().includes(q);
    });
  }, [threads, threadSearch]);

  const filteredUsers = useMemo(() => {
    if (!userSearch.trim()) return users;
    const q = userSearch.trim().toLowerCase();
    return users.filter(
      (u) =>
        u.full_name.toLowerCase().includes(q) ||
        u.username.toLowerCase().includes(q),
    );
  }, [users, userSearch]);

  const totalUnread = useMemo(
    () => threads.reduce((acc, t) => acc + (t.unread_count ?? 0), 0),
    [threads],
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

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => { void loadThreads(); }, [loadThreads]);

  useEffect(() => {
    if (selectedThreadId) void loadThread(selectedThreadId);
    else setMessages([]);
  }, [selectedThreadId, loadThread]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiService.getUsers({ limit: 200 });
        if (cancelled) return;
        const list = Array.isArray(res?.items) ? res.items : [];
        setUsers(list.filter((u) => u.id !== currentUser?.id));
      } catch {
        if (!cancelled) setUsers([]);
      }
    })();
    return () => { cancelled = true; };
  }, [currentUser?.id]);

  const handleSend = async () => {
    if (!selectedThreadId || sending) return;
    const body = draft.trim();
    if (!body) return;
    // Optimistic: append immediately so user sees the message without a reload flash.
    const optimisticMsg: MessageItem = {
      id: --optimisticIdCounterRef.current, // unique negative id, never collides with server ids
      thread_id: selectedThreadId,
      sender_user_id: currentUser?.id ?? 0,
      body,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);
    setDraft('');
    setSending(true);
    try {
      const sent = await apiService.sendMessage(selectedThreadId, { body });
      // Replace optimistic entry with the real one from the server.
      setMessages((prev) => prev.map((m) => (m.id === optimisticMsg.id ? sent : m)));
      // Refresh thread list (unread counts, last message preview).
      void loadThreads(selectedThreadId);
    } catch (e) {
      // Roll back the optimistic message on failure.
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id));
      setDraft(body);
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
      setUserSearch('');
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

  const senderLabel = (m: MessageItem): string => {
    if (currentUser && m.sender_user_id === currentUser.id) return 'أنت';
    const u = userMap.get(m.sender_user_id);
    return u ? u.full_name : `مستخدم #${m.sender_user_id}`;
  };

  const threadTitle = (t: MessageThread): string => {
    if (t.title) return t.title;
    if (t.thread_type === 'group') return 'محادثة جماعية';
    const other = t.participants?.find((p) => p.user_id !== currentUser?.id);
    if (other) {
      const u = userMap.get(other.user_id);
      if (u) return u.full_name;
      return `مستخدم #${other.user_id}`;
    }
    return `محادثة #${t.id}`;
  };

  const threadSubtitle = (t: MessageThread): string => {
    if (t.thread_type === 'group') {
      return `${t.participants?.length ?? 0} مشاركين`;
    }
    const other = t.participants?.find((p) => p.user_id !== currentUser?.id);
    if (other) {
      const u = userMap.get(other.user_id);
      return u ? (u.role ?? 'موظف') : 'محادثة مباشرة';
    }
    return 'محادثة مباشرة';
  };

  return (
    <Layout>
      <div dir="rtl" className="flex flex-col h-[calc(100vh-120px)] min-h-[600px]">
        {/* Page header */}
        <div className="flex items-center justify-between gap-3 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 shadow">
              <ChatCircleDots size={22} weight="fill" className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground leading-tight">
                مركز التواصل الداخلي
              </h1>
              <p className="text-xs text-muted-foreground">
                قناة تشغيلية آمنة للفرق البلدية
              </p>
            </div>
            {totalUnread > 0 && (
              <Badge
                variant="destructive"
                className="rounded-full px-2 py-0.5 text-xs"
              >
                {totalUnread} غير مقروء
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void loadThreads(selectedThreadId ?? undefined)}
              disabled={loadingThreads}
              className="gap-1.5 text-xs"
            >
              <ArrowClockwise size={14} className={loadingThreads ? 'animate-spin' : ''} />
              تحديث
            </Button>
            <Button
              size="sm"
              onClick={() => setCreateOpen(true)}
              className="gap-1.5 text-xs bg-sky-600 hover:bg-sky-500"
            >
              <Plus size={14} weight="bold" />
              محادثة جديدة
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-3 flex flex-wrap items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <Warning size={16} className="mt-0.5 shrink-0" />
            <span className="flex-1">{error}</span>
            <Button
              variant="outline"
              size="sm"
              className="border-red-300 bg-white text-red-800 hover:bg-red-100"
              onClick={() => {
                if (selectedThreadId) loadThread(selectedThreadId);
                else loadThreads();
              }}
            >
              إعادة المحاولة
            </Button>
          </div>
        )}

        {/* Main layout: thread list + conversation */}
        <div className="flex flex-1 overflow-hidden rounded-xl border border-border shadow-sm">
          {/* ── Thread list panel (hidden on mobile when a thread is selected) ── */}
          <div className={[
            'flex w-full shrink-0 flex-col border-l border-border bg-muted/30 md:w-72',
            mobileShowThread ? 'hidden md:flex' : 'flex',
          ].join(' ')}>
            {/* Search */}
            <div className="border-b border-border p-3">
              <div className="relative">
                <MagnifyingGlass
                  size={14}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  placeholder="بحث في المحادثات..."
                  value={threadSearch}
                  onChange={(e) => setThreadSearch(e.target.value)}
                  className="h-8 pr-8 text-xs"
                />
              </div>
            </div>

            {/* Thread items */}
            <div className="flex-1 overflow-y-auto [scrollbar-width:thin]">
              {loadingThreads ? (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                  <Spinner size={18} className="animate-spin ml-2" />
                  <span className="text-xs">جاري التحميل...</span>
                </div>
              ) : filteredThreads.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground px-4 text-center">
                  <ChatCircleDots size={32} className="mb-2 opacity-30" />
                  <p className="text-xs">
                    {threadSearch
                      ? 'لا توجد نتائج للبحث.'
                      : 'لا توجد محادثات بعد. أنشئ محادثة جديدة للبدء.'}
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {filteredThreads.map((t) => {
                    const isActive = t.id === selectedThreadId;
                    const hasUnread = (t.unread_count ?? 0) > 0;
                    return (
                      <li key={t.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedThreadId(t.id);
                            setMobileShowThread(true);
                          }}
                          className={`w-full px-3 py-3 text-right transition-colors ${
                            isActive
                              ? 'bg-sky-500/10 border-r-2 border-sky-500'
                              : 'hover:bg-muted/60 border-r-2 border-transparent'
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <div className="mt-0.5">
                              {t.thread_type === 'group' ? (
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                                  <UsersThree size={16} />
                                </div>
                              ) : (
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-100 text-sky-600">
                                  <ChatTeardropDots size={16} />
                                </div>
                              )}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between gap-1">
                                <span
                                  className={`truncate text-xs font-semibold ${
                                    isActive ? 'text-sky-700' : 'text-foreground'
                                  }`}
                                >
                                  {threadTitle(t)}
                                </span>
                                <div className="flex shrink-0 items-center gap-1">
                                  {hasUnread && (
                                    <span className="inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
                                      {(t.unread_count ?? 0) > 99 ? '99+' : t.unread_count}
                                    </span>
                                  )}
                                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                                    {fmtRelative(t.last_message?.created_at || t.updated_at)}
                                  </span>
                                </div>
                              </div>
                              <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                                {threadSubtitle(t)}
                              </p>
                              <p
                                className={`mt-0.5 truncate text-[11px] ${
                                  hasUnread ? 'font-medium text-foreground' : 'text-muted-foreground'
                                }`}
                              >
                                {t.last_message?.body || 'لا توجد رسائل بعد'}
                              </p>
                            </div>
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>

          {/* ── Conversation panel (full-width on mobile when a thread is selected) ── */}
          <div className={[
            'flex flex-col overflow-hidden bg-background',
            mobileShowThread ? 'w-full' : 'hidden md:flex md:flex-1',
          ].join(' ')}>
            {selectedThread ? (
              <>
                {/* Thread header */}
                <div className="flex items-center gap-3 border-b border-border px-4 py-3">
                  {/* Mobile: back button */}
                  <button
                    type="button"
                    onClick={() => setMobileShowThread(false)}
                    className="md:hidden flex h-8 w-8 shrink-0 items-center justify-center rounded-full hover:bg-muted transition-colors"
                    title="رجوع"
                  >
                    <ArrowClockwise size={16} className="rotate-180" />
                  </button>
                  <div>
                    {selectedThread.thread_type === 'group' ? (
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                        <UsersThree size={18} />
                      </div>
                    ) : (
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sky-100 text-sky-600">
                        <ChatTeardropDots size={18} />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-sm font-semibold truncate">
                      {threadTitle(selectedThread)}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {selectedThread.participants?.length ?? 0} مشاركين ·{' '}
                      {selectedThread.thread_type === 'group' ? 'محادثة جماعية' : 'محادثة مباشرة'} ·{' '}
                      آخر نشاط: {fmtDateTime(selectedThread.updated_at)}
                    </p>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 [scrollbar-width:thin]">
                  {loadingMessages ? (
                    <div className="flex items-center justify-center py-12 text-muted-foreground">
                      <Spinner size={20} className="animate-spin ml-2" />
                      <span className="text-sm">جاري التحميل...</span>
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                      <ChatCircleDots size={40} className="mb-3 opacity-20" />
                      <p className="text-sm font-medium">لا توجد رسائل بعد</p>
                      <p className="text-xs mt-1">ابدأ المحادثة بكتابة رسالة أدناه.</p>
                    </div>
                  ) : (
                    <>
                      {messages.map((m, idx) => {
                        const isMine = currentUser && m.sender_user_id === currentUser.id;
                        const label = senderLabel(m);
                        const prevMsg = idx > 0 ? messages[idx - 1] : null;
                        const showSender =
                          !prevMsg || prevMsg.sender_user_id !== m.sender_user_id;

                        return (
                          <div
                            key={m.id}
                            className={`flex gap-2 ${isMine ? 'flex-row-reverse' : 'flex-row'}`}
                          >
                            {showSender && (
                              <AvatarIcon name={label} mine={!!isMine} />
                            )}
                            {!showSender && <div className="w-8 shrink-0" />}
                            <div
                              className={`max-w-[70%] space-y-1 ${isMine ? 'items-end' : 'items-start'} flex flex-col`}
                            >
                              {showSender && (
                                <div
                                  className={`flex items-baseline gap-2 ${isMine ? 'flex-row-reverse' : 'flex-row'}`}
                                >
                                  <span className="text-xs font-medium text-foreground">
                                    {label}
                                  </span>
                                  <span className="text-[10px] text-muted-foreground">
                                    {fmtDateTime(m.created_at)}
                                  </span>
                                </div>
                              )}
                              <div
                                className={`rounded-2xl px-3.5 py-2.5 text-sm ${
                                  isMine
                                    ? 'rounded-tr-sm bg-sky-600 text-white'
                                    : 'rounded-tl-sm bg-muted text-foreground border border-border'
                                }`}
                              >
                                <p className="whitespace-pre-wrap break-words leading-relaxed">
                                  {m.body}
                                </p>
                              </div>
                              {!showSender && (
                                <span className="text-[10px] text-muted-foreground px-1">
                                  {fmtDateTime(m.created_at)}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                {/* Composer */}
                <div className="border-t border-border p-3">
                  <div className="flex items-end gap-2">
                    <Textarea
                      dir="rtl"
                      rows={2}
                      placeholder="اكتب رسالة... (Enter للإرسال، Shift+Enter لسطر جديد)"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          void handleSend();
                        }
                      }}
                      disabled={sending}
                      className="flex-1 resize-none text-sm min-h-[60px]"
                    />
                    <Button
                      onClick={() => void handleSend()}
                      disabled={sending || !draft.trim()}
                      className="h-[60px] w-12 shrink-0 flex-col gap-1 bg-sky-600 hover:bg-sky-500 p-2"
                    >
                      {sending ? (
                        <Spinner size={16} className="animate-spin" />
                      ) : (
                        <PaperPlaneRight size={18} />
                      )}
                    </Button>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground text-center">
                    هذه القناة محمية ومخصصة للتواصل الداخلي بين موظفي البلدية فقط.
                  </p>
                </div>
              </>
            ) : (
              /* Empty state — no thread selected */
              <div className="flex flex-1 flex-col items-center justify-center text-muted-foreground gap-3">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                  <ChatCircleDots size={32} className="opacity-40" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium">
                    {threads.length === 0
                      ? 'لا توجد محادثات'
                      : 'اختر محادثة للعرض'}
                  </p>
                  <p className="text-xs mt-1 text-muted-foreground">
                    {threads.length === 0
                      ? 'ابدأ بإنشاء محادثة مع أحد زملائك'
                      : 'انقر على محادثة من القائمة للبدء'}
                  </p>
                </div>
                {threads.length === 0 && (
                  <Button
                    size="sm"
                    onClick={() => setCreateOpen(true)}
                    className="gap-2 bg-sky-600 hover:bg-sky-500 mt-2"
                  >
                    <Plus size={14} />
                    محادثة جديدة
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create thread dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent dir="rtl" className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus size={16} className="text-sky-600" />
              محادثة جديدة
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">
                عنوان المحادثة
                <span className="text-muted-foreground font-normal mr-1">(اختياري)</span>
              </label>
              <Input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="مثال: تنسيق فريق المنطقة الشرقية"
              />
            </div>

            <Separator />

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium">
                  المشاركون
                </label>
                {newParticipantIds.length > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {newParticipantIds.length} مختار
                    {newParticipantIds.length === 1 ? ' — مباشرة' : ' — جماعية'}
                  </Badge>
                )}
              </div>
              <div className="relative mb-2">
                <MagnifyingGlass
                  size={14}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="بحث عن مستخدم..."
                  className="pr-8 h-8 text-sm"
                />
              </div>
              {users.length === 0 ? (
                <p className="text-sm text-muted-foreground py-2">
                  لا توجد قائمة مستخدمين متاحة.
                </p>
              ) : (
                <div className="max-h-56 overflow-auto rounded-lg border divide-y">
                  {filteredUsers.map((u) => {
                    const checked = newParticipantIds.includes(u.id);
                    return (
                      <label
                        key={u.id}
                        className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors ${
                          checked ? 'bg-sky-50' : 'hover:bg-muted/40'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleParticipant(u.id)}
                          className="rounded"
                        />
                        <AvatarIcon name={u.full_name} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{u.full_name}</div>
                          <div className="text-xs text-muted-foreground truncate">
                            {u.username} · {u.role ?? '—'}
                          </div>
                        </div>
                        {checked && (
                          <span className="text-[10px] text-sky-600 font-medium shrink-0">✓</span>
                        )}
                      </label>
                    );
                  })}
                  {filteredUsers.length === 0 && (
                    <div className="py-4 text-center text-xs text-muted-foreground">
                      لا توجد نتائج
                    </div>
                  )}
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-2">
                مستخدم واحد = محادثة مباشرة · أكثر من مستخدم = محادثة جماعية
              </p>
            </div>
          </div>
          <DialogFooter className="gap-2 pt-2">
            <Button
              variant="outline"
              onClick={() => { setCreateOpen(false); setUserSearch(''); setNewTitle(''); setNewParticipantIds([]); }}
              disabled={creating}
            >
              إلغاء
            </Button>
            <Button
              onClick={() => void handleCreateThread()}
              disabled={creating || newParticipantIds.length === 0}
              className="gap-2 bg-sky-600 hover:bg-sky-500"
            >
              {creating && <Spinner size={14} className="animate-spin" />}
              إنشاء المحادثة
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

