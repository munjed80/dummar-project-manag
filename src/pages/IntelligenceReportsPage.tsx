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
  CheckCircle, Clock, ArrowClockwise, DownloadSimple, FunnelSimple,
  MagnifyingGlass, X,
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

function TimeSeriesChart({ data, label }: { data: { date: string; count: number }[]; label: string }) {
  if (!data || data.length === 0) return <p className="text-sm text-muted-foreground">لا توجد بيانات زمنية</p>;
  const max = Math.max(...data.map(d => d.count), 1);

  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-muted-foreground mb-2">{label}</p>
      <div className="flex items-end gap-1 h-24 overflow-x-auto">
        {data.map((d, i) => (
          <div key={i} className="flex flex-col items-center min-w-[20px]" title={`${d.date}: ${d.count}`}>
            <div
              className="w-4 bg-primary rounded-t transition-all"
              style={{ height: `${Math.max(4, (d.count / max) * 80)}px` }}
            />
            {data.length <= 15 && (
              <span className="text-[9px] text-muted-foreground mt-0.5 rotate-[-45deg] origin-top-right w-12 truncate">
                {d.date?.slice(5) || ''}
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground mt-1">
        <span>{data[0]?.date || ''}</span>
        <span>{data[data.length - 1]?.date || ''}</span>
      </div>
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

interface Filters {
  date_from: string;
  date_to: string;
  ocr_status: string;
  review_status: string;
  classification_type: string;
  risk_severity: string;
  import_source: string;
  search: string;
}

const emptyFilters: Filters = {
  date_from: '', date_to: '', ocr_status: '', review_status: '',
  classification_type: '', risk_severity: '', import_source: '', search: '',
};

export default function IntelligenceReportsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [exportingCsv, setExportingCsv] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const activeFilterParams = useCallback(() => {
    const params: Record<string, string> = {};
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params[k] = v;
    });
    return params;
  }, [filters]);

  const hasActiveFilters = Object.values(filters).some(v => v !== '');

  const fetchData = useCallback(() => {
    setLoading(true);
    setError('');
    apiService.getIntelligenceReports(activeFilterParams())
      .then(setData)
      .catch(() => setError('فشل تحميل التقارير'))
      .finally(() => setLoading(false));
  }, [activeFilterParams]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleExportCsv = async () => {
    setExportingCsv(true);
    try {
      await apiService.downloadIntelligenceCsv({ section: 'all', ...activeFilterParams() });
    } catch { setError('فشل تصدير CSV'); }
    setExportingCsv(false);
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      await apiService.downloadIntelligencePdf(activeFilterParams());
    } catch { setError('فشل تصدير PDF'); }
    setExportingPdf(false);
  };

  const clearFilters = () => {
    setFilters(emptyFilters);
  };

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header with actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold mb-1">تقارير ذكاء العقود</h1>
            <p className="text-muted-foreground">نظرة شاملة على حالة المعالجة والمخاطر والتصنيف</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-1">
              <FunnelSimple size={16} />
              فلاتر
              {hasActiveFilters && <Badge variant="secondary" className="text-xs ms-1">{Object.values(filters).filter(v => v).length}</Badge>}
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportCsv} disabled={exportingCsv} className="flex items-center gap-1">
              <DownloadSimple size={16} />
              {exportingCsv ? 'جاري...' : 'CSV'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportPdf} disabled={exportingPdf} className="flex items-center gap-1">
              <DownloadSimple size={16} />
              {exportingPdf ? 'جاري...' : 'PDF'}
            </Button>
            <Button variant="outline" size="sm" onClick={fetchData} className="flex items-center gap-1">
              <ArrowClockwise size={16} />
              تحديث
            </Button>
          </div>
        </div>

        {/* Filters panel */}
        {showFilters && (
          <Card>
            <CardContent className="py-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold flex items-center gap-1">
                  <FunnelSimple size={18} />
                  تصفية التقارير
                </h3>
                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={clearFilters} className="flex items-center gap-1 text-xs">
                    <X size={14} />
                    مسح الكل
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* Date range */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">من تاريخ</label>
                  <input
                    type="date" value={filters.date_from}
                    onChange={e => updateFilter('date_from', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">إلى تاريخ</label>
                  <input
                    type="date" value={filters.date_to}
                    onChange={e => updateFilter('date_to', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  />
                </div>

                {/* OCR Status */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">حالة OCR</label>
                  <select
                    value={filters.ocr_status}
                    onChange={e => updateFilter('ocr_status', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  >
                    <option value="">الكل</option>
                    <option value="complete">مكتمل</option>
                    <option value="pending">قيد الانتظار</option>
                    <option value="failed">فشل</option>
                  </select>
                </div>

                {/* Review Status */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">حالة المراجعة</label>
                  <select
                    value={filters.review_status}
                    onChange={e => updateFilter('review_status', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  >
                    <option value="">الكل</option>
                    <option value="queued">في الانتظار</option>
                    <option value="processing">جاري المعالجة</option>
                    <option value="ocr_complete">OCR مكتمل</option>
                    <option value="extracted">مستخرج</option>
                    <option value="review">قيد المراجعة</option>
                    <option value="approved">مُعتمد</option>
                    <option value="rejected">مرفوض</option>
                    <option value="failed">فشل</option>
                  </select>
                </div>

                {/* Classification */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">التصنيف</label>
                  <select
                    value={filters.classification_type}
                    onChange={e => updateFilter('classification_type', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  >
                    <option value="">الكل</option>
                    {Object.entries(typeLabels).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>

                {/* Risk Severity */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">خطورة المخاطر</label>
                  <select
                    value={filters.risk_severity}
                    onChange={e => updateFilter('risk_severity', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  >
                    <option value="">الكل</option>
                    {Object.entries(severityLabels).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>

                {/* Import Source */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">مصدر الاستيراد</label>
                  <select
                    value={filters.import_source}
                    onChange={e => updateFilter('import_source', e.target.value)}
                    className="w-full border rounded px-2 py-1.5 text-sm bg-background"
                  >
                    <option value="">الكل</option>
                    {Object.entries(sourceLabels).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>

                {/* Keyword Search */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">بحث بالكلمة</label>
                  <div className="relative">
                    <MagnifyingGlass size={14} className="absolute start-2 top-2 text-muted-foreground" />
                    <input
                      type="text" value={filters.search} placeholder="اسم ملف، رقم دفعة..."
                      onChange={e => updateFilter('search', e.target.value)}
                      className="w-full border rounded ps-7 pe-2 py-1.5 text-sm bg-background"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button size="sm" onClick={fetchData}>
                  تطبيق الفلاتر
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

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

            {/* Time-series charts */}
            {(data.documents_over_time?.length > 0 || data.risks_over_time?.length > 0) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {data.documents_over_time?.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <ChartBar size={20} />
                        المستندات المُعالجة بمرور الوقت
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <TimeSeriesChart data={data.documents_over_time} label="" />
                    </CardContent>
                  </Card>
                )}
                {data.risks_over_time?.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <ShieldWarning size={20} />
                        المخاطر المكتشفة بمرور الوقت
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <TimeSeriesChart data={data.risks_over_time} label="" />
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

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
