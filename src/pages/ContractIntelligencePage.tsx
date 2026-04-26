import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Spinner, Warning, UploadSimple, FileText, Queue, FileCsv,
  ShieldWarning, CopySimple, Eye, CheckCircle, XCircle, Clock,
} from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const statusLabels: Record<string, string> = {
  pending: 'قيد الانتظار',
  processing: 'جاري المعالجة',
  review: 'قيد المراجعة',
  approved: 'مُعتمد',
  rejected: 'مرفوض',
  failed: 'فشل',
};

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800',
  processing: 'bg-blue-100 text-blue-800',
  review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  failed: 'bg-red-100 text-red-800',
};

const RECENT_LIMIT = 10;

export default function ContractIntelligencePage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [stats, setStats] = useState<any>(null);
  const [recentDocs, setRecentDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError('');
    Promise.all([
      apiService.getIntelligenceDashboard(),
      apiService.getProcessingQueue({ limit: RECENT_LIMIT }),
    ])
      .then(([dashData, queueData]) => {
        setStats(dashData);
        setRecentDocs(queueData.documents || []);
      })
      .catch(() => setError('فشل تحميل بيانات مركز الذكاء'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
      fetchData();
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
          <div className="text-center py-8 text-destructive flex flex-col items-center gap-2">
            <Warning size={32} />
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchData}>إعادة المحاولة</Button>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner className="animate-spin" size={32} />
          </div>
        ) : (
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
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>آخر المستندات</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => navigate('/contract-intelligence/queue')}>
                  عرض الكل
                </Button>
              </CardHeader>
              <CardContent>
                {/* Desktop table */}
                <div className="responsive-table-desktop">
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
                      {recentDocs.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                            لا توجد مستندات بعد
                          </TableCell>
                        </TableRow>
                      ) : (
                        recentDocs.map((doc) => (
                          <TableRow key={doc.id}>
                            <TableCell className="font-medium max-w-[200px] truncate">
                              {doc.original_filename || doc.filename || '-'}
                            </TableCell>
                            <TableCell>
                              <Badge className={statusColors[doc.status] || 'bg-gray-100 text-gray-800'}>
                                {statusLabels[doc.status] || doc.status}
                              </Badge>
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
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {/* Mobile card view */}
                <div className="responsive-cards-mobile space-y-3">
                  {recentDocs.length === 0 ? (
                    <p className="text-center py-8 text-muted-foreground">لا توجد مستندات بعد</p>
                  ) : (
                    recentDocs.map((doc) => (
                      <div
                        key={doc.id}
                        className="border rounded-lg p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={() => navigate(`/contract-intelligence/queue?doc=${doc.id}`)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium truncate max-w-[200px]">
                            {doc.original_filename || doc.filename || '-'}
                          </span>
                          <Badge className={statusColors[doc.status] || 'bg-gray-100 text-gray-800'}>
                            {statusLabels[doc.status] || doc.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {doc.created_at ? format(new Date(doc.created_at), 'yyyy/MM/dd') : '-'}
                        </p>
                      </div>
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
