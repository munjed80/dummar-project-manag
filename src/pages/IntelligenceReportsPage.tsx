import { useState, useEffect, useCallback } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Spinner, Warning, ChartBar, FileText, ShieldWarning, CopySimple,
  CheckCircle, XCircle, Clock, Eye, ArrowClockwise,
} from '@phosphor-icons/react';

const typeLabels: Record<string, string> = {
  maintenance: 'صيانة',
  cleaning: 'تنظيف',
  construction: 'إنشاء',
  roads: 'طرق',
  lighting: 'إنارة',
  supply: 'توريد',
  consulting: 'استشارات',
  services: 'خدمات',
  other: 'أخرى',
};

const severityLabels: Record<string, string> = {
  critical: 'حرج',
  high: 'مرتفع',
  medium: 'متوسط',
  low: 'منخفض',
};

const severityColors: Record<string, string> = {
  critical: 'bg-red-600 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-white',
  low: 'bg-blue-500 text-white',
};

const statusLabels: Record<string, string> = {
  queued: 'في الانتظار',
  processing: 'جاري المعالجة',
  ocr_complete: 'OCR مكتمل',
  extracted: 'مستخرج',
  review: 'قيد المراجعة',
  approved: 'مُعتمد',
  rejected: 'مرفوض',
  failed: 'فشل',
};

const statusColors: Record<string, string> = {
  queued: 'bg-gray-200 text-gray-800',
  processing: 'bg-blue-200 text-blue-800',
  ocr_complete: 'bg-cyan-200 text-cyan-800',
  extracted: 'bg-indigo-200 text-indigo-800',
  review: 'bg-yellow-200 text-yellow-800',
  approved: 'bg-green-200 text-green-800',
  rejected: 'bg-red-200 text-red-800',
  failed: 'bg-red-300 text-red-900',
};

const sourceLabels: Record<string, string> = {
  upload: 'رفع مباشر',
  bulk_scan: 'مسح جماعي',
  spreadsheet: 'جدول بيانات',
};

function BarChart({ data, labelMap }: { data: Record<string, number>; labelMap?: Record<string, string> }) {
  const entries = Object.entries(data).filter(([, v]) => v > 0);
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">لا توجد بيانات</p>;
  const max = Math.max(...entries.map(([, v]) => v));

  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-center gap-2">
          <span className="text-sm w-24 text-left truncate" title={labelMap?.[key] || key}>
            {labelMap?.[key] || key}
          </span>
          <div className="flex-1 bg-muted rounded-full h-6 overflow-hidden">
            <div
              className="bg-primary h-full rounded-full transition-all duration-500 flex items-center justify-end pe-2"
              style={{ width: `${Math.max(8, (value / max) * 100)}%` }}
            >
              <span className="text-xs text-primary-foreground font-medium">{value}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color = 'text-primary' }: {
  label: string; value: number | string; icon: any; color?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-4 px-4">
        <Icon size={28} className={color} />
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function IntelligenceReportsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = useCallback(() => {
    setLoading(true);
    setError('');
    apiService.getIntelligenceReports()
      .then(setData)
      .catch(() => setError('فشل تحميل التقارير'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold mb-1">تقارير ذكاء العقود</h1>
            <p className="text-muted-foreground">نظرة شاملة على حالة المعالجة والمخاطر والتصنيف</p>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData} className="flex items-center gap-1">
            <ArrowClockwise size={16} />
            تحديث
          </Button>
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
        ) : data ? (
          <>
            {/* Summary stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <StatCard label="إجمالي المستندات" value={data.total_documents} icon={FileText} color="text-blue-600" />
              <StatCard label="طابور المراجعة" value={data.review_queue_size} icon={Clock} color="text-yellow-600" />
              <StatCard label="عقود مرقمنة" value={data.contracts_digitized} icon={CheckCircle} color="text-green-600" />
              <StatCard label="مخاطر غير محلولة" value={data.risks_unresolved} icon={ShieldWarning} color="text-red-600" />
              <StatCard label="تكرارات معلقة" value={data.duplicates_pending} icon={CopySimple} color="text-purple-600" />
            </div>

            {/* Pipeline status + Import sources */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <ChartBar size={20} />
                    حالة خط المعالجة
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <BarChart data={data.status_breakdown} labelMap={statusLabels} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText size={20} />
                    مصادر الاستيراد
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <BarChart data={data.import_sources} labelMap={sourceLabels} />
                </CardContent>
              </Card>
            </div>

            {/* Classification + OCR */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">توزيع التصنيف</CardTitle>
                </CardHeader>
                <CardContent>
                  {Object.keys(data.classification_distribution || {}).length > 0 ? (
                    <BarChart data={data.classification_distribution} labelMap={typeLabels} />
                  ) : (
                    <p className="text-sm text-muted-foreground">لا توجد بيانات تصنيف بعد</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">جودة OCR</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <p className="text-xl font-bold text-green-600">{data.ocr_confidence?.high ?? 0}</p>
                      <p className="text-xs text-muted-foreground">عالية (&ge;70%)</p>
                    </div>
                    <div>
                      <p className="text-xl font-bold text-yellow-600">{data.ocr_confidence?.medium ?? 0}</p>
                      <p className="text-xs text-muted-foreground">متوسطة (30-70%)</p>
                    </div>
                    <div>
                      <p className="text-xl font-bold text-red-600">{data.ocr_confidence?.low ?? 0}</p>
                      <p className="text-xs text-muted-foreground">منخفضة (&lt;30%)</p>
                    </div>
                  </div>
                  {data.ocr_confidence?.average != null && (
                    <p className="text-sm text-center text-muted-foreground">
                      المتوسط: {(data.ocr_confidence.average * 100).toFixed(1)}%
                    </p>
                  )}
                  <div className="text-xs text-muted-foreground border-t pt-2">
                    <p>المحرك: <span className="font-mono">{data.ocr_engine?.engine}</span></p>
                    <p>Tesseract: {data.ocr_engine?.tesseract_available ? '✅ متوفر' : '❌ غير متوفر'}</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Risks */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <ShieldWarning size={20} />
                    المخاطر حسب الخطورة
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {Object.keys(data.risk_by_severity || {}).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(data.risk_by_severity).map(([severity, count]) => (
                        <div key={severity} className="flex items-center justify-between">
                          <Badge className={severityColors[severity] || 'bg-gray-200'}>
                            {severityLabels[severity] || severity}
                          </Badge>
                          <span className="text-lg font-bold">{count as number}</span>
                        </div>
                      ))}
                      <div className="border-t pt-2 mt-2 flex justify-between text-sm text-muted-foreground">
                        <span>محلول: {data.risks_resolved}</span>
                        <span>غير محلول: {data.risks_unresolved}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">لا توجد مخاطر</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">المخاطر حسب النوع</CardTitle>
                </CardHeader>
                <CardContent>
                  {Object.keys(data.risk_by_type || {}).length > 0 ? (
                    <BarChart data={data.risk_by_type} />
                  ) : (
                    <p className="text-sm text-muted-foreground">لا توجد بيانات</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Duplicates summary */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <CopySimple size={20} />
                  التكرارات
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{data.duplicates_total}</p>
                    <p className="text-sm text-muted-foreground">إجمالي</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-yellow-600">{data.duplicates_pending}</p>
                    <p className="text-sm text-muted-foreground">معلق</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-red-600">{data.duplicates_confirmed_same}</p>
                    <p className="text-sm text-muted-foreground">مؤكد متكرر</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-600">{data.duplicates_confirmed_different}</p>
                    <p className="text-sm text-muted-foreground">مؤكد مختلف</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Batch results */}
            {data.batch_results?.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">نتائج الاستيراد الجماعي</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-right">رقم الدفعة</TableHead>
                          <TableHead className="text-right">المصدر</TableHead>
                          <TableHead className="text-right">الإجمالي</TableHead>
                          <TableHead className="text-right">ناجح</TableHead>
                          <TableHead className="text-right">فاشل</TableHead>
                          <TableHead className="text-right">التاريخ</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.batch_results.map((b: any) => (
                          <TableRow key={b.batch_id}>
                            <TableCell className="font-mono text-xs">{b.batch_id}</TableCell>
                            <TableCell>{sourceLabels[b.source] || b.source}</TableCell>
                            <TableCell>{b.total}</TableCell>
                            <TableCell className="text-green-700">{b.successful}</TableCell>
                            <TableCell className={b.failed > 0 ? 'text-red-700 font-bold' : ''}>
                              {b.failed}
                            </TableCell>
                            <TableCell className="text-xs">
                              {b.created_at ? new Date(b.created_at).toLocaleDateString('ar') : '-'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        ) : null}
      </div>
    </Layout>
  );
}
