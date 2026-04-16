import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Spinner, ChartBar, MagnifyingGlass, DownloadSimple } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const complaintStatusLabels: Record<string, string> = {
  new: 'جديدة', under_review: 'قيد المراجعة', assigned: 'مُعينة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};
const taskStatusLabels: Record<string, string> = {
  pending: 'معلقة', assigned: 'مُعينة', in_progress: 'قيد التنفيذ',
  completed: 'مكتملة', cancelled: 'ملغاة',
};
const contractStatusLabels: Record<string, string> = {
  draft: 'مسودة', under_review: 'قيد المراجعة', approved: 'مُعتمد',
  active: 'نشط', suspended: 'معلق', completed: 'مكتمل',
  expired: 'منتهي', cancelled: 'ملغى',
};
const complaintTypeLabels: Record<string, string> = {
  infrastructure: 'البنية التحتية', cleaning: 'النظافة', electricity: 'الكهرباء',
  water: 'المياه', roads: 'الطرق', lighting: 'الإنارة', other: 'أخرى',
};
const contractTypeLabels: Record<string, string> = {
  construction: 'إنشاء', maintenance: 'صيانة', supply: 'توريد',
  consulting: 'استشارات', other: 'أخرى',
};
const priorityLabels: Record<string, string> = {
  low: 'منخفضة', medium: 'متوسطة', high: 'عالية', urgent: 'عاجلة',
};

function SummaryCard({ title, value, color }: { title: string; value: number; color: string }) {
  return (
    <Card className={`border-r-4 ${color}`}>
      <CardContent className="py-4">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}

function BreakdownList({ items, labelMap }: { items: { status?: string; type?: string; area_name?: string; count: number }[]; labelMap?: Record<string, string> }) {
  if (!items || items.length === 0) return <p className="text-muted-foreground text-sm">لا توجد بيانات</p>;
  return (
    <div className="space-y-1">
      {items.map((item, idx) => {
        const key = item.status || item.type || item.area_name || String(idx);
        const label = labelMap ? (labelMap[key] || key) : key;
        return (
          <div key={idx} className="flex justify-between text-sm">
            <span>{label}</span>
            <Badge variant="secondary">{item.count}</Badge>
          </div>
        );
      })}
    </div>
  );
}

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState('summary');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Summary data
  const [summary, setSummary] = useState<any>(null);

  // Filter state
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [areaFilter, setAreaFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [complaintTypeFilter, setComplaintTypeFilter] = useState('all');
  const [contractTypeFilter, setContractTypeFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [areas, setAreas] = useState<any[]>([]);
  const [csvLoading, setCsvLoading] = useState(false);

  // Detail tabs data
  const [complaints, setComplaints] = useState<any[]>([]);
  const [complaintsTotal, setComplaintsTotal] = useState(0);
  const [tasks, setTasks] = useState<any[]>([]);
  const [tasksTotal, setTasksTotal] = useState(0);
  const [contracts, setContracts] = useState<any[]>([]);
  const [contractsTotal, setContractsTotal] = useState(0);
  const [detailSearch, setDetailSearch] = useState('');
  const [detailPage, setDetailPage] = useState(0);

  const PAGE_SIZE = 20;

  useEffect(() => {
    apiService.getAreas().then(setAreas).catch(() => {});
  }, []);

  const buildFilterParams = () => {
    const params: Record<string, any> = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (areaFilter !== 'all') params.area_id = Number(areaFilter);
    if (statusFilter !== 'all') params.status = statusFilter;
    if (complaintTypeFilter !== 'all') params.complaint_type = complaintTypeFilter;
    if (contractTypeFilter !== 'all') params.contract_type = contractTypeFilter;
    if (priorityFilter !== 'all') params.priority = priorityFilter;
    return params;
  };

  const handleCsvDownload = async (entity: 'complaints' | 'tasks' | 'contracts') => {
    setCsvLoading(true);
    try {
      const params = buildFilterParams();
      if (detailSearch) params.search = detailSearch;
      await apiService.downloadReportCsv(entity, params);
    } catch {
      toast.error('فشل تنزيل ملف CSV. يرجى المحاولة مرة أخرى.');
    } finally {
      setCsvLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    setError('');
    const params = buildFilterParams();

    if (activeTab === 'summary') {
      apiService.getReportSummary(params)
        .then(setSummary)
        .catch(() => setError('فشل تحميل الملخص'))
        .finally(() => setLoading(false));
    } else if (activeTab === 'complaints') {
      apiService.getReportComplaints({ ...params, search: detailSearch || undefined, skip: detailPage * PAGE_SIZE, limit: PAGE_SIZE })
        .then((d: any) => { setComplaints(d.items); setComplaintsTotal(d.total_count); })
        .catch(() => setError('فشل تحميل بيانات الشكاوى'))
        .finally(() => setLoading(false));
    } else if (activeTab === 'tasks') {
      apiService.getReportTasks({ ...params, search: detailSearch || undefined, skip: detailPage * PAGE_SIZE, limit: PAGE_SIZE })
        .then((d: any) => { setTasks(d.items); setTasksTotal(d.total_count); })
        .catch(() => setError('فشل تحميل بيانات المهام'))
        .finally(() => setLoading(false));
    } else if (activeTab === 'contracts') {
      apiService.getReportContracts({ ...params, search: detailSearch || undefined, skip: detailPage * PAGE_SIZE, limit: PAGE_SIZE })
        .then((d: any) => { setContracts(d.items); setContractsTotal(d.total_count); })
        .catch(() => setError('فشل تحميل بيانات العقود'))
        .finally(() => setLoading(false));
    }
  }, [activeTab, dateFrom, dateTo, areaFilter, statusFilter, complaintTypeFilter, contractTypeFilter, priorityFilter, detailSearch, detailPage]);

  const renderPagination = (total: number) => {
    const totalPages = Math.ceil(total / PAGE_SIZE);
    if (totalPages <= 1) return null;
    return (
      <div className="flex items-center justify-center gap-2 pt-4">
        <Button variant="outline" size="sm" disabled={detailPage === 0} onClick={() => setDetailPage(p => p - 1)}>السابق</Button>
        <span className="text-sm text-muted-foreground">صفحة {detailPage + 1} من {totalPages} ({total} سجل)</span>
        <Button variant="outline" size="sm" disabled={detailPage >= totalPages - 1} onClick={() => setDetailPage(p => p + 1)}>التالي</Button>
      </div>
    );
  };

  return (
    <Layout>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2">
              <ChartBar size={24} />
              التقارير
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Filters */}
            <div className="flex flex-wrap gap-3 mb-6">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">من تاريخ</label>
                <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setDetailPage(0); }} className="w-[160px]" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">إلى تاريخ</label>
                <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setDetailPage(0); }} className="w-[160px]" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">المنطقة</label>
                <Select value={areaFilter} onValueChange={(v) => { setAreaFilter(v); setDetailPage(0); }}>
                  <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع المناطق</SelectItem>
                    {areas.map((a: any) => (
                      <SelectItem key={a.id} value={String(a.id)}>{a.name_ar || a.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">الحالة</label>
                <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setDetailPage(0); }}>
                  <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الحالات</SelectItem>
                    {Object.entries(complaintStatusLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">نوع الشكوى</label>
                <Select value={complaintTypeFilter} onValueChange={(v) => { setComplaintTypeFilter(v); setDetailPage(0); }}>
                  <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الأنواع</SelectItem>
                    {Object.entries(complaintTypeLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">نوع العقد</label>
                <Select value={contractTypeFilter} onValueChange={(v) => { setContractTypeFilter(v); setDetailPage(0); }}>
                  <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الأنواع</SelectItem>
                    {Object.entries(contractTypeLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">الأولوية</label>
                <Select value={priorityFilter} onValueChange={(v) => { setPriorityFilter(v); setDetailPage(0); }}>
                  <SelectTrigger className="w-[140px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">الكل</SelectItem>
                    {Object.entries(priorityLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setDetailPage(0); setDetailSearch(''); }}>
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="summary">ملخص عام</TabsTrigger>
                <TabsTrigger value="complaints">الشكاوى</TabsTrigger>
                <TabsTrigger value="tasks">المهام</TabsTrigger>
                <TabsTrigger value="contracts">العقود</TabsTrigger>
              </TabsList>

              {error && <div className="text-center py-8 text-destructive">{error}</div>}

              {loading ? (
                <div className="flex justify-center py-12"><Spinner className="animate-spin" size={32} /></div>
              ) : (
                <>
                  {/* Summary Tab */}
                  <TabsContent value="summary">
                    {summary && (
                      <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <SummaryCard title="إجمالي الشكاوى" value={summary.complaints?.total || 0} color="border-r-blue-500" />
                          <SummaryCard title="إجمالي المهام" value={summary.tasks?.total || 0} color="border-r-green-500" />
                          <SummaryCard title="إجمالي العقود" value={summary.contracts?.total || 0} color="border-r-purple-500" />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <Card>
                            <CardHeader><CardTitle className="text-lg">الشكاوى حسب الحالة</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.complaints?.by_status || []} labelMap={complaintStatusLabels} /></CardContent>
                          </Card>
                          <Card>
                            <CardHeader><CardTitle className="text-lg">الشكاوى حسب النوع</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.complaints?.by_type || []} labelMap={complaintTypeLabels} /></CardContent>
                          </Card>
                          <Card>
                            <CardHeader><CardTitle className="text-lg">الشكاوى حسب المنطقة</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.complaints?.by_area || []} /></CardContent>
                          </Card>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <Card>
                            <CardHeader><CardTitle className="text-lg">المهام حسب الحالة</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.tasks?.by_status || []} labelMap={taskStatusLabels} /></CardContent>
                          </Card>
                          <Card>
                            <CardHeader><CardTitle className="text-lg">المهام حسب المنطقة</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.tasks?.by_area || []} /></CardContent>
                          </Card>
                          <Card>
                            <CardHeader><CardTitle className="text-lg">العقود حسب الحالة</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.contracts?.by_status || []} labelMap={contractStatusLabels} /></CardContent>
                          </Card>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <Card>
                            <CardHeader><CardTitle className="text-lg">العقود حسب النوع</CardTitle></CardHeader>
                            <CardContent><BreakdownList items={summary.contracts?.by_type || []} labelMap={contractTypeLabels} /></CardContent>
                          </Card>
                        </div>
                      </div>
                    )}
                  </TabsContent>

                  {/* Complaints Tab */}
                  <TabsContent value="complaints">
                    <div className="space-y-4">
                      <div className="flex items-end gap-3">
                        <div className="relative flex-1 max-w-sm">
                          <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                          <Input
                            placeholder="بحث في الشكاوى..."
                            value={detailSearch}
                            onChange={(e) => { setDetailSearch(e.target.value); setDetailPage(0); }}
                            className="pr-10"
                          />
                        </div>
                        <Button variant="outline" size="sm" disabled={csvLoading} onClick={() => handleCsvDownload('complaints')}>
                          <DownloadSimple size={16} className="ml-1" />
                          تصدير CSV
                        </Button>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">رقم التتبع</TableHead>
                            <TableHead className="text-right">مقدم الشكوى</TableHead>
                            <TableHead className="text-right">النوع</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">الأولوية</TableHead>
                            <TableHead className="text-right">التاريخ</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {complaints.length === 0 ? (
                            <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">لا توجد بيانات</TableCell></TableRow>
                          ) : complaints.map((c: any) => (
                            <TableRow key={c.id}>
                              <TableCell className="font-mono">{c.tracking_number}</TableCell>
                              <TableCell>{c.full_name}</TableCell>
                              <TableCell>{complaintTypeLabels[c.complaint_type] || c.complaint_type}</TableCell>
                              <TableCell><Badge variant="secondary">{complaintStatusLabels[c.status] || c.status}</Badge></TableCell>
                              <TableCell><Badge variant="outline">{priorityLabels[c.priority] || c.priority}</Badge></TableCell>
                              <TableCell>{c.created_at ? format(new Date(c.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                      {renderPagination(complaintsTotal)}
                    </div>
                  </TabsContent>

                  {/* Tasks Tab */}
                  <TabsContent value="tasks">
                    <div className="space-y-4">
                      <div className="flex items-end gap-3">
                        <div className="relative flex-1 max-w-sm">
                          <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                          <Input
                            placeholder="بحث في المهام..."
                            value={detailSearch}
                            onChange={(e) => { setDetailSearch(e.target.value); setDetailPage(0); }}
                            className="pr-10"
                          />
                        </div>
                        <Button variant="outline" size="sm" disabled={csvLoading} onClick={() => handleCsvDownload('tasks')}>
                          <DownloadSimple size={16} className="ml-1" />
                          تصدير CSV
                        </Button>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">العنوان</TableHead>
                            <TableHead className="text-right">المصدر</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">الأولوية</TableHead>
                            <TableHead className="text-right">تاريخ الاستحقاق</TableHead>
                            <TableHead className="text-right">التاريخ</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {tasks.length === 0 ? (
                            <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">لا توجد بيانات</TableCell></TableRow>
                          ) : tasks.map((t: any) => (
                            <TableRow key={t.id}>
                              <TableCell>{t.title}</TableCell>
                              <TableCell>{t.source_type === 'complaint' ? 'شكوى' : t.source_type === 'contract' ? 'عقد' : 'داخلي'}</TableCell>
                              <TableCell><Badge variant="secondary">{taskStatusLabels[t.status] || t.status}</Badge></TableCell>
                              <TableCell><Badge variant="outline">{priorityLabels[t.priority] || t.priority}</Badge></TableCell>
                              <TableCell>{t.due_date ? format(new Date(t.due_date), 'yyyy/MM/dd') : '-'}</TableCell>
                              <TableCell>{t.created_at ? format(new Date(t.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                      {renderPagination(tasksTotal)}
                    </div>
                  </TabsContent>

                  {/* Contracts Tab */}
                  <TabsContent value="contracts">
                    <div className="space-y-4">
                      <div className="flex items-end gap-3">
                        <div className="relative flex-1 max-w-sm">
                          <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                          <Input
                            placeholder="بحث في العقود..."
                            value={detailSearch}
                            onChange={(e) => { setDetailSearch(e.target.value); setDetailPage(0); }}
                            className="pr-10"
                          />
                        </div>
                        <Button variant="outline" size="sm" disabled={csvLoading} onClick={() => handleCsvDownload('contracts')}>
                          <DownloadSimple size={16} className="ml-1" />
                          تصدير CSV
                        </Button>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">رقم العقد</TableHead>
                            <TableHead className="text-right">العنوان</TableHead>
                            <TableHead className="text-right">المقاول</TableHead>
                            <TableHead className="text-right">النوع</TableHead>
                            <TableHead className="text-right">القيمة</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">تاريخ الانتهاء</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {contracts.length === 0 ? (
                            <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">لا توجد بيانات</TableCell></TableRow>
                          ) : contracts.map((c: any) => (
                            <TableRow key={c.id}>
                              <TableCell className="font-mono">{c.contract_number}</TableCell>
                              <TableCell>{c.title}</TableCell>
                              <TableCell>{c.contractor_name}</TableCell>
                              <TableCell>{contractTypeLabels[c.contract_type] || c.contract_type}</TableCell>
                              <TableCell>{c.contract_value ? Number(c.contract_value).toLocaleString('en-US') : '-'}</TableCell>
                              <TableCell><Badge variant="secondary">{contractStatusLabels[c.status] || c.status}</Badge></TableCell>
                              <TableCell>{c.end_date ? format(new Date(c.end_date), 'yyyy/MM/dd') : '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                      {renderPagination(contractsTotal)}
                    </div>
                  </TabsContent>
                </>
              )}
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
