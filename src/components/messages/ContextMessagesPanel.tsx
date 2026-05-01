import { useCallback, useEffect, useRef, useState } from 'react';
import {
  apiService,
  ApiError,
  type MessageContextType,
  type MessageItem,
  type MessageThread,
} from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  ChatCircleDots,
  PaperPlaneRight,
  Spinner,
  Warning,
} from '@phosphor-icons/react';
import { describeLoadError } from '@/lib/loadError';
import { toast } from 'sonner';

interface ContextMessagesPanelProps {
  contextType: MessageContextType;
  contextId: number;
  contextTitle?: string;
}

function fmtTime(value?: string | null): string {
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

/**
 * Phase-2 contextual messages panel — shown inside an entity detail page
 * (currently only ComplaintDetailsPage). It loads or creates the linked
 * thread on mount and provides a minimal compose/send UI.
 */
export function ContextMessagesPanel({
  contextType,
  contextId,
  contextTitle,
}: ContextMessagesPanelProps) {
  const { user: currentUser } = useAuth();
  const [thread, setThread] = useState<MessageThread | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadThread = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const t = await apiService.getOrCreateContextThread(
        contextType,
        contextId,
        contextTitle,
      );
      setThread(t);
      const detail = await apiService.getMessageThread(t.id);
      setMessages(Array.isArray(detail?.messages) ? detail.messages : []);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail || e.message || 'تعذّر تحميل النقاش');
      } else {
        setError(describeLoadError(e, 'النقاش الداخلي').message);
      }
      setThread(null);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [contextType, contextId, contextTitle]);

  useEffect(() => { void loadThread(); }, [loadThread]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!thread) return;
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    try {
      const sent = await apiService.sendMessage(thread.id, { body });
      setMessages((prev) => [...prev, sent]);
      setDraft('');
    } catch (e) {
      const msg = e instanceof ApiError ? (e.detail || e.message) : 'تعذّر إرسال الرسالة';
      toast.error(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <Card dir="rtl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ChatCircleDots size={20} />
          النقاش الداخلي
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading && (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Spinner size={18} className="animate-spin ml-2" />
            <span className="text-sm">جاري تحميل النقاش...</span>
          </div>
        )}

        {!loading && error && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <Warning size={16} className="mt-0.5 shrink-0" />
            <div className="flex-1">
              <p>{error}</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2"
                onClick={() => void loadThread()}
              >
                إعادة المحاولة
              </Button>
            </div>
          </div>
        )}

        {!loading && !error && thread && (
          <>
            <div className="max-h-80 overflow-y-auto space-y-2 rounded-md border border-border bg-muted/30 p-3 [scrollbar-width:thin]">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <ChatCircleDots size={32} className="mb-2 opacity-30" />
                  <p className="text-sm">لا توجد رسائل بعد. ابدأ النقاش أدناه.</p>
                </div>
              ) : (
                <>
                  {messages.map((m) => {
                    const isMine = currentUser && m.sender_user_id === currentUser.id;
                    return (
                      <div
                        key={m.id}
                        className={`flex ${isMine ? 'justify-start' : 'justify-end'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                            isMine
                              ? 'bg-sky-600 text-white'
                              : 'bg-background text-foreground border border-border'
                          }`}
                        >
                          <p className="whitespace-pre-wrap break-words leading-relaxed">
                            {m.body}
                          </p>
                          <p
                            className={`mt-1 text-[10px] ${
                              isMine ? 'text-sky-100' : 'text-muted-foreground'
                            }`}
                          >
                            {fmtTime(m.created_at)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

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
                className="flex-1 resize-none text-sm min-h-[56px]"
              />
              <Button
                onClick={() => void handleSend()}
                disabled={sending || !draft.trim()}
                className="h-[56px] w-12 shrink-0 bg-sky-600 hover:bg-sky-500 p-2"
              >
                {sending ? (
                  <Spinner size={16} className="animate-spin" />
                ) : (
                  <PaperPlaneRight size={18} />
                )}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default ContextMessagesPanel;
