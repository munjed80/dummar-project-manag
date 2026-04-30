import { useEffect, useMemo, useState } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Spinner, WarningCircle } from '@phosphor-icons/react';

type Thread = any;

export default function InternalMessagesPage() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null);
  const [selectedThread, setSelectedThread] = useState<any | null>(null);
  const [composer, setComposer] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [participants, setParticipants] = useState('');
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [sending, setSending] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const loadThreads = async () => {
    setLoadingThreads(true);
    setError('');
    try {
      const data = await apiService.getMessageThreads();
      const safe = Array.isArray(data) ? data : [];
      setThreads(safe);
      if (!selectedThreadId && safe.length > 0) setSelectedThreadId(safe[0].id);
    } catch (e: any) {
      setError(e?.message || 'تعذر تحميل الرسائل الداخلية');
      setThreads([]);
    } finally { setLoadingThreads(false); }
  };

  useEffect(() => { loadThreads(); }, []);

  useEffect(() => {
    if (!selectedThreadId) { setSelectedThread(null); return; }
    setLoadingThread(true);
    apiService.getMessageThread(selectedThreadId)
      .then((data) => setSelectedThread(data))
      .catch((e: any) => setError(e?.message || 'تعذر تحميل المحادثة'))
      .finally(() => setLoadingThread(false));
  }, [selectedThreadId]);

  const messages = useMemo(() => Array.isArray(selectedThread?.messages) ? selectedThread.messages : [], [selectedThread]);

  const onSend = async () => {
    if (!selectedThreadId || !composer.trim()) return;
    setSending(true);
    setError('');
    try {
      await apiService.sendMessage(selectedThreadId, { body: composer.trim() });
      setComposer('');
      const updated = await apiService.getMessageThread(selectedThreadId);
      setSelectedThread(updated);
      await loadThreads();
    } catch (e: any) { setError(e?.message || 'تعذر إرسال الرسالة'); }
    finally { setSending(false); }
  };

  const onCreateThread = async () => {
    const participantIds = participants.split(',').map((v) => Number(v.trim())).filter((n) => Number.isFinite(n) && n > 0);
    if (participantIds.length === 0) return;
    setCreating(true);
    setError('');
    try {
      const created = await apiService.createMessageThread({ title: newTitle.trim() || undefined, participant_ids: participantIds, is_group: participantIds.length > 1 });
      setNewTitle('');
      setParticipants('');
      await loadThreads();
      if (created?.id) setSelectedThreadId(created.id);
    } catch (e: any) { setError(e?.message || 'تعذر إنشاء المحادثة'); }
    finally { setCreating(false); }
  };

  return (
    <Layout>
      <div dir="rtl" className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>الرسائل الداخلية</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 lg:grid-cols-[320px_1fr]">
            <div className="space-y-3 border rounded-lg p-3 bg-muted/20">
              <h3 className="font-semibold">إنشاء محادثة</h3>
              <Input placeholder="عنوان المحادثة (اختياري)" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
              <Input placeholder="معرّفات المشاركين: 12,24" value={participants} onChange={(e) => setParticipants(e.target.value)} />
              <Button onClick={onCreateThread} disabled={creating}>{creating ? 'جارٍ الإنشاء...' : 'إنشاء محادثة'}</Button>
              <hr />
              <h3 className="font-semibold">قائمة المحادثات</h3>
              {loadingThreads ? <div className="flex justify-center py-4"><Spinner className="animate-spin" /></div> : (
                threads.length === 0 ? <p className="text-sm text-muted-foreground">لا توجد محادثات حالياً.</p> : (
                  <div className="space-y-2">
                    {threads.map((thread) => (
                      <button key={thread.id} type="button" onClick={() => setSelectedThreadId(thread.id)} className={`w-full rounded border p-2 text-right ${selectedThreadId === thread.id ? 'bg-primary/10 border-primary' : 'bg-background'}`}>
                        <p className="font-medium">{thread.title || `محادثة #${thread.id}`}</p>
                        <p className="text-xs text-muted-foreground">{thread.last_message_preview || 'بدون رسائل'}</p>
                      </button>
                    ))}
                  </div>
                )
              )}
            </div>

            <div className="border rounded-lg p-3 space-y-3">
              {!selectedThreadId ? <p className="text-muted-foreground">اختر محادثة من القائمة لعرض التفاصيل.</p> : (
                <>
                  {loadingThread ? <div className="flex justify-center py-8"><Spinner className="animate-spin" /></div> : (
                    <>
                      <h3 className="font-semibold text-lg">{selectedThread?.title || `محادثة #${selectedThreadId}`}</h3>
                      <div className="h-[360px] overflow-auto rounded border bg-muted/20 p-3 space-y-2">
                        {messages.length === 0 ? <p className="text-sm text-muted-foreground">لا توجد رسائل بعد. ابدأ المحادثة الآن.</p> : messages.map((m: any) => (
                          <div key={m.id || `${m.sender_id}-${m.created_at}`} className="rounded bg-background p-2 border">
                            <div className="text-xs text-muted-foreground">{m.sender_name || `مستخدم #${m.sender_id || '-'}`}</div>
                            <div>{m.body || m.content || '-'}</div>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-2">
                        <Textarea value={composer} onChange={(e) => setComposer(e.target.value)} placeholder="اكتب رسالة داخلية..." />
                        <Button onClick={onSend} disabled={sending || !composer.trim()}>{sending ? 'جارٍ الإرسال...' : 'إرسال'}</Button>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          </CardContent>
        </Card>
        {error && <div className="text-destructive text-sm flex items-center gap-2"><WarningCircle size={18} />{error}</div>}
      </div>
    </Layout>
  );
}
