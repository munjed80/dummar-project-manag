import { useEffect, useMemo, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Robot,
  Spinner,
  Warning,
  ChartBar,
  ChatCircleDots,
  ListChecks,
  FileText,
  MapPin,
  CalendarCheck,
  LightbulbFilament,
  Info,
  ArrowClockwise,
  ShieldWarning,
  CheckCircle,
  Link as LinkIcon,
} from '@phosphor-icons/react';
import {
  apiService,
  ApiError,
  type InternalBotIntent,
  type InternalBotResponse,
  type InternalBotRiskLevel,
} from '@/services/api';
import { describeLoadError } from '@/lib/loadError';

// ── Types ────────────────────────────────────────────────────────────────────

type AssistantTab = 'ask' | 'daily' | 'suggest';

interface QuickPrompt {
  intent: InternalBotIntent | undefined;
  question: string;
  label: string;
  icon: typeof ChatCircleDots;
  tab: AssistantTab;
}

// ── Constants ────────────────────────────────────────────────────────────────

const TABS: { id: AssistantTab; label: string; icon: typeof Robot }[] = [
  { id: 'ask', label: 'اسأل النظام', icon: Robot },
  { id: 'daily', label: 'ملخص اليوم', icon: CalendarCheck },
  { id: 'suggest', label: 'اقترح إجراء', icon: LightbulbFilament },
];

const QUICK_PROMPTS: QuickPrompt[] = [
  {
    tab: 'ask',
    intent: 'complaints_summary',
    question: 'أعطني ملخص الشكاوى اليوم',
    label: 'ملخص الشكاوى اليوم',
    icon: ChatCircleDots,
  },
  {
    tab: 'ask',
    intent: 'tasks_summary',
    question: 'ما هي المهام المتأخرة؟',
    label: 'المهام المتأخرة',
    icon: ListChecks,
  },
  {
    tab: 'ask',
    intent: 'contracts_expiring',
    question: 'ما هي العقود التي تقترب من الانتهاء؟',
    label: 'العقود التي تقترب من الانتهاء',
    icon: FileText,
  },
  {
    tab: 'ask',
    intent: undefined,
    question: 'أكثر المناطق ضغطاً من حيث الشكاوى',
    label: 'أكثر المناطق ضغطاً',
    icon: MapPin,
  },
];

const DAILY_PROMPTS: QuickPrompt[] = [
  {
    tab: 'daily',
    intent: 'complaints_summary',
    question: 'أعطني ملخص شامل لنشاط اليوم في الشكاوى',
    label: 'ملخص الشكاوى',
    icon: ChatCircleDots,
  },
  {
    tab: 'daily',
    intent: 'tasks_summary',
    question: 'ما هي إحصائيات المهام لليوم؟',
    label: 'إحصائيات المهام',
    icon: ListChecks,
  },
  {
    tab: 'daily',
    intent: 'contracts_expiring',
    question: 'هل هناك عقود تنتهي خلال الأسبوع القادم؟',
    label: 'تنبيهات العقود',
    icon: FileText,
  },
];

const SUGGEST_PROMPTS: QuickPrompt[] = [
  {
    tab: 'suggest',
    intent: 'tasks_summary',
    question: 'اقترح إجراءات لمعالجة المهام المتأخرة',
    label: 'معالجة التأخير',
    icon: ListChecks,
  },
  {
    tab: 'suggest',
    intent: 'complaints_summary',
    question: 'اقترح أولويات لمعالجة الشكاوى المعلقة',
    label: 'أولويات الشكاوى',
    icon: ChatCircleDots,
  },
  {
    tab: 'suggest',
    intent: 'contracts_expiring',
    question: 'اقترح خطة لتجديد العقود المنتهية قريباً',
    label: 'خطة تجديد العقود',
    icon: FileText,
  },
];

const INTENT_LABELS: Record<InternalBotIntent, string> = {
  complaints_summary: 'ملخص الشكاوى',
  tasks_summary: 'ملخص المهام',
  contracts_expiring: 'العقود المنتهية قريباً',
  context_analysis: 'تحليل سياقي',
};

const RISK_META: Record<InternalBotRiskLevel, { label: string; classes: string }> = {
  low: {
    label: 'منخفض',
    classes: 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300',
  },
  medium: {
    label: 'متوسط',
    classes: 'border-amber-500/30 bg-amber-950/30 text-amber-300',
  },
  high: {
    label: 'مرتفع',
    classes: 'border-red-500/30 bg-red-950/30 text-red-300',
  },
};

const COLUMN_LABELS: Record<string, string> = {
  status: 'الحالة',
  count: 'العدد',
  contract_number: 'رقم العقد',
  title: 'العنوان',
  end_date: 'تاريخ الانتهاء',
  days_until_expiry: 'أيام حتى الانتهاء',
};

// ── Context analysis panel (Phase 3) ─────────────────────────────────────────

function ContextAnalysisPanel({ response }: { response: InternalBotResponse }) {
  const risk = response.risk_level ?? 'low';
  const riskMeta = RISK_META[risk];
  const keyPoints = response.key_points ?? [];
  const actions = response.recommended_actions ?? [];
  const related = response.related_items ?? [];

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="rounded-lg border border-sky-200/30 bg-sky-950/40 p-4">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-sky-300 font-medium text-sm">
            <ChartBar size={16} />
            <span>الخلاصة</span>
          </div>
          <Badge
            variant="secondary"
            className="text-[10px] bg-indigo-900/60 text-indigo-200 border border-indigo-500/30"
          >
            {INTENT_LABELS[response.intent] ?? response.intent}
          </Badge>
        </div>
        <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
          {response.summary}
        </p>
        <p className="text-[11px] text-slate-500 mt-2">توليد: {response.generated_on}</p>
      </div>

      {/* Risk badge */}
      <div className={`flex items-center gap-2 rounded-lg border p-3 text-sm ${riskMeta.classes}`}>
        <ShieldWarning size={18} />
        <span className="font-medium">مستوى المخاطر:</span>
        <span className="font-bold">{riskMeta.label}</span>
      </div>

      {/* Key points */}
      {keyPoints.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 mb-2">النقاط الرئيسية</p>
          <ul className="space-y-1.5 rounded-lg border border-white/10 bg-white/5 p-3">
            {keyPoints.map((kp, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-200">
                <Info size={12} className="mt-0.5 shrink-0 text-sky-400" />
                <span className="leading-relaxed">{kp}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommended actions */}
      {actions.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 mb-2">إجراءات مقترحة</p>
          <ul className="space-y-1.5 rounded-lg border border-emerald-500/20 bg-emerald-950/20 p-3">
            {actions.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-emerald-200">
                <CheckCircle size={12} className="mt-0.5 shrink-0 text-emerald-400" />
                <span className="leading-relaxed">{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Related items */}
      {related.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 mb-2">عناصر مرتبطة</p>
          <div className="space-y-1.5">
            {related.map((item) => (
              <div
                key={`${item.type}-${item.id}`}
                className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200"
              >
                <LinkIcon size={12} className="text-sky-400" />
                <span className="font-medium">{item.label}</span>
                <span className="text-[10px] text-slate-500">#{item.id} · {item.type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Result display ────────────────────────────────────────────────────────────

type BotRow = Record<string, unknown>;

function ResultPanel({ response }: { response: InternalBotResponse }) {
  const columns = useMemo(() => {
    const rows = response.data ?? [];
    if (rows.length === 0) return [] as string[];
    return Object.keys(rows[0]);
  }, [response]);

  const statCards = useMemo(() => {
    const rows = response.data ?? [];
    if (rows.length === 0) return [] as { label: string; count: number }[];
    const isCountTable = rows.every(
      (r) => typeof r === 'object' && r !== null && 'count' in r,
    );
    if (!isCountTable) return [];
    return rows.map((r) => {
      const row = r as BotRow;
      return {
        label: String(row.status ?? '—'),
        count: Number(row.count ?? 0),
      };
    });
  }, [response]);

  const totalCount = useMemo(
    () => statCards.reduce((acc, s) => acc + (Number.isFinite(s.count) ? s.count : 0), 0),
    [statCards],
  );

  return (
    <div className="space-y-4">
      {/* Summary card */}
      <div className="rounded-lg border border-sky-200/30 bg-sky-950/40 p-4">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-sky-300 font-medium text-sm">
            <ChartBar size={16} />
            <span>النتيجة</span>
          </div>
          <Badge
            variant="secondary"
            className="text-[10px] bg-indigo-900/60 text-indigo-200 border border-indigo-500/30"
          >
            {INTENT_LABELS[response.intent] ?? response.intent}
          </Badge>
        </div>
        <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
          {response.summary}
        </p>
        <p className="text-[11px] text-slate-500 mt-2">
          توليد: {response.generated_on}
        </p>
      </div>

      {/* Stat cards */}
      {statCards.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 mb-2">الإحصائيات</p>
          <div className="grid grid-cols-2 gap-2">
            {statCards.map((s) => (
              <div
                key={s.label}
                className="rounded-lg border border-white/10 bg-white/5 p-3"
              >
                <div className="text-[10px] text-slate-400 truncate">{s.label}</div>
                <div className="text-xl font-bold text-white mt-1">{s.count}</div>
              </div>
            ))}
            <div className="rounded-lg border border-sky-500/30 bg-sky-900/30 p-3 col-span-2">
              <div className="text-[10px] text-sky-400">الإجمالي</div>
              <div className="text-xl font-bold text-sky-200 mt-1">{totalCount}</div>
            </div>
          </div>
        </div>
      )}

      {/* Data table */}
      {response.data.length > 0 && columns.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 mb-2">
            التفاصيل ({response.data.length})
          </p>
          <div className="overflow-auto rounded-lg border border-white/10">
            <Table>
              <TableHeader>
                <TableRow className="border-white/10 hover:bg-transparent">
                  {columns.map((c) => (
                    <TableHead
                      key={c}
                      className="text-right text-[11px] text-slate-400 bg-white/5 py-2"
                    >
                      {COLUMN_LABELS[c] ?? c}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {response.data.map((row, idx) => (
                  <TableRow key={idx} className="border-white/5 hover:bg-white/5">
                    {columns.map((c) => (
                      <TableCell key={c} className="text-xs text-slate-300 py-2">
                        {String((row as BotRow)[c] ?? '—')}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {response.data.length === 0 && (
        <div className="text-center py-6 text-sm text-slate-500">
          لا توجد سجلات مطابقة.
        </div>
      )}
    </div>
  );
}

// ── Main drawer component ─────────────────────────────────────────────────────

export interface SmartAssistantContext {
  contextType: 'complaint';
  contextId: number;
  contextTitle?: string;
}

interface SmartAssistantDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /**
   * Optional contextual pointer (Phase 3). When provided, the drawer
   * shows a context banner, swaps in a "حلّل هذه الشكوى" quick prompt
   * and auto-runs the analysis the first time it is opened.
   */
  context?: SmartAssistantContext | null;
}

export function SmartAssistantDrawer({ open, onOpenChange, context }: SmartAssistantDrawerProps) {
  const [activeTab, setActiveTab] = useState<AssistantTab>('ask');
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<InternalBotResponse | null>(null);
  // Track which context we've already auto-run for to avoid re-firing.
  const [autoRanFor, setAutoRanFor] = useState<string | null>(null);

  const runQuery = async (opts: {
    intent?: InternalBotIntent;
    question?: string;
    useContext?: boolean;
  }) => {
    const useContext = opts.useContext && context;
    const q = opts.question?.trim() || question.trim() || undefined;
    const intent = opts.intent;
    if (!useContext && !intent && !q) {
      setError('اكتب سؤالاً أو اختر استعلاماً سريعاً.');
      return;
    }
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const res = await apiService.queryInternalBot(
        useContext
          ? {
              context_type: context!.contextType,
              context_id: context!.contextId,
            }
          : { intent, question: q },
      );
      setResponse(res);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail || e.message || 'تعذّر تنفيذ الاستعلام');
      } else {
        setError(describeLoadError(e, 'المساعد الذكي').message);
      }
    } finally {
      setLoading(false);
    }
  };

  // Auto-run the contextual analysis the first time the drawer is opened
  // for a given context. Re-runnable manually via the quick prompt.
  useEffect(() => {
    if (!open || !context) return;
    const key = `${context.contextType}:${context.contextId}`;
    if (autoRanFor === key) return;
    setAutoRanFor(key);
    void runQuery({ useContext: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, context?.contextType, context?.contextId]);

  const handlePrompt = (p: QuickPrompt) => {
    setQuestion(p.question);
    void runQuery({ intent: p.intent, question: p.question });
  };

  const handleSend = () => {
    void runQuery({ question: question.trim() || undefined });
  };

  const promptsForTab: QuickPrompt[] =
    activeTab === 'daily'
      ? DAILY_PROMPTS
      : activeTab === 'suggest'
        ? SUGGEST_PROMPTS
        : QUICK_PROMPTS;

  const tabDescription: Record<AssistantTab, string> = {
    ask: 'اطرح سؤالاً على النظام أو اختر استعلاماً سريعاً.',
    daily: 'ملخص تلقائي لنشاط اليوم عبر الوحدات.',
    suggest: 'اقترح إجراءات بناءً على الوضع الحالي.',
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        dir="rtl"
        className="flex w-full max-w-md flex-col gap-0 border-l border-white/10 bg-slate-950 p-0 text-slate-100 sm:max-w-md"
      >
        {/* Header */}
        <SheetHeader className="border-b border-white/10 px-5 py-4">
          <SheetTitle className="flex items-center gap-2 text-right text-base text-white">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-sky-600 shadow-lg">
              <Robot size={18} weight="fill" className="text-white" />
            </div>
            مركز القرار الذكي
          </SheetTitle>
          <p className="text-right text-xs text-slate-400 mt-0.5">
            {tabDescription[activeTab]}
          </p>
        </SheetHeader>

        {/* Tabs */}
        <div className="flex border-b border-white/10">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id);
                  setResponse(null);
                  setError(null);
                }}
                className={`flex flex-1 items-center justify-center gap-1.5 border-b-2 px-3 py-3 text-xs font-medium transition-colors ${
                  active
                    ? 'border-sky-400 text-sky-300'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon size={14} weight={active ? 'fill' : 'regular'} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 [scrollbar-width:thin] space-y-4">
          {/* Context banner (Phase 3) */}
          {context && (
            <div className="space-y-2">
              <div className="flex items-start gap-2 rounded-lg border border-sky-500/30 bg-sky-950/30 p-3 text-xs text-sky-200">
                <Info size={14} className="mt-0.5 shrink-0" />
                <span>
                  تحليل مرتبط بالشكوى رقم {context.contextTitle ?? `#${context.contextId}`}
                </span>
              </div>
              <Button
                onClick={() => void runQuery({ useContext: true })}
                disabled={loading}
                size="sm"
                className="w-full gap-2 bg-sky-600 hover:bg-sky-500 text-white font-medium"
              >
                {loading ? (
                  <Spinner size={14} className="animate-spin" />
                ) : (
                  <Robot size={14} />
                )}
                حلّل هذه الشكوى
              </Button>
            </div>
          )}

          {/* Info banner */}
          <div className="flex items-start gap-2 rounded-lg border border-indigo-500/20 bg-indigo-950/30 p-3 text-xs text-indigo-300">
            <Info size={14} className="mt-0.5 shrink-0" />
            <span>النتائج محدودة بصلاحياتك التنظيمية. لا تُشارك هذه البيانات مع أطراف خارجية.</span>
          </div>

          {/* Quick prompts grid */}
          <div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              استعلامات سريعة
            </p>
            <div className="grid grid-cols-2 gap-2">
              {promptsForTab.map((p) => {
                const Icon = p.icon;
                return (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => handlePrompt(p)}
                    disabled={loading}
                    className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-right text-xs text-slate-300 transition-colors hover:border-sky-500/40 hover:bg-sky-950/30 hover:text-sky-200 disabled:opacity-50"
                  >
                    <Icon size={14} className="mt-0.5 shrink-0 text-sky-400" />
                    <span className="leading-tight">{p.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <Separator className="bg-white/10" />

          {/* Free-text question */}
          {activeTab === 'ask' && (
            <div className="space-y-2">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                سؤال مخصص
              </p>
              <Textarea
                dir="rtl"
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="مثال: كم عدد الشكاوى المفتوحة هذا الشهر؟"
                disabled={loading}
                className="resize-none border-white/15 bg-white/5 text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:ring-sky-500/20 text-sm"
              />
              <Button
                onClick={handleSend}
                disabled={loading || !question.trim()}
                className="w-full gap-2 bg-sky-600 hover:bg-sky-500 text-white font-medium"
              >
                {loading ? (
                  <Spinner size={15} className="animate-spin" />
                ) : (
                  <Robot size={15} />
                )}
                {loading ? 'جاري التحليل...' : 'إرسال السؤال'}
              </Button>
            </div>
          )}

          {/* For daily/suggest tabs — show a run-all button */}
          {activeTab !== 'ask' && (
            <Button
              onClick={() => handlePrompt(promptsForTab[0])}
              disabled={loading}
              className="w-full gap-2 bg-sky-600 hover:bg-sky-500 text-white font-medium"
            >
              {loading ? (
                <Spinner size={15} className="animate-spin" />
              ) : (
                <ArrowClockwise size={15} />
              )}
              {loading
                ? 'جاري التحليل...'
                : activeTab === 'daily'
                  ? 'تحديث ملخص اليوم'
                  : 'توليد اقتراحات'}
            </Button>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-950/30 p-3 text-xs text-red-300">
              <Warning size={14} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div className="space-y-3 animate-pulse">
              <div className="h-24 rounded-lg bg-white/5" />
              <div className="grid grid-cols-2 gap-2">
                <div className="h-16 rounded-lg bg-white/5" />
                <div className="h-16 rounded-lg bg-white/5" />
              </div>
            </div>
          )}

          {/* Results */}
          {!loading && response && (
            response.intent === 'context_analysis'
              ? <ContextAnalysisPanel response={response} />
              : <ResultPanel response={response} />
          )}

          {/* Empty state */}
          {!loading && !response && !error && (
            <div className="flex flex-col items-center justify-center py-10 text-slate-600">
              <Robot size={40} className="mb-3 opacity-30" />
              <p className="text-xs text-center">
                اختر استعلاماً سريعاً أو اكتب سؤالاً للحصول على النتائج.
              </p>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default SmartAssistantDrawer;
