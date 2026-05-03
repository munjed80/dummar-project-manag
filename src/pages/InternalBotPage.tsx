import { useMemo, useState } from 'react';
import { Layout } from '@/components/Layout';
import {
  apiService,
  ApiError,
  type InternalBotIntent,
  type InternalBotResponse,
} from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Robot, Spinner, Warning, Info, ChartBar, ChatCircleDots, ListChecks, FileText,
} from '@phosphor-icons/react';
import { describeLoadError } from '@/lib/loadError';

const INTENT_LABELS: Record<InternalBotIntent, string> = {
  complaints_summary: 'ملخص الشكاوى',
  tasks_summary: 'ملخص المهام',
  contracts_expiring: 'العقود التي تقترب من الانتهاء',
};

const COLUMN_LABELS: Record<string, string> = {
  status: 'الحالة',
  count: 'العدد',
  contract_number: 'رقم العقد',
  title: 'العنوان',
  end_date: 'تاريخ الانتهاء',
};

interface Preset {
  intent: InternalBotIntent;
  label: string;
  question: string;
  icon: typeof ChatCircleDots;
}

const PRESETS: Preset[] = [
  {
    intent: 'complaints_summary',
    label: 'ملخص الشكاوى',
    question: 'أعطني ملخص الشكاوى لآخر فترة',
    icon: ChatCircleDots,
  },
  {
    intent: 'tasks_summary',
    label: 'ملخص المهام',
    question: 'أعطني ملخص المهام لآخر فترة',
    icon: ListChecks,
  },
  {
    intent: 'contracts_expiring',
    label: 'العقود التي تقترب من الانتهاء',
    question: 'ما هي العقود التي ستنتهي قريباً؟',
    icon: FileText,
  },
];

export default function InternalBotPage() {
  const [question, setQuestion] = useState('');
  const [intent, setIntent] = useState<InternalBotIntent | ''>('');
  const [days, setDays] = useState<string>('30');
  const [limit, setLimit] = useState<string>('10');
  const [locationId, setLocationId] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<InternalBotResponse | null>(null);

  const runQuery = async (override?: { intent?: InternalBotIntent; question?: string }) => {
    const effectiveIntent = override?.intent ?? (intent || undefined);
    const effectiveQuestion = override?.question ?? (question.trim() || undefined);

    if (!effectiveIntent && !effectiveQuestion) {
      setError('اختر نية أو اكتب سؤالاً قبل الإرسال.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const parsedDays = days === '' ? undefined : Number(days);
      const parsedLimit = limit === '' ? undefined : Number(limit);
      const parsedLocation = locationId === '' ? undefined : Number(locationId);
      const parsedProject = projectId === '' ? undefined : Number(projectId);
      const res = await apiService.queryInternalBot({
        intent: effectiveIntent,
        question: effectiveQuestion,
        days: Number.isFinite(parsedDays) ? parsedDays : undefined,
        limit: Number.isFinite(parsedLimit) ? parsedLimit : undefined,
        location_id: Number.isFinite(parsedLocation) ? parsedLocation : undefined,
        project_id: Number.isFinite(parsedProject) ? parsedProject : undefined,
      });
      setResponse(res);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail || e.message || 'تعذّر تنفيذ الاستعلام');
      } else {
        setError(describeLoadError(e, 'نتيجة المساعد').message);
      }
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const handlePreset = (preset: Preset) => {
    if (loading) return;
    setIntent(preset.intent);
    setQuestion(preset.question);
    void runQuery({ intent: preset.intent, question: preset.question });
  };

  // Derive column order from the first row, with sensible fallbacks per intent.
  const columns = useMemo(() => {
    const rows = response?.data ?? [];
    if (rows.length === 0) return [] as string[];
    return Object.keys(rows[0]);
  }, [response]);

  // For "summary" intents, the rows are { status, count } — surface as
  // dashboard-style stat cards in addition to the raw table.
  const statCards = useMemo(() => {
    if (!response) return [] as { label: string; count: number }[];
    const rows = response.data ?? [];
    if (rows.length === 0) return [];
    const isCountTable = rows.every(
      (r) => typeof r === 'object' && r !== null && 'count' in r,
    );
    if (!isCountTable) return [];
    return rows.map((r) => ({
      label: String((r as Record<string, unknown>).status ?? '—'),
      count: Number((r as Record<string, unknown>).count ?? 0),
    }));
  }, [response]);

  const totalCount = useMemo(
    () => statCards.reduce((acc, s) => acc + (Number.isFinite(s.count) ? s.count : 0), 0),
    [statCards],
  );

  return (
    <Layout>
      <div dir="rtl" className="p-4 md:p-6 space-y-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Robot size={24} className="text-primary" />
            المساعد الذكي
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            أداة دعم قرار داخلية للموظفين الإداريين — وليست بوت دردشة عام.
            استخدمها للحصول على ملخصات سريعة عن الشكاوى والمهام والعقود.
          </p>
        </div>

        <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          <Info size={18} className="mt-0.5 shrink-0" />
          <span>
            النتائج محدودة بصلاحياتك التنظيمية ومجال إشرافك. لا يتم مشاركة هذه
            البيانات مع أي طرف خارجي.
          </span>
        </div>

        {/* Query form */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">طرح سؤال</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-sm font-medium block mb-1">السؤال</label>
              <Textarea
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="مثال: كم عدد الشكاوى المفتوحة هذا الشهر؟"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
              <div>
                <label className="text-xs font-medium block mb-1">النية</label>
                <Select
                  value={intent || 'auto'}
                  onValueChange={(v) => setIntent(v === 'auto' ? '' : (v as InternalBotIntent))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="استنتاج تلقائي" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">استنتاج تلقائي من السؤال</SelectItem>
                    <SelectItem value="complaints_summary">ملخص الشكاوى</SelectItem>
                    <SelectItem value="tasks_summary">ملخص المهام</SelectItem>
                    <SelectItem value="contracts_expiring">العقود المنتهية قريباً</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-medium block mb-1">عدد الأيام</label>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium block mb-1">حد النتائج</label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium block mb-1">رقم الموقع (اختياري)</label>
                <Input
                  type="number"
                  min={1}
                  value={locationId}
                  onChange={(e) => setLocationId(e.target.value)}
                  placeholder="—"
                />
              </div>
              <div>
                <label className="text-xs font-medium block mb-1">رقم المشروع (اختياري)</label>
                <Input
                  type="number"
                  min={1}
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  placeholder="—"
                />
              </div>
            </div>

            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex flex-wrap gap-2">
                <span className="text-xs font-medium self-center text-muted-foreground">
                  استعلامات سريعة:
                </span>
                {PRESETS.map((p) => {
                  const Icon = p.icon;
                  return (
                    <Button
                      key={p.intent}
                      variant="outline"
                      size="sm"
                      onClick={() => handlePreset(p)}
                      disabled={loading}
                      className="gap-1"
                    >
                      <Icon size={14} />
                      {p.label}
                    </Button>
                  );
                })}
              </div>
              <Button onClick={() => runQuery()} disabled={loading} className="gap-2">
                {loading ? <Spinner size={16} className="animate-spin" /> : <Robot size={16} />}
                {loading ? 'جاري التحليل...' : 'إرسال السؤال'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <Warning size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Results */}
        {response ? (
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2 justify-between">
                  <span className="flex items-center gap-2">
                    <ChartBar size={18} className="text-primary" />
                    النتائج
                  </span>
                  <Badge variant="secondary">{INTENT_LABELS[response.intent] ?? response.intent}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{response.summary}</p>
                <p className="text-xs text-muted-foreground">
                  تاريخ التوليد: {response.generated_on}
                </p>
              </CardContent>
            </Card>

            {statCards.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">إحصائيات</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                    {statCards.map((s) => (
                      <div
                        key={s.label}
                        className="border rounded-md p-3 bg-muted/20"
                      >
                        <div className="text-xs text-muted-foreground">{s.label}</div>
                        <div className="text-2xl font-bold mt-1">{s.count}</div>
                      </div>
                    ))}
                    <div className="border rounded-md p-3 bg-primary/10 border-primary/30">
                      <div className="text-xs text-muted-foreground">الإجمالي</div>
                      <div className="text-2xl font-bold mt-1">{totalCount}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  البيانات التفصيلية ({response.data.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {response.data.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    لا توجد سجلات مطابقة لهذا الاستعلام.
                  </p>
                ) : (
                  <div className="overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {columns.map((c) => (
                            <TableHead key={c} className="text-right">
                              {COLUMN_LABELS[c] ?? c}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {response.data.map((row, idx) => (
                          <TableRow key={idx}>
                            {columns.map((c) => (
                              <TableCell key={c}>
                                {String((row as Record<string, unknown>)[c] ?? '—')}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ) : (
          !loading && (
            <Card>
              <CardContent className="py-10 text-center text-sm text-muted-foreground">
                <Robot size={36} className="mx-auto mb-2 opacity-40" />
                لا توجد نتائج بعد. اختر استعلاماً سريعاً أو اكتب سؤالاً ثم اضغط
                "إرسال السؤال".
              </CardContent>
            </Card>
          )
        )}
      </div>
    </Layout>
  );
}
