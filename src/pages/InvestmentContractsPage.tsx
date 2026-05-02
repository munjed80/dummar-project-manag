import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService, ApiError } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { MagnifyingGlass, Spinner, Plus, FileText, PencilSimple, Trash } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';
import { FileUpload } from '@/components/FileUpload';
import {
  DataTableShell, DataToolbar, StatusBadge,
  EmptyState, ErrorState, LoadingSkeleton, PaginationBar, MobileEntityCard,
  type StatusTone,
} from '@/components/data';

// ── Lookups ───────────────────────────────────────────────────────────────

const INVESTMENT_TYPE_LABELS: Record<string, string> = {
  lease: 'إيجار',
  investment: 'استثمار',
  usufruct: 'حق انتفاع',
  partnership: 'شراكة',
  other: 'غير ذلك',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'فعال',
  near_expiry: 'قارب على الانتهاء',
  expired: 'منتهي',
  cancelled: 'ملغى',
};

const STATUS_TONES: Record<string, StatusTone> = {
  active: 'success',
  near_expiry: 'warning',
  expired: 'danger',
  cancelled: 'neutral',
};

// Map computed expiry_alert bucket to a small in-row badge.
const EXPIRY_TONES: Record<string, { label: string; tone: StatusTone }> = {
  expired: { label: 'منتهي', tone: 'danger' },
  '30': { label: 'يقل عن 30 يوم', tone: 'danger' },
  '60': { label: 'يقل عن 60 يوم', tone: 'warning' },
  '90': { label: 'يقل عن 90 يوم', tone: 'warning' },
};

// Legacy alias kept for backwards-compat with existing exports.
const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-50 text-emerald-700',
  near_expiry: 'bg-amber-50 text-amber-700',
  expired: 'bg-red-50 text-red-700',
  cancelled: 'bg-slate-100 text-slate-700',
};

const EXPIRY_BADGE: Record<string, { label: string; cls: string }> = {
  expired: { label: 'منتهي', cls: 'bg-red-50 text-red-700' },
  '30': { label: 'يقل عن 30 يوم', cls: 'bg-red-50 text-red-700' },
  '60': { label: 'يقل عن 60 يوم', cls: 'bg-amber-50 text-amber-700' },
  '90': { label: 'يقل عن 90 يوم', cls: 'bg-amber-50 text-amber-700' },
};

const PAGE_SIZE = 15;

// Typed attachment slots (keyed in the contract record).
const ATTACHMENT_SLOTS: { field: string; label: string }[] = [
  { field: 'contract_copy', label: 'نسخة العقد' },
  { field: 'terms_booklet', label: 'نسخة دفتر الشروط' },
  { field: 'investor_id_copy', label: 'صورة هوية المستثمر' },
  { field: 'owner_id_copy', label: 'صورة هوية المالك' },
  { field: 'ownership_proof', label: 'وثيقة / سند ملكية العقار' },
  { field: 'handover_report', label: 'محضر تسليم العقار' },
];

// ── Empty form ─────────────────────────────────────────────────────────────

const emptyForm = {
  contract_number: '',
  property_id: '',
  investor_name: '',
  investor_contact: '',
  investment_type: 'lease',
  start_date: '',
  end_date: '',
  contract_value: '',
  contract_copy: '',
  terms_booklet: '',
  investor_id_copy: '',
  owner_id_copy: '',
  ownership_proof: '',
  handover_report: '',
  handover_property_images: [] as string[],
  financial_documents: [] as string[],
  additional_attachments: [] as string[],
  notes: '',
};

// ── Form dialog ───────────────────────────────────────────────────────────

interface ContractFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editData?: any;
  properties: any[];
  onSuccess: () => void;
}

function ContractFormDialog({ open, onOpenChange, editData, properties, onSuccess }: ContractFormDialogProps) {
  const isEdit = !!editData;
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      if (editData) {
        setForm({
          contract_number: editData.contract_number || '',
          property_id: editData.property_id !== undefined ? String(editData.property_id) : '',
          investor_name: editData.investor_name || '',
          investor_contact: editData.investor_contact || '',
          investment_type: editData.investment_type || 'lease',
          start_date: editData.start_date || '',
          end_date: editData.end_date || '',
          contract_value: editData.contract_value !== undefined && editData.contract_value !== null
            ? String(editData.contract_value)
            : '',
          contract_copy: editData.contract_copy || '',
          terms_booklet: editData.terms_booklet || '',
          investor_id_copy: editData.investor_id_copy || '',
          owner_id_copy: editData.owner_id_copy || '',
          ownership_proof: editData.ownership_proof || '',
          handover_report: editData.handover_report || '',
          handover_property_images: Array.isArray(editData.handover_property_images) ? editData.handover_property_images : [],
          financial_documents: Array.isArray(editData.financial_documents) ? editData.financial_documents : [],
          additional_attachments: Array.isArray(editData.additional_attachments) ? editData.additional_attachments : [],
          notes: editData.notes || '',
        });
      } else {
        setForm({ ...emptyForm });
      }
      setErrors({});
    }
  }, [open, editData]);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.contract_number.trim()) e.contract_number = 'رقم العقد مطلوب';
    if (!form.property_id) e.property_id = 'العقار المرتبط مطلوب';
    if (!form.investor_name.trim()) e.investor_name = 'اسم المستثمر مطلوب';
    if (!form.start_date) e.start_date = 'تاريخ بداية العقد مطلوب';
    if (!form.end_date) e.end_date = 'تاريخ نهاية العقد مطلوب';
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      e.end_date = 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية';
    }
    if (form.contract_value && isNaN(Number(form.contract_value))) {
      e.contract_value = 'قيمة العقد يجب أن تكون رقماً';
    }
    return e;
  };

  const handleSave = async () => {
    const e = validate();
    if (Object.keys(e).length > 0) {
      setErrors(e);
      return;
    }
    setSaving(true);
    try {
      const payload: any = {
        contract_number: form.contract_number.trim(),
        property_id: Number(form.property_id),
        investor_name: form.investor_name.trim(),
        investor_contact: form.investor_contact.trim() || null,
        investment_type: form.investment_type,
        start_date: form.start_date,
        end_date: form.end_date,
        contract_value: form.contract_value ? Number(form.contract_value) : 0,
        contract_copy: form.contract_copy || null,
        terms_booklet: form.terms_booklet || null,
        investor_id_copy: form.investor_id_copy || null,
        owner_id_copy: form.owner_id_copy || null,
        ownership_proof: form.ownership_proof || null,
        handover_report: form.handover_report || null,
        handover_property_images: form.handover_property_images.length > 0 ? form.handover_property_images : null,
        financial_documents: form.financial_documents.length > 0 ? form.financial_documents : null,
        additional_attachments: form.additional_attachments.length > 0 ? form.additional_attachments : null,
        notes: form.notes.trim() || null,
      };
      if (isEdit) {
        await apiService.updateInvestmentContract(editData.id, payload);
        toast.success('تم تحديث العقد بنجاح');
      } else {
        await apiService.createInvestmentContract(payload);
        toast.success('تم إضافة العقد بنجاح');
      }
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof ApiError
        ? (err.detail ? `فشل الحفظ: ${err.detail}` : 'فشل حفظ العقد')
        : 'فشل حفظ العقد';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const set = (field: string, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: '' }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'تعديل العقد' : 'إضافة عقد استثماري'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label>رقم العقد *</Label>
            <Input
              value={form.contract_number}
              onChange={e => set('contract_number', e.target.value)}
              className={errors.contract_number ? 'border-destructive' : ''}
            />
            {errors.contract_number && <p className="text-xs text-destructive">{errors.contract_number}</p>}
          </div>

          <div className="space-y-1">
            <Label>العقار المرتبط *</Label>
            <Select value={form.property_id} onValueChange={v => set('property_id', v)}>
              <SelectTrigger className={errors.property_id ? 'border-destructive' : ''}>
                <SelectValue placeholder="اختر عقاراً" />
              </SelectTrigger>
              <SelectContent>
                {properties.map(p => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.address}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.property_id && <p className="text-xs text-destructive">{errors.property_id}</p>}
            {properties.length === 0 && (
              <p className="text-xs text-muted-foreground">لا توجد أصول متاحة. أضف عقاراً أولاً.</p>
            )}
          </div>

          <div className="space-y-1">
            <Label>اسم المستثمر *</Label>
            <Input
              value={form.investor_name}
              onChange={e => set('investor_name', e.target.value)}
              className={errors.investor_name ? 'border-destructive' : ''}
            />
            {errors.investor_name && <p className="text-xs text-destructive">{errors.investor_name}</p>}
          </div>

          <div className="space-y-1">
            <Label>معلومات الاتصال بالمستثمر</Label>
            <Input
              value={form.investor_contact}
              onChange={e => set('investor_contact', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>نوع الاستثمار</Label>
              <Select value={form.investment_type} onValueChange={v => set('investment_type', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(INVESTMENT_TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>قيمة العقد</Label>
              <Input
                type="number"
                step="0.01"
                value={form.contract_value}
                onChange={e => set('contract_value', e.target.value)}
                className={errors.contract_value ? 'border-destructive' : ''}
              />
              {errors.contract_value && <p className="text-xs text-destructive">{errors.contract_value}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>تاريخ بداية العقد *</Label>
              <Input
                type="date"
                value={form.start_date}
                onChange={e => set('start_date', e.target.value)}
                className={errors.start_date ? 'border-destructive' : ''}
              />
              {errors.start_date && <p className="text-xs text-destructive">{errors.start_date}</p>}
            </div>
            <div className="space-y-1">
              <Label>تاريخ نهاية العقد *</Label>
              <Input
                type="date"
                value={form.end_date}
                onChange={e => set('end_date', e.target.value)}
                className={errors.end_date ? 'border-destructive' : ''}
              />
              {errors.end_date && <p className="text-xs text-destructive">{errors.end_date}</p>}
            </div>
          </div>

          <div className="space-y-1">
            <Label>ملاحظات</Label>
            <Textarea
              value={form.notes}
              onChange={e => set('notes', e.target.value)}
              rows={3}
            />
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <Label className="text-base">المستندات والمرفقات</Label>
              <p className="text-xs text-muted-foreground mt-1">جميع المرفقات اختيارية.</p>
            </div>
            <FileUpload category="investment_contracts" accept="documents" multiple={false} existingFiles={form.contract_copy ? [form.contract_copy] : []} onUploadComplete={(files) => set('contract_copy', files[0] || '')} label="نسخة العقد" />
            <FileUpload category="investment_contracts" accept="documents" multiple={false} existingFiles={form.terms_booklet ? [form.terms_booklet] : []} onUploadComplete={(files) => set('terms_booklet', files[0] || '')} label="نسخة دفتر الشروط" />
            <FileUpload category="investment_contracts" accept="images" multiple={false} existingFiles={form.investor_id_copy ? [form.investor_id_copy] : []} onUploadComplete={(files) => set('investor_id_copy', files[0] || '')} label="صورة هوية المستثمر" />
            <FileUpload category="investment_contracts" accept="images" multiple={false} existingFiles={form.owner_id_copy ? [form.owner_id_copy] : []} onUploadComplete={(files) => set('owner_id_copy', files[0] || '')} label="صورة هوية المالك" />
            <FileUpload category="investment_contracts" accept="documents" multiple={false} existingFiles={form.ownership_proof ? [form.ownership_proof] : []} onUploadComplete={(files) => set('ownership_proof', files[0] || '')} label="وثيقة / سند ملكية العقار" />
            <FileUpload category="investment_contracts" accept="documents" multiple={false} existingFiles={form.handover_report ? [form.handover_report] : []} onUploadComplete={(files) => set('handover_report', files[0] || '')} label="محضر تسليم العقار" />
            <FileUpload category="investment_contracts" accept="images" existingFiles={form.handover_property_images} onUploadComplete={(files) => set('handover_property_images', files)} label="صور العقار عند التسليم" />
            <FileUpload category="investment_contracts" accept="documents" existingFiles={form.financial_documents} onUploadComplete={(files) => set('financial_documents', files)} label="مستندات مالية إن وجدت" />
            <FileUpload category="investment_contracts" accept="all" existingFiles={form.additional_attachments} onUploadComplete={(files) => set('additional_attachments', files)} label="مرفقات إضافية" />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            إلغاء
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Spinner className="animate-spin ml-1" size={16} />}
            {isEdit ? 'حفظ التعديلات' : 'إضافة العقد'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function InvestmentContractsPage() {
  const navigate = useNavigate();
  const { role } = useAuth();

  const [contracts, setContracts] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [properties, setProperties] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [propertyFilter, setPropertyFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<any>(null);

  const canManage = role && ['project_director', 'contracts_manager', 'investment_manager'].includes(role);

  const fetchContracts = useCallback(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (propertyFilter !== 'all') params.property_id = Number(propertyFilter);
    if (statusFilter !== 'all') params.status_filter = statusFilter;
    if (search.trim()) params.q = search.trim();
    apiService.listInvestmentContracts(params)
      .then(data => {
        setContracts(data.items);
        setTotalCount(data.total_count);
      })
      .catch(err => setError(describeLoadError(err, 'العقود الاستثمارية').message))
      .finally(() => setLoading(false));
  }, [page, propertyFilter, statusFilter, search]);

  useEffect(() => {
    // Load properties once for dropdowns and labels.
    apiService.listInvestmentProperties({ limit: 500 })
      .then(data => setProperties(data.items))
      .catch(() => setProperties([]));
  }, []);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const propertyAddress = (id: number) => {
    const p = properties.find(x => x.id === id);
    return p ? p.address : `#${id}`;
  };

  const handleCreate = () => {
    setEditTarget(null);
    setDialogOpen(true);
  };

  const handleEdit = (c: any) => {
    setEditTarget(c);
    setDialogOpen(true);
  };

  const handleDelete = async (c: any) => {
    if (!window.confirm(`هل تريد إلغاء/حذف العقد رقم: "${c.contract_number}"؟`)) return;
    try {
      await apiService.deleteInvestmentContract(c.id);
      toast.success('تم إلغاء العقد');
      fetchContracts();
    } catch {
      toast.error('فشل حذف العقد');
    }
  };

  return (
    <Layout>
      <Card className="border-[#D8E2EF]">
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-2">
            <div className="space-y-2">
              <CardTitle className="text-2xl flex items-center gap-2 text-[#0F2A4A]">
                <FileText size={26} weight="duotone" />
                العقود الاستثمارية
              </CardTitle>
              <div className="flex gap-2 flex-wrap">
                <Button variant="outline" size="sm" className="border-[#D8E2EF]" onClick={() => navigate('/contract-intelligence')}>
                  تحليل عقد استثماري
                </Button>
                <Button variant="outline" size="sm" className="border-[#D8E2EF]" onClick={() => navigate('/contract-intelligence/queue')}>
                  استيراد من مركز ذكاء العقود
                </Button>
              </div>
            </div>
            {canManage && (
              <Button onClick={handleCreate} disabled={properties.length === 0}>
                <Plus size={18} className="ml-1" />
                إضافة عقد جديد
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <DataToolbar
            search={(
              <div className="relative">
                <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                <Input
                  placeholder="بحث برقم العقد، اسم المستثمر، أو الملاحظات..."
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(0); }}
                  className="pr-10"
                />
              </div>
            )}
            filters={(
              <>
                <Select value={propertyFilter} onValueChange={v => { setPropertyFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[200px]"><SelectValue placeholder="العقار" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الأصول</SelectItem>
                    {properties.map(p => (
                      <SelectItem key={p.id} value={String(p.id)}>{p.address}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={statusFilter} onValueChange={v => { setStatusFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[170px]"><SelectValue placeholder="حالة العقد" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الحالات</SelectItem>
                    {Object.entries(STATUS_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </>
            )}
          />

          {error && (
            <ErrorState message={error} onRetry={fetchContracts} retrying={loading} />
          )}

          {loading && !error && (
            <>
              <div className="responsive-table-desktop">
                <DataTableShell>
                  <LoadingSkeleton rows={5} columns={canManage ? 8 : 7} />
                </DataTableShell>
              </div>
              <div className="responsive-cards-mobile">
                <LoadingSkeleton rows={4} variant="cards" />
              </div>
            </>
          )}

          {!loading && !error && contracts.length === 0 && (
            <EmptyState
              icon={<FileText size={40} weight="duotone" />}
              title={search || propertyFilter !== 'all' || statusFilter !== 'all'
                ? 'لم يتم العثور على نتائج مطابقة'
                : 'لا توجد عقود استثمارية بعد'}
              description={properties.length === 0 ? 'يجب إضافة عقار أولاً قبل إنشاء عقد.' : undefined}
              action={canManage && properties.length > 0 && !(search || propertyFilter !== 'all' || statusFilter !== 'all') ? (
                <Button onClick={handleCreate}>إضافة أول عقد</Button>
              ) : undefined}
            />
          )}

          {!loading && !error && contracts.length > 0 && (
            <>
              {/* Desktop table view */}
              <div className="responsive-table-desktop">
                <DataTableShell>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-right">رقم العقد</TableHead>
                        <TableHead className="text-right">العقار المرتبط</TableHead>
                        <TableHead className="text-right">اسم المستثمر</TableHead>
                        <TableHead className="text-right">تاريخ النهاية</TableHead>
                        <TableHead className="text-right">قيمة العقد</TableHead>
                        <TableHead className="text-right">حالة العقد</TableHead>
                        <TableHead className="text-right">تنبيه الانتهاء</TableHead>
                        {canManage && <TableHead className="text-center">الإجراءات</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {contracts.map(c => {
                        const alert = c.expiry_alert as keyof typeof EXPIRY_TONES | null;
                        return (
                          <TableRow
                            key={c.id}
                            className="cursor-pointer"
                            onClick={() => navigate(`/investment-contracts/${c.id}`)}
                          >
                            <TableCell className="font-medium text-[#0F2A4A]">{c.contract_number}</TableCell>
                            <TableCell>{propertyAddress(c.property_id)}</TableCell>
                            <TableCell>{c.investor_name}</TableCell>
                            <TableCell>{c.end_date}</TableCell>
                            <TableCell>{Number(c.contract_value).toLocaleString('ar')}</TableCell>
                            <TableCell>
                              <StatusBadge tone={STATUS_TONES[c.status] ?? 'neutral'}>
                                {STATUS_LABELS[c.status] || c.status}
                              </StatusBadge>
                            </TableCell>
                            <TableCell>
                              {alert && EXPIRY_TONES[alert] ? (
                                <StatusBadge tone={EXPIRY_TONES[alert].tone}>
                                  {EXPIRY_TONES[alert].label}
                                </StatusBadge>
                              ) : '-'}
                            </TableCell>
                            {canManage && (
                              <TableCell className="text-center" onClick={e => e.stopPropagation()}>
                                <div className="flex justify-center gap-1">
                                  <Button variant="ghost" size="sm" onClick={() => handleEdit(c)} title="تعديل">
                                    <PencilSimple size={16} />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-destructive hover:text-destructive"
                                    onClick={() => handleDelete(c)}
                                    title="حذف"
                                  >
                                    <Trash size={16} />
                                  </Button>
                                </div>
                              </TableCell>
                            )}
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </DataTableShell>
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {contracts.map(c => {
                  const alert = c.expiry_alert as keyof typeof EXPIRY_TONES | null;
                  return (
                    <MobileEntityCard
                      key={c.id}
                      onClick={() => navigate(`/investment-contracts/${c.id}`)}
                      title={<span className="font-mono text-[#1D4ED8]">{c.contract_number}</span>}
                      badge={
                        <StatusBadge tone={STATUS_TONES[c.status] ?? 'neutral'}>
                          {STATUS_LABELS[c.status] || c.status}
                        </StatusBadge>
                      }
                      subtitle={c.investor_name}
                      meta={(
                        <>
                          <span>{INVESTMENT_TYPE_LABELS[c.investment_type] || c.investment_type}</span>
                          <span aria-hidden>•</span>
                          <span>{propertyAddress(c.property_id)}</span>
                          <span aria-hidden>•</span>
                          <span>{Number(c.contract_value).toLocaleString('ar')}</span>
                          {c.end_date && (
                            <>
                              <span aria-hidden>•</span>
                              <span>ينتهي: {c.end_date}</span>
                            </>
                          )}
                          {alert && EXPIRY_TONES[alert] && (
                            <>
                              <span aria-hidden>•</span>
                              <StatusBadge tone={EXPIRY_TONES[alert].tone}>
                                {EXPIRY_TONES[alert].label}
                              </StatusBadge>
                            </>
                          )}
                        </>
                      )}
                    />
                  );
                })}
              </div>

              <PaginationBar
                page={page}
                totalPages={totalPages}
                totalCount={totalCount}
                pageSize={PAGE_SIZE}
                entityLabel="عقد"
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <ContractFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editData={editTarget}
        properties={properties}
        onSuccess={fetchContracts}
      />
    </Layout>
  );
}

export { ATTACHMENT_SLOTS, INVESTMENT_TYPE_LABELS, STATUS_LABELS, STATUS_COLORS, EXPIRY_BADGE };
