import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';
import { queryKeys } from '@/lib/queryKeys';
import { RefreshingIndicator, StaleDataNotice } from '@/components/data';
import {
  ChatCircleDots, ListChecks, FileText, WarningCircle, ArrowRight,
  Spinner, PaperPlaneTilt, Bell, Buildings, ChartBar, UsersThree,
  MapTrifold, Briefcase, Brain, ClockCounterClockwise,
} from '@phosphor-icons/react';

// ── Label / colour maps ───────────────────────────────────────────────────────

const complaintStatusLabels: Record<string, string> = {
  new: 'قيد المعالجة', under_review: 'قيد المعالجة', assigned: 'قيد المعالجة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};

const complaintStatusColors: Record<string, string> = {
  new: 'bg-indigo-500', under_review: 'bg-indigo-500',
  assigned: 'bg-indigo-500', in_progress: 'bg-purple-500',
  resolved: 'bg-green-500', rejected: 'bg-red-500',
};

// The three internal backend values that all map to قيد المعالجة.
const IN_PROCESSING_STATUSES = ['new', 'under_review', 'assigned'] as const;

/** Merge raw backend status counts into the four simplified display buckets. */
function simplifyComplaintStatusCounts(raw: Record<string, number>): Record<string, number> {
  return {
    new: IN_PROCESSING_STATUSES.reduce((sum, s) => sum + (raw[s] || 0), 0),
    in_progress: raw.in_progress || 0,
    resolved: raw.resolved || 0,
    rejected: raw.rejected || 0,
  };
}

const complaintStatusBadge: Record<string, string> = {
  new: 'bg-indigo-100 text-indigo-700',
  under_review: 'bg-indigo-100 text-indigo-700',
  assigned: 'bg-indigo-100 text-indigo-700',
  in_progress: 'bg-purple-100 text-purple-700',
  resolved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

const taskStatusLabels: Record<string, string> = {
  pending: 'معلقة', assigned: 'مُعينة', in_progress: 'قيد التنفيذ',
  completed: 'مكتملة', cancelled: 'ملغاة',
};

const taskStatusColors: Record<string, string> = {
  pending: 'bg-yellow-500', assigned: 'bg-orange-500',
  in_progress: 'bg-purple-500', completed: 'bg-green-500',
  cancelled: 'bg-red-500',
};

const taskStatusBadge: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  assigned: 'bg-orange-100 text-orange-700',
  in_progress: 'bg-purple-100 text-purple-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
};

const contractStatusBadge: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  expired: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-600',
  pending: 'bg-yellow-100 text-yellow-700',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function getArabicGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'صباح الخير';
  if (h < 18) return 'مساء الخير';
  return 'مساء النور';
}

function getArabicDate(): string {
  return new Intl.DateTimeFormat('ar-SA', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  }).format(new Date());
}

// ── Page ─────────────────────────────────────────────────────────────────────

const RECENT_ITEMS_LIMIT = 5;

export default function DashboardPage() {
  const { user } = useAuth();

  const statsQuery = useQuery({
    queryKey: queryKeys.dashboard.stats(),
    queryFn: () => apiService.getDashboardStats(),
  });

  const activityQuery = useQuery({
    queryKey: queryKeys.dashboard.activity(),
    queryFn: () => apiService.getRecentActivity(),
  });

  const stats = statsQuery.data ?? null;
  const activity = activityQuery.data ?? null;

  // First load with no cache → full skeleton. Once cached data exists we
  // keep it on screen and only show a small "refreshing" indicator.
  const firstLoad = statsQuery.isPending && !stats;
  const refreshing =
    (statsQuery.isFetching && !!stats) ||
    (activityQuery.isFetching && !!activity);
  const refreshFailed =
    (statsQuery.isError && !!stats) ||
    (activityQuery.isError && !!activity);
  const fullPageError = statsQuery.isError && !stats;
  const statsError = fullPageError
    ? describeLoadError(statsQuery.error, 'لوحة التحكم').message
    : null;

  const refetchAll = () => {
    void statsQuery.refetch();
    void activityQuery.refetch();
  };

  if (firstLoad) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  const totalComplaints = stats?.total_complaints || 0;
  const totalTasks = stats?.total_tasks || 0;
  const newComplaints = stats?.complaints_by_status?.new || 0;
  const inProgressTasks = stats?.tasks_by_status?.in_progress || 0;
  const resolvedComplaints = stats?.complaints_by_status?.resolved || 0;
  const completedTasks = stats?.tasks_by_status?.completed || 0;
  const urgentAlerts =
    (stats?.contracts_nearing_expiry || 0) +
    (stats?.investment_contracts_expired || 0) +
    (stats?.investment_contracts_within_30 || 0);
  const hasExpiryAlerts =
    stats &&
    (stats.investment_contracts_expired || 0) + (stats.investment_contracts_within_30 || 0) > 0;

  // ── KPI card definitions ──────────────────────────────────────────────────

  const kpiCards = [
    {
      label: 'إجمالي الشكاوى',
      value: totalComplaints,
      hint: `جديدة: ${newComplaints}  •  محلولة: ${resolvedComplaints}`,
      hintAlert: newComplaints > 0,
      icon: ChatCircleDots,
      href: '/complaints',
      bg: 'from-sky-50 to-blue-50',
      border: 'border-sky-200',
      iconColor: 'text-sky-600',
      textColor: 'text-sky-900',
      valueColor: 'text-sky-800',
    },
    {
      label: 'إجمالي المهام',
      value: totalTasks,
      hint: `قيد التنفيذ: ${inProgressTasks}  •  مكتملة: ${completedTasks}`,
      hintAlert: inProgressTasks > 0,
      icon: ListChecks,
      href: '/tasks',
      bg: 'from-indigo-50 to-violet-50',
      border: 'border-indigo-200',
      iconColor: 'text-indigo-600',
      textColor: 'text-indigo-900',
      valueColor: 'text-indigo-800',
    },
    {
      label: 'العقود النشطة',
      value: stats?.active_contracts || 0,
      hint: `إجمالي العقود: ${stats?.total_contracts || 0}`,
      hintAlert: false,
      icon: FileText,
      href: '/manual-contracts',
      bg: 'from-emerald-50 to-green-50',
      border: 'border-emerald-200',
      iconColor: 'text-emerald-600',
      textColor: 'text-emerald-900',
      valueColor: 'text-emerald-800',
    },
    {
      label: 'تنبيهات العقود',
      value: urgentAlerts,
      hint: urgentAlerts > 0 ? 'تنتهي خلال 30 يوم أو منتهية فعلاً' : 'لا تنبيهات حالياً',
      hintAlert: urgentAlerts > 0,
      icon: Bell,
      href: '/investment-contracts',
      bg: urgentAlerts > 0 ? 'from-rose-50 to-red-50' : 'from-gray-50 to-slate-50',
      border: urgentAlerts > 0 ? 'border-rose-300' : 'border-gray-200',
      iconColor: urgentAlerts > 0 ? 'text-rose-600' : 'text-gray-400',
      textColor: urgentAlerts > 0 ? 'text-rose-900' : 'text-gray-600',
      valueColor: urgentAlerts > 0 ? 'text-rose-700' : 'text-gray-500',
    },
  ];

  // ── Quick-action shortcuts ────────────────────────────────────────────────

  const quickActions = [
    { label: 'الشكاوى',            href: '/complaints',             icon: ChatCircleDots,       cls: 'text-sky-700 bg-sky-50 hover:bg-sky-100' },
    { label: 'المهام',             href: '/tasks',                  icon: ListChecks,            cls: 'text-indigo-700 bg-indigo-50 hover:bg-indigo-100' },
    { label: 'العقود',             href: '/manual-contracts',       icon: FileText,              cls: 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100' },
    { label: 'عقود استثمارية',     href: '/investment-contracts',   icon: Briefcase,             cls: 'text-amber-700 bg-amber-50 hover:bg-amber-100' },
    { label: 'عقارات استثمارية',   href: '/investment-properties',  icon: Buildings,             cls: 'text-violet-700 bg-violet-50 hover:bg-violet-100' },
    { label: 'التقارير',           href: '/reports',                icon: ChartBar,              cls: 'text-blue-700 bg-blue-50 hover:bg-blue-100' },
    { label: 'خريطة الشكاوى',     href: '/complaints-map',         icon: MapTrifold,            cls: 'text-teal-700 bg-teal-50 hover:bg-teal-100' },
    { label: 'الفرق',              href: '/teams',                  icon: UsersThree,            cls: 'text-orange-700 bg-orange-50 hover:bg-orange-100' },
    { label: 'المساعد الذكي',      href: '/internal-bot',           icon: Brain,                 cls: 'text-pink-700 bg-pink-50 hover:bg-pink-100' },
  ];

  return (
    <Layout>
      <div className="space-y-6">

        {/* ── 1. Hero / Welcome banner ──────────────────────────────────── */}
        <section className="relative overflow-hidden rounded-2xl border border-sky-100 bg-gradient-to-bl from-sky-50 via-white to-indigo-50 p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <Badge variant="outline" className="mb-2 text-xs text-sky-700 border-sky-300 bg-sky-50">
                {getArabicDate()}
              </Badge>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-900 mb-1">
                {getArabicGreeting()}{user?.full_name ? `، ${user.full_name}` : ''}
              </h1>
              <p className="text-muted-foreground text-sm">
                نظرة شاملة على نشاطات إدارة التجمع — مشروع دمر
              </p>
            </div>
            <div className="flex gap-2 flex-wrap shrink-0">
              <Button asChild size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white">
                <Link to="/executive-briefing">
                  <PaperPlaneTilt size={16} className="ml-1" />
                  موجز تنفيذي
                  <ArrowRight size={14} className="mr-1" />
                </Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link to="/reports">
                  <ChartBar size={16} className="ml-1" />
                  التقارير
                </Link>
              </Button>
            </div>
          </div>
        </section>

        {/* ── 2. Error banner ───────────────────────────────────────────── */}
        {statsError && !stats && (
          <Card className="border-amber-300 bg-amber-50">
            <CardContent className="py-3 text-sm text-amber-900 flex flex-col sm:flex-row sm:items-center gap-2">
              <div className="flex items-center gap-2 flex-1">
                <WarningCircle size={18} className="text-amber-700" />
                <span>{statsError}</span>
              </div>
              <Button variant="outline" size="sm" onClick={refetchAll} className="self-start sm:self-auto">
                إعادة المحاولة
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Soft inline indicator: a background refresh is running while
            cached data is on screen. */}
        {refreshing && !refreshFailed && (
          <RefreshingIndicator />
        )}

        {/* Refresh failed but the previous payload is still visible — keep
            the operator's context, do NOT replace the page with an error. */}
        {refreshFailed && (
          <StaleDataNotice onRetry={refetchAll} retrying={refreshing} />
        )}

        {/* ── 3. Urgent-alert banner ────────────────────────────────────── */}
        {hasExpiryAlerts && (
          <div className="flex items-center gap-3 rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-rose-800 text-sm">
            <WarningCircle size={20} className="text-rose-600 shrink-0" />
            <span className="flex-1">
              <strong>تنبيه عاجل: </strong>
              {(stats.investment_contracts_expired || 0) > 0 && (
                <span className="font-semibold">{stats.investment_contracts_expired} عقد استثماري منتهٍ</span>
              )}
              {(stats.investment_contracts_expired || 0) > 0 && (stats.investment_contracts_within_30 || 0) > 0 && ' و'}
              {(stats.investment_contracts_within_30 || 0) > 0 && (
                <span className="font-semibold"> {stats.investment_contracts_within_30} عقد ينتهي خلال 30 يومًا</span>
              )}
              {' '}— تحتاج إلى مراجعة فورية.
            </span>
            <Button asChild size="sm" variant="outline" className="border-rose-300 text-rose-700 hover:bg-rose-100 shrink-0">
              <Link to="/investment-contracts">مراجعة</Link>
            </Button>
          </div>
        )}

        {/* ── 4. KPI cards ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpiCards.map((card) => (
            <Link key={card.label} to={card.href} className="block group">
              <Card className={`border ${card.border} bg-gradient-to-br ${card.bg} hover:shadow-md transition-shadow h-full`}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className={`text-sm font-medium ${card.textColor}`}>{card.label}</CardTitle>
                  <div className={`rounded-lg p-1.5 bg-white/60 ${card.iconColor}`}>
                    <card.icon size={20} weight="duotone" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${card.valueColor}`}>{card.value}</div>
                  <p className={`text-xs mt-1 ${card.hintAlert ? card.iconColor : 'text-muted-foreground'}`}>
                    {card.hint}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* ── 5. Investment-contract expiry buckets ─────────────────────── */}
        {stats && (stats.investment_contracts_expired || 0) + (stats.investment_contracts_within_90 || 0) > 0 && (
          <Card className="border-yellow-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <ClockCounterClockwise size={18} className="text-yellow-600" />
                تفاصيل انتهاء العقود الاستثمارية
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                <Link to="/investment-contracts" className="rounded-lg border border-red-300 bg-red-50 p-3 hover:bg-red-100 transition-colors">
                  <div className="text-2xl font-bold text-red-700">{stats.investment_contracts_expired || 0}</div>
                  <div className="text-xs text-red-700 mt-0.5">منتهية</div>
                </Link>
                <Link to="/investment-contracts" className="rounded-lg border border-red-200 bg-red-50/60 p-3 hover:bg-red-100 transition-colors">
                  <div className="text-2xl font-bold text-red-600">{stats.investment_contracts_within_30 || 0}</div>
                  <div className="text-xs text-red-700 mt-0.5">خلال 30 يوم</div>
                </Link>
                <Link to="/investment-contracts" className="rounded-lg border border-orange-200 bg-orange-50/60 p-3 hover:bg-orange-100 transition-colors">
                  <div className="text-2xl font-bold text-orange-600">{stats.investment_contracts_within_60 || 0}</div>
                  <div className="text-xs text-orange-700 mt-0.5">خلال 60 يوم</div>
                </Link>
                <Link to="/investment-contracts" className="rounded-lg border border-yellow-200 bg-yellow-50/60 p-3 hover:bg-yellow-100 transition-colors">
                  <div className="text-2xl font-bold text-yellow-700">{stats.investment_contracts_within_90 || 0}</div>
                  <div className="text-xs text-yellow-700 mt-0.5">خلال 90 يوم</div>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── 6. Status distributions + recent complaints ───────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Complaints distribution */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>توزيع الشكاوى</span>
                <Link to="/complaints" className="text-xs text-sky-600 hover:underline flex items-center gap-1">
                  عرض الكل <ArrowRight size={12} />
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {stats && (() => {
                  const raw = stats.complaints_by_status as Record<string, number>;
                  const simplified = simplifyComplaintStatusCounts(raw);
                  return Object.entries(simplified).map(([status, count]) => {
                    const pct = totalComplaints > 0 ? Math.round((count / totalComplaints) * 100) : 0;
                    return (
                      <div key={status} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">{complaintStatusLabels[status] || status}</span>
                          <span className="font-semibold">{count} <span className="text-muted-foreground">({pct}%)</span></span>
                        </div>
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${complaintStatusColors[status] || 'bg-gray-400'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            </CardContent>
          </Card>

          {/* Tasks distribution */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>توزيع المهام</span>
                <Link to="/tasks" className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
                  عرض الكل <ArrowRight size={12} />
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {stats && Object.entries(stats.tasks_by_status as Record<string, number>).map(([status, count]) => {
                  const pct = totalTasks > 0 ? Math.round((count / totalTasks) * 100) : 0;
                  return (
                    <div key={status} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">{taskStatusLabels[status] || status}</span>
                        <span className="font-semibold">{count} <span className="text-muted-foreground">({pct}%)</span></span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${taskStatusColors[status] || 'bg-gray-400'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Recent complaints */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>آخر الشكاوى</span>
                <Link to="/complaints" className="text-xs text-sky-600 hover:underline flex items-center gap-1">
                  عرض الكل <ArrowRight size={12} />
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!activity?.recent_complaints?.length ? (
                <p className="text-xs text-muted-foreground text-center py-6">لا توجد بيانات</p>
              ) : (
                <div className="space-y-1">
                  {activity.recent_complaints.slice(0, RECENT_ITEMS_LIMIT).map((c: any) => (
                    <Link
                      key={c.id}
                      to={`/complaints/${c.id}`}
                      className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-muted transition-colors group"
                    >
                      <span className="text-xs font-medium truncate group-hover:text-sky-700">{c.tracking_number}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 ${complaintStatusBadge[c.status] || 'bg-gray-100 text-gray-600'}`}>
                        {complaintStatusLabels[c.status] || c.status}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── 7. Recent tasks + contracts ───────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>آخر المهام</span>
                <Link to="/tasks" className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
                  عرض الكل <ArrowRight size={12} />
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!activity?.recent_tasks?.length ? (
                <p className="text-xs text-muted-foreground text-center py-6">لا توجد بيانات</p>
              ) : (
                <div className="space-y-1">
                  {activity.recent_tasks.slice(0, RECENT_ITEMS_LIMIT).map((t: any) => (
                    <Link
                      key={t.id}
                      to={`/tasks/${t.id}`}
                      className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-muted transition-colors group"
                    >
                      <span className="text-xs font-medium truncate flex-1 group-hover:text-indigo-700">{t.title}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 ${taskStatusBadge[t.status] || 'bg-gray-100 text-gray-600'}`}>
                        {taskStatusLabels[t.status] || t.status}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>آخر العقود</span>
                <Link to="/manual-contracts" className="text-xs text-emerald-600 hover:underline flex items-center gap-1">
                  عرض الكل <ArrowRight size={12} />
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!activity?.recent_contracts?.length ? (
                <p className="text-xs text-muted-foreground text-center py-6">لا توجد بيانات</p>
              ) : (
                <div className="space-y-1">
                  {activity.recent_contracts.slice(0, RECENT_ITEMS_LIMIT).map((c: any) => (
                    <Link
                      key={c.id}
                      to={`/contracts/${c.id}`}
                      className="flex items-start justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-muted transition-colors group"
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-medium truncate group-hover:text-emerald-700">{c.title || c.contract_number}</p>
                        {c.title && <p className="text-xs text-muted-foreground">{c.contract_number}</p>}
                      </div>
                      <span className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 mt-0.5 ${contractStatusBadge[c.status] || 'bg-gray-100 text-gray-600'}`}>
                        {c.status}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── 8. Quick-access grid ──────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">الوصول السريع</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
              {quickActions.map((action) => (
                <Link
                  key={action.href}
                  to={action.href}
                  className={`flex flex-col items-center gap-1.5 rounded-xl p-3 transition-colors ${action.cls}`}
                >
                  <action.icon size={22} weight="duotone" />
                  <span className="text-xs font-medium text-center leading-tight">{action.label}</span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

      </div>
    </Layout>
  );
}
