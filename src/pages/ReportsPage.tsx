import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Spinner, ChartBar, Warning, CheckCircle, ClipboardText, FileText } from '@phosphor-icons/react';

const complaintTypeLabels: Record<string, string> = {
  infrastructure: 'البنية التحتية',
  cleaning: 'النظافة',
  electricity: 'الكهرباء',
  water: 'المياه',
  roads: 'الطرق',
  lighting: 'الإنارة',
  other: 'أخرى',
};

const statusLabelsComplaints: Record<string, string> = {
  new: 'جديدة',
  under_review: 'قيد المراجعة',
  assigned: 'مُعينة',
  in_progress: 'قيد التنفيذ',
  resolved: 'تم الحل',
  rejected: 'مرفوضة',
};

const statusLabelsTasks: Record<string, string> = {
  pending: 'معلقة',
  assigned: 'مُعينة',
  in_progress: 'قيد التنفيذ',
  completed: 'مكتملة',
  cancelled: 'ملغاة',
};

function StatCard({ title, value, icon: Icon, color }: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-lg ${color}`}>
            <Icon size={24} />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiService.getReportsSummary()
      .then(setReport)
      .catch((err) => setError(err.message || 'فشل تحميل التقارير'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="text-center py-12 text-destructive">{error}</div>
      </Layout>
    );
  }

  if (!report) {
    return (
      <Layout>
        <div className="text-center py-12 text-muted-foreground">لا توجد بيانات للتقارير</div>
      </Layout>
    );
  }

  const { complaints, tasks, contracts } = report;

  return (
    <Layout>
      <div className="space-y-6">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <ChartBar size={28} />
          التقارير والإحصائيات
        </h2>

        {/* Top-level KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="إجمالي الشكاوى" value={complaints.total} icon={ClipboardText} color="bg-blue-100 text-blue-700" />
          <StatCard title="نسبة الحل" value={`${complaints.resolution_rate}%`} icon={CheckCircle} color="bg-green-100 text-green-700" />
          <StatCard title="المهام المتأخرة" value={tasks.overdue} icon={Warning} color="bg-red-100 text-red-700" />
          <StatCard title="قيمة العقود الكلية (ل.س)" value={Number(contracts.total_value).toLocaleString('en-US')} icon={FileText} color="bg-purple-100 text-purple-700" />
        </div>

        {/* Complaints breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>تفاصيل الشكاوى</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold mb-3">حسب النوع</h4>
                <div className="space-y-2">
                  {Object.entries(complaints.by_type || {}).map(([key, count]) => (
                    <div key={key} className="flex justify-between items-center py-1 border-b border-muted">
                      <span>{complaintTypeLabels[key] || key}</span>
                      <span className="font-mono font-bold">{count as number}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-3">حسب الحالة</h4>
                <div className="space-y-2">
                  {Object.entries(complaints.by_status || {}).map(([key, count]) => (
                    <div key={key} className="flex justify-between items-center py-1 border-b border-muted">
                      <span>{statusLabelsComplaints[key] || key}</span>
                      <span className="font-mono font-bold">{count as number}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <Separator className="my-4" />
            <p className="text-sm text-muted-foreground">
              شكاوى هذا الشهر: <span className="font-bold">{complaints.this_month}</span> | 
              تم حلّها: <span className="font-bold">{complaints.resolved}</span> من أصل <span className="font-bold">{complaints.total}</span>
            </p>
          </CardContent>
        </Card>

        {/* Tasks breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>تفاصيل المهام</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">الإجمالي</p>
                <p className="text-3xl font-bold">{tasks.total}</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-sm text-muted-foreground">مكتملة</p>
                <p className="text-3xl font-bold text-green-700">{tasks.completed}</p>
              </div>
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <p className="text-sm text-muted-foreground">متأخرة</p>
                <p className="text-3xl font-bold text-red-700">{tasks.overdue}</p>
              </div>
            </div>
            <h4 className="font-semibold mb-3">حسب الحالة</h4>
            <div className="space-y-2">
              {Object.entries(tasks.by_status || {}).map(([key, count]) => (
                <div key={key} className="flex justify-between items-center py-1 border-b border-muted">
                  <span>{statusLabelsTasks[key] || key}</span>
                  <span className="font-mono font-bold">{count as number}</span>
                </div>
              ))}
            </div>
            <Separator className="my-4" />
            <p className="text-sm text-muted-foreground">
              نسبة الإنجاز: <span className="font-bold">{tasks.completion_rate}%</span>
            </p>
          </CardContent>
        </Card>

        {/* Contracts summary */}
        <Card>
          <CardHeader>
            <CardTitle>ملخص العقود</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">إجمالي العقود</p>
                <p className="text-3xl font-bold">{contracts.total}</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-sm text-muted-foreground">العقود النشطة</p>
                <p className="text-3xl font-bold text-green-700">{contracts.active}</p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-sm text-muted-foreground">القيمة الإجمالية</p>
                <p className="text-2xl font-bold text-purple-700">{Number(contracts.total_value).toLocaleString('en-US')}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
