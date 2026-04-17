import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { apiService } from '@/services/api';
import { ChatCircleDots, ListChecks, FileText, WarningCircle } from '@phosphor-icons/react';

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

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
        <div className="text-center py-12">جاري التحميل...</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold mb-2">لوحة التحكم</h1>
          <p className="text-muted-foreground">نظرة عامة على نشاطات مشروع دمر</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">إجمالي الشكاوى</CardTitle>
              <ChatCircleDots size={20} className="text-accent" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_complaints || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                جديدة: {stats?.complaints_by_status?.new || 0}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">إجمالي المهام</CardTitle>
              <ListChecks size={20} className="text-accent" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_tasks || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                قيد التنفيذ: {stats?.tasks_by_status?.in_progress || 0}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">العقود النشطة</CardTitle>
              <FileText size={20} className="text-accent" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.active_contracts || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                إجمالي: {stats?.total_contracts || 0}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">عقود قرب الانتهاء</CardTitle>
              <WarningCircle size={20} className="text-warning" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.contracts_nearing_expiry || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">خلال 30 يومًا</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>توزيع الشكاوى حسب الحالة</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {stats && Object.entries(stats.complaints_by_status as Record<string, number>).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className="text-sm">{status}</span>
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>توزيع المهام حسب الحالة</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {stats && Object.entries(stats.tasks_by_status as Record<string, number>).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className="text-sm">{status}</span>
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
