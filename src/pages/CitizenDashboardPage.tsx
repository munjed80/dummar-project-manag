import { useState, useMemo } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { CitizenInstallBanner } from '@/components/CitizenInstallBanner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';
import { queryKeys } from '@/lib/queryKeys';
import { RefreshingIndicator, StaleDataNotice } from '@/components/data';
import { ChatCircleDots, Clock, CheckCircle, Warning, ArrowRight, Plus } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';

interface Complaint {
  id: number;
  tracking_number: string;
  complaint_type: string;
  description: string;
  status: string;
  priority?: string;
  location_text?: string;
  created_at: string;
  updated_at?: string;
  resolved_at?: string;
}

const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  new: { label: 'قيد المعالجة', variant: 'secondary' },
  under_review: { label: 'قيد المعالجة', variant: 'secondary' },
  assigned: { label: 'قيد المعالجة', variant: 'secondary' },
  in_progress: { label: 'قيد التنفيذ', variant: 'default' },
  resolved: { label: 'تم الحل', variant: 'default' },
  rejected: { label: 'مرفوضة', variant: 'destructive' },
};

const typeLabels: Record<string, string> = {
  infrastructure: 'بنية تحتية',
  cleaning: 'نظافة',
  electricity: 'كهرباء',
  water: 'مياه',
  roads: 'طرق',
  lighting: 'إنارة',
  other: 'أخرى',
};

function CitizenDashboardPage() {
  const { user } = useAuth();
  const [statusFilter, setStatusFilter] = useState<string>('');

  const listParams = useMemo(() => {
    const params: Record<string, unknown> = {};
    if (statusFilter) params.status_filter = statusFilter;
    return params;
  }, [statusFilter]);

  const complaintsQuery = useQuery({
    queryKey: queryKeys.complaints.citizen(listParams),
    queryFn: () => apiService.getCitizenComplaints(listParams as any),
    placeholderData: keepPreviousData,
  });

  const data = complaintsQuery.data;
  const complaints: Complaint[] = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const firstLoad = complaintsQuery.isPending && !data;
  const refreshing = complaintsQuery.isFetching && !!data;
  const refreshFailed = complaintsQuery.isError && !!data;
  const fullPageError = complaintsQuery.isError && !data;
  const errorMessage = fullPageError
    ? describeLoadError(complaintsQuery.error, 'الشكاوى').message
    : '';

  // Stats
  const stats = {
    total: totalCount,
    active: complaints.filter((c) => !['resolved', 'rejected'].includes(c.status)).length,
    resolved: complaints.filter((c) => c.status === 'resolved').length,
  };

  const statusFilters = [
    { value: '', label: 'الكل' },
    { value: 'new', label: 'قيد المعالجة' },
    { value: 'in_progress', label: 'قيد التنفيذ' },
    { value: 'resolved', label: 'تم الحل' },
    { value: 'rejected', label: 'مرفوضة' },
  ];

  return (
    <Layout>
      <div className="space-y-6">
        <CitizenInstallBanner />
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">مرحباً، {user?.full_name || 'مواطن'}</h1>
            <p className="text-muted-foreground mt-1">لوحة تحكم طلباتك وشكاواك في إدارة التجمع - مشروع دمر</p>
          </div>
          <Link to="/complaints/new">
            <Button>
              <Plus className="ml-2" size={18} />
              تقديم شكوى جديدة
            </Button>
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-blue-100">
                  <ChatCircleDots size={24} className="text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.total}</p>
                  <p className="text-sm text-muted-foreground">إجمالي الشكاوى</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-amber-100">
                  <Clock size={24} className="text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.active}</p>
                  <p className="text-sm text-muted-foreground">شكاوى نشطة</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-green-100">
                  <CheckCircle size={24} className="text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.resolved}</p>
                  <p className="text-sm text-muted-foreground">تم حلها</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filter */}
        <div className="flex flex-wrap gap-2">
          {statusFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                statusFilter === f.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Background-refresh indicators — keep cached data on screen. */}
        {refreshing && !refreshFailed && (
          <RefreshingIndicator />
        )}
        {refreshFailed && (
          <StaleDataNotice onRetry={() => complaintsQuery.refetch()} retrying={refreshing} />
        )}

        {/* Complaints List */}
        {firstLoad ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : fullPageError ? (
          <Card>
            <CardContent className="py-12 text-center space-y-4">
              <Warning size={48} className="mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{errorMessage}</p>
              <Button variant="outline" onClick={() => complaintsQuery.refetch()}>
                إعادة المحاولة
              </Button>
            </CardContent>
          </Card>
        ) : complaints.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Warning size={48} className="mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg font-medium text-muted-foreground">لا توجد شكاوى</p>
              <p className="text-sm text-muted-foreground mt-1">
                {statusFilter ? 'لا توجد شكاوى بهذه الحالة' : 'لم تقم بتقديم أي شكاوى بعد'}
              </p>
              <Link to="/complaints/new">
                <Button className="mt-4">تقديم شكوى جديدة</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {complaints.map((complaint) => {
              const sc = statusConfig[complaint.status] || { label: complaint.status, variant: 'outline' as const };
              return (
                <Card key={complaint.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="py-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-sm font-bold text-primary">
                            {complaint.tracking_number}
                          </span>
                          <Badge variant={sc.variant}>{sc.label}</Badge>
                        </div>
                        <p className="text-sm text-gray-700 line-clamp-1">{complaint.description}</p>
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
                          <span>{typeLabels[complaint.complaint_type] || complaint.complaint_type}</span>
                          <span>•</span>
                          <span>تاريخ التقديم: {format(new Date(complaint.created_at), 'dd/MM/yyyy', { locale: ar })}</span>
                          {complaint.updated_at && (
                            <>
                              <span>•</span>
                              <span>آخر تحديث: {format(new Date(complaint.updated_at), 'dd/MM/yyyy', { locale: ar })}</span>
                            </>
                          )}
                          {complaint.location_text && (
                            <>
                              <span>•</span>
                              <span>{complaint.location_text}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <Link to={`/complaints/${complaint.id}`}>
                        <Button variant="ghost" size="sm">
                          التفاصيل
                          <ArrowRight className="mr-1" size={16} />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}

export default CitizenDashboardPage;
