import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Spinner, UploadSimple, FileText, Queue, FileCsv,
  ShieldWarning, CopySimple, Eye, CheckCircle, XCircle, Clock,
} from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { describeLoadError } from '@/lib/loadError';
import { queryKeys } from '@/lib/queryKeys';
import {
  DataTableShell, StatusBadge, EmptyState, ErrorState, LoadingSkeleton,
  MobileEntityCard, RefreshingIndicator, StaleDataNotice, type StatusTone,
} from '@/components/data';

const statusLabels: Record<string, string> = {
  pending: 'قيد الانتظار',
  processing: 'جاري المعالجة',
  review: 'قيد المراجعة',
  approved: 'مُعتمد',
  rejected: 'مرفوض',
  failed: 'فشل',
};

const statusTones: Record<string, StatusTone> = {
  pending: 'neutral',
  processing: 'progress',
  review: 'warning',
  approved: 'success',
  rejected: 'danger',
  failed: 'danger',
};

const RECENT_LIMIT = 10;

export default function ContractIntelligencePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const dashboardQuery = useQuery({
    queryKey: queryKeys.contractIntelligence.dashboard(),
    queryFn: () => apiService.getIntelligenceDashboard(),
  });
  const queueQuery = useQuery({
    queryKey: queryKeys.contractIntelligence.queue({ limit: RECENT_LIMIT }),
    queryFn: () => apiService.getProcessingQueue({ limit: RECENT_LIMIT }).then((d) => d.documents || []),
  });

  const stats = dashboardQuery.data ?? null;
  const recentDocs = queueQuery.data ?? [];

  const firstLoad = dashboardQuery.isPending && !stats;
  const refreshing =
    (dashboardQuery.isFetching && !!stats) || (queueQuery.isFetching && recentDocs.length > 0);
  const refreshFailed =
    (dashboardQuery.isError && !!stats) || (queueQuery.isError && recentDocs.length > 0);
  const fullPageError = dashboardQuery.isError && !stats;
  const error = fullPageError
    ? describeLoadError(dashboardQuery.error, 'مركز ذكاء العقود').message
    : '';

  const refetchAll = () => {
    void dashboardQuery.refetch();
    void queueQuery.refetch();
  };
  const invalidateAll = () =>
    queryClient.invalidateQueries({ queryKey: ['contract-intelligence'] });

  const handleUpload = async (file: File) => {
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      toast.error('حجم الملف يتجاوز 10 ميجابايت');
      return;
    }
    setUploading(true);
    try {
      await apiService.uploadContractDocument(file);
      toast.success(`تم رفع "${file.name}" بنجاح`);
      void invalidateAll();
    } catch {
      toast.error('فشل رفع الملف');
    } finally {
      setUploading(false);
    }
  };

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const statCards = [
    { label: 'إجمالي المستندات', key: 'total_documents', icon: FileText, color: 'text-blue-600' },
    { label: 'قيد المراجعة', key: 'review', icon: Clock, color: 'text-yellow-600' },
    { label: 'مُعتمد', key: 'approved', icon: CheckCircle, color: 'text-green-600' },
    { label: 'فشل', key: 'failed', icon: XCircle, color: 'text-red-600' },
    { label: 'علامات المخاطر', key: 'total_risk_flags', icon: ShieldWarning, color: 'text-orange-600' },
    { label: 'التكرارات', key: 'total_duplicates', icon: CopySimple, color: 'text-purple-600' },
  ];

  const quickLinks = [
    { label: 'طابور المعالجة', path: '/contract-intelligence/queue', icon: Queue },
    { label: 'استيراد جماعي', path: '/contract-intelligence/bulk-import', icon: FileCsv },
    { label: 'المخاطر', path: '/contract-intelligence/risks', icon: ShieldWarning },
    { label: 'التكرارات', path: '/contract-intelligence/duplicates', icon: CopySimple },
    { label: 'التقارير', path: '/contract-intelligence/reports', icon: FileText },
  ];

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold mb-2">مركز ذكاء العقود</h1>
            <p className="text-muted-foreground">مركز ذكي لرفع وتحليل عقود الاستثمار وتجهيزها للإرسال إلى صفحة العقود الاستثمارية</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" onClick={() => navigate('/investment-contracts')}>
              عرض العقود الاستثمارية
            </Button>
            <Button variant="outline" onClick={() => navigate('/manual-contracts')}>
              العقود التشغيلية
            </Button>
          </div>
        </div>

        {error && (
          <ErrorState message={error} onRetry={refetchAll} retrying={dashboardQuery.isFetching} />
        )}

        {refreshFailed && (
          <StaleDataNotice onRetry={refetchAll} retrying={refreshing} />
        )}
        {refreshing && !refreshFailed && (
          <RefreshingIndicator />
        )}

        {firstLoad && !error ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i} className="border-[#D8E2EF]">
                  <CardContent className="py-6">
                    <LoadingSkeleton rows={1} columns={2} />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ) : !error && (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {statCards.map((sc) => (
                <Card key={sc.key}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">{sc.label}</CardTitle>
                    <sc.icon size={20} className={sc.color} />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats?.[sc.key] ?? 0}</div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Quick Links */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {quickLinks.map((link) => (
                <Button
                  key={link.path}
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2"
                  onClick={() => navigate(link.path)}
                >
                  <link.icon size={24} />
                  <span className="text-sm">{link.label}</span>
                </Button>
              ))}
            </div>

            {/* Upload Area */}
            <Card>
              <CardHeader>
                <CardTitle>رفع مستند</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                >
                  {uploading ? (
                    <div className="flex flex-col items-center gap-2">
                      <Spinner className="animate-spin" size={32} />
                      <p className="text-sm text-muted-foreground">جاري الرفع...</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <UploadSimple size={32} className="text-muted-foreground" />
                      <p className="text-sm font-medium">اسحب الملف هنا أو انقر للاختيار</p>
                      <p className="text-xs text-muted-foreground">PDF, Word, صور — حد أقصى 10 ميجابايت</p>
                    </div>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.tiff"
                    onChange={onFileSelect}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Recent Documents */}
            <Card className="border-[#D8E2EF]">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-[#0F2A4A]">آخر المستندات</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => navigate('/contract-intelligence/queue')}>
                  عرض الكل
                </Button>
              </CardHeader>
              <CardContent>
                {/* Desktop table */}
                <div className="responsive-table-desktop">
                  {recentDocs.length === 0 ? (
                    <EmptyState
                      icon={<FileText size={40} weight="duotone" />}
                      title="لا توجد مستندات بعد"
                    />
                  ) : (
                    <DataTableShell>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">اسم الملف</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">تاريخ الرفع</TableHead>
                            <TableHead className="text-right">إجراء</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {recentDocs.map((doc) => (
                            <TableRow key={doc.id}>
                              <TableCell className="font-medium max-w-[260px] truncate text-[#0F2A4A]">
                                {doc.original_filename || doc.filename || '-'}
                              </TableCell>
                              <TableCell>
                                <StatusBadge tone={statusTones[doc.status] ?? 'neutral'}>
                                  {statusLabels[doc.status] || doc.status}
                                </StatusBadge>
                              </TableCell>
                              <TableCell>
                                {doc.created_at ? format(new Date(doc.created_at), 'yyyy/MM/dd') : '-'}
                              </TableCell>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => navigate(`/contract-intelligence/queue?doc=${doc.id}`)}
                                >
                                  <Eye size={16} />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </DataTableShell>
                  )}
                </div>

                {/* Mobile card view */}
                <div className="responsive-cards-mobile space-y-3">
                  {recentDocs.length === 0 ? (
                    <EmptyState
                      icon={<FileText size={40} weight="duotone" />}
                      title="لا توجد مستندات بعد"
                    />
                  ) : (
                    recentDocs.map((doc) => (
                      <MobileEntityCard
                        key={doc.id}
                        onClick={() => navigate(`/contract-intelligence/queue?doc=${doc.id}`)}
                        title={
                          <span className="truncate inline-block max-w-[220px] align-middle">
                            {doc.original_filename || doc.filename || '-'}
                          </span>
                        }
                        badge={
                          <StatusBadge tone={statusTones[doc.status] ?? 'neutral'}>
                            {statusLabels[doc.status] || doc.status}
                          </StatusBadge>
                        }
                        meta={(
                          <span>{doc.created_at ? format(new Date(doc.created_at), 'yyyy/MM/dd') : '-'}</span>
                        )}
                      />
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </Layout>
  );
}
