import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService, ApiError } from '@/services/api';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import { MagnifyingGlass, Spinner, Warning, Plus } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { describeLoadError } from '@/lib/loadError';

const statusLabels: Record<string, string> = {
  draft: 'مسودة', under_review: 'قيد المراجعة', approved: 'مُعتمد',
  active: 'نشط', suspended: 'معلق', completed: 'مكتمل',
  expired: 'منتهي', cancelled: 'ملغى',
};

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800', under_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800', active: 'bg-green-100 text-green-800',
  suspended: 'bg-orange-100 text-orange-800', completed: 'bg-emerald-100 text-emerald-800',
  expired: 'bg-red-100 text-red-800', cancelled: 'bg-red-100 text-red-800',
};

const typeLabels: Record<string, string> = {
  construction: 'إنشاء', maintenance: 'صيانة', supply: 'توريد',
  consulting: 'استشارات', other: 'أخرى',
};

function formatValue(value: number | string | null | undefined): string {
  if (value == null) return '-';
  return Number(value).toLocaleString('en-US');
}

const PAGE_SIZE = 15;
const todayIso = new Date().toISOString().slice(0, 10);

const emptyContractForm = {
  contract_number: '',
  title: '',
  contractor_name: '',
  contractor_contact: '',
  contract_type: 'maintenance',
  contract_value: '',
  start_date: todayIso,
  end_date: todayIso,
  scope_description: '',
  related_areas: '',
  project_id: 'none',
};

export default function ContractsListPage() {
  const navigate = useNavigate();
  const { canCreateContracts } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProject = searchParams.get('project_id') || 'all';
  const [contracts, setContracts] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState(initialProject);
  const [page, setPage] = useState(0);
  const [reloadToken, setReloadToken] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [createSaving, setCreateSaving] = useState(false);
  const [createErrors, setCreateErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState({ ...emptyContractForm });

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (projectFilter === 'all') next.delete('project_id');
    else next.set('project_id', projectFilter);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectFilter]);

  useEffect(() => {
    apiService.getProjects({ limit: 200 })
      .then((data) => setProjects(data.items || []))
      .catch((err) => {
        if (import.meta.env?.DEV) console.warn('[load:projects-selector]', err);
        setProjects([]);
      });
  }, []);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (typeFilter !== 'all') params.contract_type = typeFilter;
    if (projectFilter !== 'all') params.project_id = Number(projectFilter);
    if (search) params.search = search;
    apiService.getContracts(params)
      .then((data) => {
        setContracts(data.items);
        setTotalCount(data.total_count);
      })
      .catch((err) => setError(describeLoadError(err, 'العقود التشغيلية').message))
      .finally(() => setLoading(false));
  }, [statusFilter, typeFilter, projectFilter, search, page, reloadToken]);

  const projectMap = Object.fromEntries(projects.map((p: any) => [p.id, p.title]));

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const setFormField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setCreateErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const openCreateDialog = () => {
    setForm({ ...emptyContractForm, project_id: projectFilter === 'all' ? 'none' : projectFilter });
    setCreateErrors({});
    setCreateOpen(true);
  };

  const validateCreate = () => {
    const nextErrors: Record<string, string> = {};
    if (!form.contract_number.trim()) nextErrors.contract_number = 'رقم العقد مطلوب';
    if (!form.title.trim()) nextErrors.title = 'عنوان العقد مطلوب';
    if (!form.contractor_name.trim()) nextErrors.contractor_name = 'اسم المقاول مطلوب';
    if (!form.contract_value.trim()) nextErrors.contract_value = 'قيمة العقد مطلوبة';
    else if (isNaN(Number(form.contract_value))) nextErrors.contract_value = 'قيمة العقد يجب أن تكون رقماً';
    if (!form.start_date) nextErrors.start_date = 'تاريخ البدء مطلوب';
    if (!form.end_date) nextErrors.end_date = 'تاريخ الانتهاء مطلوب';
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      nextErrors.end_date = 'تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء';
    }
    if (!form.scope_description.trim()) nextErrors.scope_description = 'نطاق العمل مطلوب';
    return nextErrors;
  };

  const handleCreate = async () => {
    const nextErrors = validateCreate();
    if (Object.keys(nextErrors).length > 0) {
      setCreateErrors(nextErrors);
      return;
    }
    setCreateSaving(true);
    try {
      const created = await apiService.createContract({
        contract_number: form.contract_number.trim(),
        title: form.title.trim(),
        contractor_name: form.contractor_name.trim(),
        contractor_contact: form.contractor_contact.trim() || null,
        contract_type: form.contract_type,
        contract_value: Number(form.contract_value),
        start_date: form.start_date,
        end_date: form.end_date,
        scope_description: form.scope_description.trim(),
        related_areas: form.related_areas.trim() || null,
        project_id: form.project_id === 'none' ? null : Number(form.project_id),
      });
      toast.success('تمت إضافة عقد تشغيلي جديد');
      setCreateOpen(false);
      navigate(`/contracts/${created.id}`);
    } catch (err) {
      const message = err instanceof ApiError
        ? (err.detail ? `فشل إضافة العقد: ${err.detail}` : 'فشل إضافة العقد')
        : 'فشل إضافة العقد';
      toast.error(message);
    } finally {
      setCreateSaving(false);
    }
  };

  return (
    <Layout>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <CardTitle className="text-2xl">العقود التشغيلية</CardTitle>
            {canCreateContracts && (
              <Button className="gap-2" onClick={openCreateDialog}>
                <Plus size={18} />
                إضافة عقد تشغيلي
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث في العقود التشغيلية برقم العقد أو العنوان أو المقاول..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                className="pr-10"
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الحالات</SelectItem>
                  {Object.entries(statusLabels).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="النوع" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الأنواع</SelectItem>
                  {Object.entries(typeLabels).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={projectFilter} onValueChange={(v) => { setProjectFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="المشروع" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع المشاريع</SelectItem>
                  {projects.map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {error && (
            <div className="text-center py-8 text-destructive flex flex-col items-center gap-2">
              <Warning size={32} />
              <p>{error}</p>
              <Button variant="outline" size="sm" onClick={() => setReloadToken((t) => t + 1)}>
                إعادة المحاولة
              </Button>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner className="animate-spin" size={32} />
            </div>
          ) : (
            <>
              {/* Desktop table view */}
              <div className="responsive-table-desktop">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">رقم العقد</TableHead>
                      <TableHead className="text-right">العنوان</TableHead>
                      <TableHead className="text-right">المقاول</TableHead>
                      <TableHead className="text-right">النوع</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-right">القيمة</TableHead>
                      <TableHead className="text-right">الحالة</TableHead>
                      <TableHead className="text-right">تاريخ الانتهاء</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {contracts.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                          لا توجد عقود تشغيلية
                        </TableCell>
                      </TableRow>
                    ) : (
                      contracts.map((c) => (
                        <TableRow
                          key={c.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/contracts/${c.id}`)}
                        >
                          <TableCell className="font-mono">{c.contract_number}</TableCell>
                          <TableCell>{c.title}</TableCell>
                          <TableCell>{c.contractor_name}</TableCell>
                          <TableCell>{typeLabels[c.contract_type] || c.contract_type || '-'}</TableCell>
                          <TableCell>{c.project_id ? (projectMap[c.project_id] || `#${c.project_id}`) : '-'}</TableCell>
                          <TableCell>{formatValue(c.contract_value)}</TableCell>
                          <TableCell>
                            <Badge className={statusColors[c.status] || 'bg-gray-100 text-gray-800'}>
                              {statusLabels[c.status] || c.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{c.end_date ? format(new Date(c.end_date), 'yyyy/MM/dd') : '-'}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {contracts.length === 0 ? (
                  <p className="text-center py-8 text-muted-foreground">لا توجد عقود تشغيلية</p>
                ) : (
                  contracts.map((c) => (
                    <div
                      key={c.id}
                      className="border rounded-lg p-3 cursor-pointer hover:bg-muted/50 active:bg-muted/70 transition-colors"
                      onClick={() => navigate(`/contracts/${c.id}`)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-sm font-bold text-primary">{c.contract_number}</span>
                        <Badge className={statusColors[c.status] || 'bg-gray-100 text-gray-800'}>
                          {statusLabels[c.status] || c.status}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium mb-1">{c.title}</p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{c.contractor_name}</span>
                        <span>•</span>
                        <span>{typeLabels[c.contract_type] || c.contract_type || '-'}</span>
                        <span>•</span>
                        <span>{formatValue(c.contract_value)}</span>
                        {c.project_id && (
                          <>
                            <span>•</span>
                            <span>{projectMap[c.project_id] || `مشروع #${c.project_id}`}</span>
                          </>
                        )}
                        {c.end_date && (
                          <>
                            <span>•</span>
                            <span>ينتهي: {format(new Date(c.end_date), 'yyyy/MM/dd')}</span>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>السابق</Button>
                  <span className="text-sm text-muted-foreground">
                    صفحة {page + 1} من {totalPages} ({totalCount} عقد)
                  </span>
                  <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>التالي</Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>إضافة عقد تشغيلي جديد</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 overflow-y-auto px-1 py-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>رقم العقد *</Label>
                <Input
                  value={form.contract_number}
                  onChange={(e) => setFormField('contract_number', e.target.value)}
                  className={createErrors.contract_number ? 'border-destructive' : ''}
                />
                {createErrors.contract_number && <p className="text-xs text-destructive">{createErrors.contract_number}</p>}
              </div>
              <div className="space-y-1">
                <Label>نوع العقد *</Label>
                <Select value={form.contract_type} onValueChange={(v) => setFormField('contract_type', v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(typeLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label>عنوان العقد *</Label>
              <Input
                value={form.title}
                onChange={(e) => setFormField('title', e.target.value)}
                className={createErrors.title ? 'border-destructive' : ''}
              />
              {createErrors.title && <p className="text-xs text-destructive">{createErrors.title}</p>}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>اسم المقاول *</Label>
                <Input
                  value={form.contractor_name}
                  onChange={(e) => setFormField('contractor_name', e.target.value)}
                  className={createErrors.contractor_name ? 'border-destructive' : ''}
                />
                {createErrors.contractor_name && <p className="text-xs text-destructive">{createErrors.contractor_name}</p>}
              </div>
              <div className="space-y-1">
                <Label>بيانات التواصل</Label>
                <Input
                  value={form.contractor_contact}
                  onChange={(e) => setFormField('contractor_contact', e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1 sm:col-span-1">
                <Label>قيمة العقد *</Label>
                <Input
                  type="number"
                  value={form.contract_value}
                  onChange={(e) => setFormField('contract_value', e.target.value)}
                  className={createErrors.contract_value ? 'border-destructive' : ''}
                />
                {createErrors.contract_value && <p className="text-xs text-destructive">{createErrors.contract_value}</p>}
              </div>
              <div className="space-y-1 sm:col-span-1">
                <Label>تاريخ البدء *</Label>
                <Input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setFormField('start_date', e.target.value)}
                  className={createErrors.start_date ? 'border-destructive' : ''}
                />
                {createErrors.start_date && <p className="text-xs text-destructive">{createErrors.start_date}</p>}
              </div>
              <div className="space-y-1 sm:col-span-1">
                <Label>تاريخ الانتهاء *</Label>
                <Input
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setFormField('end_date', e.target.value)}
                  className={createErrors.end_date ? 'border-destructive' : ''}
                />
                {createErrors.end_date && <p className="text-xs text-destructive">{createErrors.end_date}</p>}
              </div>
            </div>

            <div className="space-y-1">
              <Label>المشروع المرتبط</Label>
              <Select value={form.project_id} onValueChange={(v) => setFormField('project_id', v)}>
                <SelectTrigger>
                  <SelectValue placeholder="اختياري" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">بدون مشروع</SelectItem>
                  {projects.map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label>نطاق العمل *</Label>
              <Textarea
                rows={3}
                value={form.scope_description}
                onChange={(e) => setFormField('scope_description', e.target.value)}
                className={createErrors.scope_description ? 'border-destructive' : ''}
              />
              {createErrors.scope_description && <p className="text-xs text-destructive">{createErrors.scope_description}</p>}
            </div>

            <div className="space-y-1">
              <Label>المناطق المرتبطة</Label>
              <Input
                value={form.related_areas}
                onChange={(e) => setFormField('related_areas', e.target.value)}
                placeholder="مثال: المنطقة الشمالية، السوق الرئيسي"
              />
            </div>
          </div>
          <DialogFooter className="border-t pt-3 mt-1 bg-background">
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={createSaving}>
              إلغاء
            </Button>
            <Button onClick={handleCreate} disabled={createSaving}>
              {createSaving && <Spinner className="animate-spin ml-1" size={16} />}
              إضافة العقد
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
