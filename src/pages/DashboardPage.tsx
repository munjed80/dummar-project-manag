import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { ChatCircleDots, ListChecks, FileText, WarningCircle, Plus, ArrowRight, Spinner } from '@phosphor-icons/react';

const complaintStatusLabels: Record<string, string> = {
  new: 'جديدة', under_review: 'قيد المراجعة', assigned: 'مُعينة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};

const complaintStatusColors: Record<string, string> = {
  new: 'bg-blue-500', under_review: 'bg-yellow-500',
  assigned: 'bg-orange-500', in_progress: 'bg-purple-500',
  resolved: 'bg-green-500', rejected: 'bg-red-500',
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

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { role } = useAuth();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await apiService.getDashboardStats();
        setStats(data);
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
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

  const totalComplaints = stats?.total_complaints || 0;
  const totalTasks = stats?.total_tasks || 0;

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold mb-1">لوحة التحكم</h1>
            <p className="text-muted-foreground text-sm">نظرة عامة على نشاطات إدارة التجمع - مشروع دمر</p>
          </div>
          <div className="flex gap-2">
            <Button asChild size="sm" variant="outline">
              <Link to="/complaints">
                <ChatCircleDots size={16} className="ml-1" />
                الشكاوى
                <ArrowRight size={14} className="mr-1" />
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to="/tasks">
                <ListChecks size={16} className="ml-1" />
                المهام
                <ArrowRight size={14} className="mr-1" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-t-2 border-t-[#C8A24A]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">إجمالي الشكاوى</CardTitle>
              <ChatCircleDots size={20} className="text-[#C8A24A]" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalComplaints}</div>
              <p className="text-xs text-muted-foreground mt-1">
                جديدة: {stats?.complaints_by_status?.new || 0}
              </p>
            </CardContent>
          </Card>

          <Card className="border-t-2 border-t-[#C8A24A]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">إجمالي المهام</CardTitle>
              <ListChecks size={20} className="text-[#C8A24A]" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalTasks}</div>
              <p className="text-xs text-muted-foreground mt-1">
                قيد التنفيذ: {stats?.tasks_by_status?.in_progress || 0}
              </p>
            </CardContent>
          </Card>

          <Card className="border-t-2 border-t-[#C8A24A]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">العقود النشطة</CardTitle>
              <FileText size={20} className="text-[#C8A24A]" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.active_contracts || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                إجمالي: {stats?.total_contracts || 0}
              </p>
            </CardContent>
          </Card>

          <Card className="border-t-2 border-t-[#C8A24A]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">عقود قرب الانتهاء</CardTitle>
              <WarningCircle size={20} className="text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.contracts_nearing_expiry || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">خلال 30 يومًا</p>
            </CardContent>
          </Card>
        </div>

        {/* Investment-contract expiry alerts (90/60/30 + expired). Shown
            only when at least one bucket is non-zero so we don't add noise
            for orgs that don't use the investment-contracts module yet. */}
        {stats && (
          (stats.investment_contracts_expired || 0) +
          (stats.investment_contracts_within_90 || 0) > 0
        ) && (
          <Card className="border-yellow-300">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <WarningCircle size={20} className="text-yellow-600" />
                تنبيهات العقود الاستثمارية
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                <Link to="/investment-contracts" className="rounded border border-red-300 bg-red-50 p-3 hover:bg-red-100">
                  <div className="text-xl font-bold text-red-700">{stats.investment_contracts_expired || 0}</div>
                  <div className="text-xs text-red-700">منتهية</div>
                </Link>
                <Link to="/investment-contracts" className="rounded border border-red-200 bg-red-50/60 p-3 hover:bg-red-100">
                  <div className="text-xl font-bold text-red-600">{stats.investment_contracts_within_30 || 0}</div>
                  <div className="text-xs text-red-700">خلال 30 يوم</div>
                </Link>
                <Link to="/investment-contracts" className="rounded border border-orange-200 bg-orange-50/60 p-3 hover:bg-orange-100">
                  <div className="text-xl font-bold text-orange-600">{stats.investment_contracts_within_60 || 0}</div>
                  <div className="text-xs text-orange-700">خلال 60 يوم</div>
                </Link>
                <Link to="/investment-contracts" className="rounded border border-yellow-200 bg-yellow-50/60 p-3 hover:bg-yellow-100">
                  <div className="text-xl font-bold text-yellow-700">{stats.investment_contracts_within_90 || 0}</div>
                  <div className="text-xs text-yellow-700">خلال 90 يوم</div>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>توزيع الشكاوى حسب الحالة</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {stats && Object.entries(stats.complaints_by_status as Record<string, number>).map(([status, count]) => {
                  const pct = totalComplaints > 0 ? Math.round((count / totalComplaints) * 100) : 0;
                  return (
                    <div key={status} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span>{complaintStatusLabels[status] || status}</span>
                        <span className="font-semibold">{count} <span className="text-xs text-muted-foreground">({pct}%)</span></span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${complaintStatusColors[status] || 'bg-gray-400'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>توزيع المهام حسب الحالة</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {stats && Object.entries(stats.tasks_by_status as Record<string, number>).map(([status, count]) => {
                  const pct = totalTasks > 0 ? Math.round((count / totalTasks) * 100) : 0;
                  return (
                    <div key={status} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span>{taskStatusLabels[status] || status}</span>
                        <span className="font-semibold">{count} <span className="text-xs text-muted-foreground">({pct}%)</span></span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
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
        </div>
      </div>
    </Layout>
  );
}
