import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { SmartAssistantDrawer } from '@/components/SmartAssistantDrawer';
import { apiService } from '@/services/api';
import {
  ChatCircleDots,
  ListChecks,
  FileText,
  Bell,
  ChatsCircle,
  Robot,
  ArrowLeft,
  ClockCounterClockwise,
  ChartBar,
  ShieldCheck,
  Lightbulb,
  Files,
  Gavel,
  PaperPlaneTilt,
  Users,
} from '@phosphor-icons/react';

type IconType = typeof ChatCircleDots;

// ── Types ────────────────────────────────────────────────────────────────────

interface DashboardStats {
  total_complaints?: number;
  total_tasks?: number;
  total_contracts?: number;
  active_contracts?: number;
  contracts_nearing_expiry?: number;
  investment_contracts_expired?: number;
  investment_contracts_within_30?: number;
  investment_contracts_within_60?: number;
  investment_contracts_within_90?: number;
  complaints_by_status?: Record<string, number>;
  tasks_by_status?: Record<string, number>;
}

interface KpiCardSpec {
  label: string;
  value: number | null;
  hint: string;
  icon: IconType;
  href?: string;
  tone: 'sky' | 'indigo' | 'emerald' | 'amber' | 'rose' | 'violet';
}

const TONE_CLASSES: Record<KpiCardSpec['tone'], { ring: string; bg: string; text: string; icon: string }> = {
  sky:     { ring: 'border-sky-200',     bg: 'bg-sky-50',     text: 'text-sky-900',     icon: 'text-sky-600' },
  indigo:  { ring: 'border-indigo-200',  bg: 'bg-indigo-50',  text: 'text-indigo-900',  icon: 'text-indigo-600' },
  emerald: { ring: 'border-emerald-200', bg: 'bg-emerald-50', text: 'text-emerald-900', icon: 'text-emerald-600' },
  amber:   { ring: 'border-amber-200',   bg: 'bg-amber-50',   text: 'text-amber-900',   icon: 'text-amber-600' },
  rose:    { ring: 'border-rose-200',    bg: 'bg-rose-50',    text: 'text-rose-900',    icon: 'text-rose-600' },
  violet:  { ring: 'border-violet-200',  bg: 'bg-violet-50',  text: 'text-violet-900',  icon: 'text-violet-600' },
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ExecutiveBriefingPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(false);
  const [unreadMessages, setUnreadMessages] = useState<number | null>(null);
  const [assistantOpen, setAssistantOpen] = useState(false);

  // Fetch dashboard stats — graceful empty state on failure, never crashes.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await apiService.getDashboardStats();
        if (alive) setStats(data ?? {});
      } catch {
        if (alive) setStatsError(true);
      } finally {
        if (alive) setStatsLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Best-effort unread internal-message count. Endpoint may not be available
  // for every role — fall back silently.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const threads = await apiService.getMessageThreads({ limit: 50 });
        if (!alive || !Array.isArray(threads)) return;
        const total = threads.reduce(
          (acc, t) => acc + (t.unread_count ?? 0),
          0,
        );
        setUnreadMessages(total);
      } catch {
        // leave as null → empty state
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // ── KPI specs (graceful nulls when data missing) ────────────────────
  const overdueComplaintsCount =
    (stats?.complaints_by_status?.under_review ?? 0) +
    (stats?.complaints_by_status?.assigned ?? 0);
  const followupTasksCount =
    (stats?.tasks_by_status?.pending ?? 0) +
    (stats?.tasks_by_status?.assigned ?? 0);
  const expiringContractsCount =
    (stats?.contracts_nearing_expiry ?? 0) +
    (stats?.investment_contracts_within_30 ?? 0) +
    (stats?.investment_contracts_expired ?? 0);

  const kpiCards: KpiCardSpec[] = [
    { label: 'الشكاوى',         value: stats?.total_complaints ?? null, hint: 'إجمالي الشكاوى المسجّلة',         icon: ChatCircleDots, href: '/complaints',          tone: 'sky' },
    { label: 'المهام',          value: stats?.total_tasks ?? null,      hint: 'إجمالي المهام التنفيذية',         icon: ListChecks,     href: '/tasks',               tone: 'indigo' },
    { label: 'العقود',          value: stats?.total_contracts ?? null,  hint: `النشطة: ${stats?.active_contracts ?? 0}`, icon: FileText,    href: '/manual-contracts',    tone: 'emerald' },
    { label: 'المتأخرات',       value: overdueComplaintsCount || null,   hint: 'شكاوى قيد المراجعة أو معيّنة',     icon: ClockCounterClockwise, href: '/complaints', tone: 'amber' },
    { label: 'التنبيهات',       value: expiringContractsCount || null,   hint: 'عقود تقترب من الانتهاء',           icon: Bell,           href: '/contracts',           tone: 'rose' },
    { label: 'الرسائل الداخلية', value: unreadMessages ?? null,           hint: 'رسائل غير مقروءة',                icon: ChatsCircle,    href: '/messages',            tone: 'violet' },
  ];

  // ── Priority focus areas ────────────────────────────────────────────
  const priorityCards: { title: string; count: number | null; href: string; icon: IconType; description: string }[] = [
    {
      title: 'الشكاوى المتأخرة',
      count: overdueComplaintsCount || null,
      href: '/complaints',
      icon: ChatCircleDots,
      description: 'شكاوى لم تُحسم بعد وبحاجة إلى متابعة',
    },
    {
      title: 'المهام التي تحتاج متابعة',
      count: followupTasksCount || null,
      href: '/tasks',
      icon: ListChecks,
      description: 'مهام معلّقة أو بانتظار التنفيذ',
    },
    {
      title: 'العقود التي تقترب من الانتهاء',
      count: expiringContractsCount || null,
      href: '/contracts',
      icon: FileText,
      description: 'عقود تشغيلية واستثمارية بحاجة إلى قرار تجديد',
    },
    {
      title: 'الملفات التي تحتاج قراراً إدارياً',
      // TODO: replace with a real KPI once a dedicated endpoint exists.
      count: null,
      href: '/messages',
      icon: Files,
      description: 'ملفات مرفوعة للنقاش الداخلي بانتظار قرار',
    },
  ];

  // ── Presentation storyline ──────────────────────────────────────────
  const storySteps: { title: string; description: string; href?: string; icon: IconType }[] = [
    { title: '١. استقبال الشكوى',                  description: 'يستقبل النظام الشكاوى من المواطنين والقنوات الميدانية ويصنّفها فوراً.', href: '/complaints',        icon: ChatCircleDots },
    { title: '٢. تحويلها إلى مهمة',                description: 'يتم تحويل الشكوى المؤهَّلة إلى مهمة تنفيذية موثّقة بضغطة واحدة.',           href: '/tasks',             icon: ListChecks },
    { title: '٣. إسنادها إلى فريق تنفيذي',         description: 'تُسنَد المهمة إلى الفريق المختص مع تواريخ ومسؤوليات واضحة.',                href: '/teams',             icon: Users },
    { title: '٤. متابعة النقاش الداخلي',           description: 'يجري النقاش بين الفرق داخل النظام، مرتبطاً بالشكوى مباشرةً.',                href: '/messages',          icon: ChatsCircle },
    { title: '٥. تحليل الشكوى بالمساعد الذكي',      description: 'يقدّم المساعد الذكي خلاصة وقائمة مخاطر وإجراءات مقترحة لكل شكوى.',           icon: Robot },
    { title: '٦. متابعة العقود والتنبيهات',         description: 'متابعة العقود التشغيلية والاستثمارية وتنبيه قبل الانتهاء بمدّة كافية.',       href: '/manual-contracts',  icon: FileText },
    { title: '٧. إصدار تقارير وقرارات أسرع',        description: 'تقارير لحظية تُمكِّن القيادة من اتخاذ قرارات مبنيّة على بيانات.',              href: '/reports',           icon: ChartBar },
  ];

  // ── Decision-support cards ──────────────────────────────────────────
  const decisionSupportCards: { title: string; description: string; icon: IconType }[] = [
    { title: 'كشف التأخير',                              description: 'تنبيهات تلقائية على الشكاوى والمهام التي تجاوزت المدة المعتادة.',          icon: ClockCounterClockwise },
    { title: 'تحديد المسؤولية',                          description: 'كل إجراء موثّق باسم المستخدم والوقت — لا مجال للالتباس.',                   icon: ShieldCheck },
    { title: 'توثيق النقاش الداخلي',                     description: 'كل نقاش بين الفرق محفوظ ومرتبط بالشكوى أو الملف ذي الصلة.',                icon: ChatsCircle },
    { title: 'تحليل الشكاوى',                            description: 'تحليل سياقي بقواعد واضحة يصنّف المخاطر ويقترح الإجراءات.',                  icon: Lightbulb },
    { title: 'متابعة العقود',                            description: 'لوحة موحّدة للعقود مع تنبيهات قبل الانتهاء وتجديد منظَّم.',                  icon: FileText },
    { title: 'تقليل الاعتماد على الاتصالات الورقية والشفوية', description: 'كل قرار وكل متابعة تتم داخل النظام، وتُحفظ للرجوع إليها لاحقاً.',         icon: Gavel },
  ];

  return (
    <Layout>
      <div className="space-y-8">
        {/* ── 1. Executive hero ───────────────────────────────── */}
        <section className="relative overflow-hidden rounded-2xl border border-sky-200 bg-gradient-to-bl from-sky-50 via-white to-indigo-50 p-6 md:p-8 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
            <div className="space-y-3 max-w-3xl">
              <Badge className="bg-indigo-600 hover:bg-indigo-600 text-white">
                نسخة عرض تنفيذية
              </Badge>
              <h1 className="text-3xl md:text-4xl font-bold text-slate-900 leading-tight">
                موجز المحافظ
              </h1>
              <p className="text-slate-700 leading-relaxed text-sm md:text-base">
                منصّة موحّدة تحوّل الشكاوى والمهام والعقود والقرارات الداخلية إلى نظام تشغيل رقمي
                للمحافظة، يتيح للقيادة متابعة الأداء واتخاذ القرار في الوقت المناسب — بدل الاعتماد
                على الاتصالات الورقية والشفوية.
              </p>
              <div className="flex flex-wrap gap-2 pt-2">
                <Button onClick={() => setAssistantOpen(true)} className="gap-2 bg-indigo-600 hover:bg-indigo-500 text-white">
                  <Robot size={18} />
                  افتح المساعد الذكي
                </Button>
                <Button asChild variant="outline" className="gap-2">
                  <Link to="/dashboard">
                    <ChartBar size={18} />
                    لوحة القيادة
                    <ArrowLeft size={14} />
                  </Link>
                </Button>
                <Button asChild variant="outline" className="gap-2">
                  <Link to="/reports">
                    <FileText size={18} />
                    التقارير
                    <ArrowLeft size={14} />
                  </Link>
                </Button>
              </div>
            </div>
            <div className="hidden md:flex items-center justify-center rounded-2xl bg-white/70 p-6 border border-white">
              <PaperPlaneTilt size={72} weight="duotone" className="text-indigo-600" />
            </div>
          </div>
        </section>

        {/* ── 2. KPI cards ─────────────────────────────────────── */}
        <section>
          <SectionHeader title="مؤشرات عامة" subtitle="نظرة سريعة على حجم النشاط الحالي" />
          {statsError && !stats && (
            <Card className="mb-3 border-amber-300 bg-amber-50">
              <CardContent className="py-3 text-sm text-amber-900">
                تعذّر تحميل المؤشرات في الوقت الحالي. سيتم عرض الحالات الفارغة.
              </CardContent>
            </Card>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {kpiCards.map((kpi) => (
              <KpiCard key={kpi.label} kpi={kpi} loading={statsLoading} />
            ))}
          </div>
        </section>

        {/* ── 3. Priority focus areas ──────────────────────────── */}
        <section>
          <SectionHeader title="أولويات العمل الحالية" subtitle="المجالات التي تحتاج إلى متابعة قيادية" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {priorityCards.map((card) => (
              <PriorityCard key={card.title} card={card} loading={statsLoading} />
            ))}
          </div>
        </section>

        {/* ── 4. Presentation storyline ────────────────────────── */}
        <section>
          <SectionHeader title="قصة العرض في 7 خطوات" subtitle="مسار توضيحي لكيفية عمل النظام من البلاغ إلى القرار" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {storySteps.map((step) => (
              <Card key={step.title} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2 text-slate-800">
                    <step.icon size={20} className="text-indigo-600 shrink-0" />
                    {step.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 space-y-3">
                  <p className="text-xs text-slate-600 leading-relaxed">{step.description}</p>
                  {step.href ? (
                    <Button asChild size="sm" variant="outline" className="w-full gap-2">
                      <Link to={step.href}>
                        فتح الصفحة
                        <ArrowLeft size={14} />
                      </Link>
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="w-full gap-2"
                      onClick={() => setAssistantOpen(true)}
                    >
                      <Robot size={14} />
                      تجربة المساعد الذكي
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* ── 5. Decision-support section ──────────────────────── */}
        <section>
          <SectionHeader title="كيف يساعد النظام في القرار؟" subtitle="ست قدرات أساسية تدعم اتخاذ القرار اليومي" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {decisionSupportCards.map((card) => (
              <Card key={card.title} className="border-slate-200">
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <card.icon size={20} className="text-emerald-600 shrink-0" />
                    <h3 className="font-semibold text-sm text-slate-800">{card.title}</h3>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{card.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <Separator />

        {/* ── 6. Assistant CTA footer ──────────────────────────── */}
        <section className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-5 text-center">
          <Robot size={32} className="mx-auto text-indigo-600 mb-2" />
          <h2 className="text-lg font-semibold text-slate-900 mb-1">جرّب المساعد الذكي مباشرةً</h2>
          <p className="text-sm text-slate-600 mb-4">
            احصل على ملخّص قراري لأي شكوى أو سؤال تشغيلي بضغطة زر — دون أي اتصال خارجي.
          </p>
          <Button onClick={() => setAssistantOpen(true)} className="gap-2 bg-indigo-600 hover:bg-indigo-500 text-white">
            <Robot size={18} />
            افتح المساعد الذكي
          </Button>
        </section>
      </div>

      <SmartAssistantDrawer open={assistantOpen} onOpenChange={setAssistantOpen} />
    </Layout>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-xl font-bold text-slate-900">{title}</h2>
      {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function KpiCard({ kpi, loading }: { kpi: KpiCardSpec; loading: boolean }) {
  const tone = TONE_CLASSES[kpi.tone];
  const Icon = kpi.icon;
  const hasValue = kpi.value !== null && kpi.value !== undefined;
  const body = (
    <Card className={`border ${tone.ring} ${tone.bg} h-full`}>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className={`text-xs font-medium ${tone.text}`}>{kpi.label}</span>
          <Icon size={18} className={tone.icon} />
        </div>
        {loading ? (
          <div className="h-7 w-14 rounded bg-slate-200 animate-pulse" />
        ) : hasValue ? (
          <div className={`text-2xl font-bold ${tone.text}`}>{kpi.value}</div>
        ) : (
          <div className="text-sm text-slate-500">لا توجد بيانات حالياً</div>
        )}
        <p className="text-[11px] text-slate-500 truncate">{kpi.hint}</p>
      </CardContent>
    </Card>
  );
  return kpi.href ? <Link to={kpi.href} className="block">{body}</Link> : body;
}

function PriorityCard({
  card,
  loading,
}: {
  card: { title: string; count: number | null; href: string; icon: IconType; description: string };
  loading: boolean;
}) {
  const Icon = card.icon;
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4 flex items-start gap-3">
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-2.5 shrink-0">
          <Icon size={22} className="text-amber-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="font-semibold text-sm text-slate-800">{card.title}</h3>
            {loading ? (
              <div className="h-5 w-10 rounded bg-slate-200 animate-pulse" />
            ) : card.count !== null ? (
              <Badge variant="secondary" className="bg-amber-100 text-amber-900">
                {card.count}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-slate-500">لا توجد بيانات حالياً</Badge>
            )}
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">{card.description}</p>
          <Button asChild size="sm" variant="link" className="px-0 mt-1 h-auto text-indigo-600">
            <Link to={card.href} className="gap-1">
              عرض التفاصيل
              <ArrowLeft size={12} />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
