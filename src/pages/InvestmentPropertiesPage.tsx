import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService, ApiError } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { MagnifyingGlass, Spinner, Warning, Plus, Buildings, PencilSimple, Trash } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';
import { FileUpload } from '@/components/FileUpload';

// ── Lookup maps ────────────────────────────────────────────────────────────

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  building: 'بناء',
  land: 'أرض',
  restaurant: 'مطعم',
  kiosk: 'كشك',
  shop: 'محل',
  other: 'غير ذلك',
};

const STATUS_LABELS: Record<string, string> = {
  available: 'متاح',
  invested: 'مستثمر',
  maintenance: 'قيد الصيانة',
  suspended: 'متوقف',
  unfit: 'غير صالح',
};

const STATUS_COLORS: Record<string, string> = {
  available: 'bg-green-100 text-green-800',
  invested: 'bg-blue-100 text-blue-800',
  maintenance: 'bg-yellow-100 text-yellow-800',
  suspended: 'bg-gray-100 text-gray-800',
  unfit: 'bg-red-100 text-red-800',
};

const PAGE_SIZE = 15;

// ── Empty form ─────────────────────────────────────────────────────────────

const emptyForm = {
  property_type: 'building',
  address: '',
  area: '',
  status: 'available',
  description: '',
  owner_name: '',
  owner_info: '',
  property_images: [] as string[],
  property_documents: [] as string[],
  owner_id_image: '',
  additional_attachments: [] as string[],
  notes: '',
};

// ── Property form dialog ───────────────────────────────────────────────────

interface PropertyFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editData?: any;
  onSuccess: () => void;
}

function PropertyFormDialog({ open, onOpenChange, editData, onSuccess }: PropertyFormDialogProps) {
  const isEdit = !!editData;
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      if (editData) {
        setForm({
          property_type: editData.property_type || 'building',
          address: editData.address || '',
          area: editData.area !== null && editData.area !== undefined ? String(editData.area) : '',
          status: editData.status || 'available',
          description: editData.description || '',
          owner_name: editData.owner_name || '',
          owner_info: editData.owner_info || '',
          property_images: Array.isArray(editData.property_images) ? editData.property_images : [],
          property_documents: Array.isArray(editData.property_documents) ? editData.property_documents : [],
          owner_id_image: editData.owner_id_image || '',
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
    if (!form.address.trim()) e.address = 'العنوان التفصيلي مطلوب';
    if (!form.property_type) e.property_type = 'نوع العقار مطلوب';
    if (form.area && isNaN(Number(form.area))) e.area = 'المساحة يجب أن تكون رقماً';
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
        property_type: form.property_type,
        address: form.address.trim(),
        status: form.status,
        description: form.description.trim() || null,
        owner_name: form.owner_name.trim() || null,
        owner_info: form.owner_info.trim() || null,
        property_images: form.property_images.length > 0 ? form.property_images : null,
        property_documents: form.property_documents.length > 0 ? form.property_documents : null,
        owner_id_image: form.owner_id_image || null,
        additional_attachments: form.additional_attachments.length > 0 ? form.additional_attachments : null,
        notes: form.notes.trim() || null,
      };
      if (form.area.trim()) payload.area = Number(form.area);

      if (isEdit) {
        const result = await apiService.updateInvestmentProperty(editData.id, payload);
        toast.success(result?.queued ? 'تم حفظ الطلب محليًا وسيتم إرساله عند عودة الاتصال' : 'تم تحديث العقار بنجاح');
      } else {
        const result = await apiService.createInvestmentProperty(payload);
        toast.success(result?.queued ? 'تم حفظ الطلب محليًا وسيتم إرساله عند عودة الاتصال' : 'تم إضافة العقار بنجاح');
      }
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof ApiError
        ? (err.detail ? `فشل الحفظ: ${err.detail}` : 'فشل حفظ العقار')
        : 'فشل حفظ العقار';
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'تعديل العقار' : 'إضافة عقار جديد'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* نوع العقار */}
          <div className="space-y-1">
            <Label>نوع العقار *</Label>
            <Select value={form.property_type} onValueChange={v => set('property_type', v)}>
              <SelectTrigger className={errors.property_type ? 'border-destructive' : ''}>
                <SelectValue placeholder="اختر النوع" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(PROPERTY_TYPE_LABELS).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.property_type && <p className="text-xs text-destructive">{errors.property_type}</p>}
          </div>

          {/* العنوان التفصيلي */}
          <div className="space-y-1">
            <Label>العنوان التفصيلي *</Label>
            <Input
              placeholder="أدخل العنوان التفصيلي للعقار"
              value={form.address}
              onChange={e => set('address', e.target.value)}
              className={errors.address ? 'border-destructive' : ''}
            />
            {errors.address && <p className="text-xs text-destructive">{errors.address}</p>}
          </div>

          {/* المساحة والحالة */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>المساحة (م²)</Label>
              <Input
                type="number"
                placeholder="0.00"
                value={form.area}
                onChange={e => set('area', e.target.value)}
                className={errors.area ? 'border-destructive' : ''}
              />
              {errors.area && <p className="text-xs text-destructive">{errors.area}</p>}
            </div>
            <div className="space-y-1">
              <Label>الحالة</Label>
              <Select value={form.status} onValueChange={v => set('status', v)}>
                <SelectTrigger>
                  <SelectValue placeholder="اختر الحالة" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(STATUS_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* الوصف */}
          <div className="space-y-1">
            <Label>الوصف</Label>
            <Textarea
              placeholder="وصف العقار..."
              value={form.description}
              onChange={e => set('description', e.target.value)}
              rows={2}
            />
          </div>

          {/* المالك */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>اسم المالك</Label>
              <Input
                placeholder="اسم المالك"
                value={form.owner_name}
                onChange={e => set('owner_name', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>معلومات المالك</Label>
              <Input
                placeholder="رقم الهاتف أو ملاحظات"
                value={form.owner_info}
                onChange={e => set('owner_info', e.target.value)}
              />
            </div>
          </div>

          {/* ملاحظات */}
          <div className="space-y-1">
            <Label>ملاحظات</Label>
            <Textarea
              placeholder="ملاحظات إضافية..."
              value={form.notes}
              onChange={e => set('notes', e.target.value)}
              rows={2}
            />
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <Label className="text-base">الصور والمرفقات</Label>
              <p className="text-xs text-muted-foreground mt-1">اختياري بالكامل — يمكن إضافة الملفات لاحقًا.</p>
            </div>
            <FileUpload
              category="investment_contracts"
              accept="images"
              existingFiles={form.property_images}
              onUploadComplete={(files) => set('property_images', files)}
              label="صور العقار"
            />
            <FileUpload
              category="investment_contracts"
              accept="documents"
              existingFiles={form.property_documents}
              onUploadComplete={(files) => set('property_documents', files)}
              label="وثائق العقار"
            />
            <FileUpload
              category="investment_contracts"
              accept="images"
              multiple={false}
              existingFiles={form.owner_id_image ? [form.owner_id_image] : []}
              onUploadComplete={(files) => set('owner_id_image', files[0] || '')}
              label="صورة هوية المالك"
            />
            <FileUpload
              category="investment_contracts"
              accept="all"
              existingFiles={form.additional_attachments}
              onUploadComplete={(files) => set('additional_attachments', files)}
              label="مرفقات إضافية"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            إلغاء
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Spinner className="animate-spin ml-1" size={16} />}
            {isEdit ? 'حفظ التعديلات' : 'إضافة العقار'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function InvestmentPropertiesPage() {
  const navigate = useNavigate();
  const { role } = useAuth();

  const [properties, setProperties] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<any>(null);

  const canManage = role && ['project_director', 'property_manager'].includes(role);

  const fetchProperties = useCallback(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (typeFilter !== 'all') params.type = typeFilter;
    if (statusFilter !== 'all') params.status = statusFilter;
    if (search.trim()) params.q = search.trim();
    apiService.listInvestmentProperties(params)
      .then(data => {
        setProperties(data.items);
        setTotalCount(data.total_count);
      })
      .catch(err => setError(describeLoadError(err, 'الأصول').message))
      .finally(() => setLoading(false));
  }, [page, typeFilter, statusFilter, search]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const handleCreate = () => {
    setEditTarget(null);
    setDialogOpen(true);
  };

  const handleEdit = (prop: any) => {
    setEditTarget(prop);
    setDialogOpen(true);
  };

  const handleDelete = async (prop: any) => {
    if (!window.confirm(`هل تريد حذف العقار: "${prop.address}"؟`)) return;
    try {
      await apiService.deleteInvestmentProperty(prop.id);
      toast.success('تم حذف العقار');
      fetchProperties();
    } catch {
      toast.error('فشل حذف العقار');
    }
  };

  return (
    <Layout>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-2">
            <CardTitle className="text-2xl flex items-center gap-2">
              <Buildings size={28} />
              الأصول
            </CardTitle>
            {canManage && (
              <Button onClick={handleCreate}>
                <Plus size={20} className="ml-1" />
                إضافة عقار جديد
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Filters */}
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث بالعنوان أو المالك أو الوصف..."
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(0); }}
                className="pr-10"
              />
            </div>

            <div className="flex gap-2 flex-wrap">
              <Select value={typeFilter} onValueChange={v => { setTypeFilter(v); setPage(0); }}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="نوع العقار" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الأنواع</SelectItem>
                  {Object.entries(PROPERTY_TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={v => { setStatusFilter(v); setPage(0); }}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="الحالة" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الحالات</SelectItem>
                  {Object.entries(STATUS_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex justify-center py-8">
              <Spinner className="animate-spin text-primary" size={32} />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 text-destructive py-4">
              <Warning size={20} />
              <span>{error}</span>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && properties.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <Buildings size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-lg mb-2">لا توجد أصول استثمارية بعد</p>
              {canManage && (
                <Button onClick={handleCreate} className="mt-4">
                  إضافة أول عقار
                </Button>
              )}
            </div>
          )}

          {/* Table */}
          {!loading && !error && properties.length > 0 && (
            <>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>نوع العقار</TableHead>
                      <TableHead>العنوان التفصيلي</TableHead>
                      <TableHead>المساحة (م²)</TableHead>
                      <TableHead>الحالة</TableHead>
                      <TableHead>المالك</TableHead>
                      {canManage && <TableHead className="text-center">الإجراءات</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {properties.map(prop => (
                      <TableRow
                        key={prop.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => navigate(`/investment-properties/${prop.id}`)}
                      >
                        <TableCell className="font-medium">
                          {PROPERTY_TYPE_LABELS[prop.property_type] || prop.property_type}
                        </TableCell>
                        <TableCell>{prop.address}</TableCell>
                        <TableCell>{prop.area !== null && prop.area !== undefined ? Number(prop.area).toLocaleString('ar') : '-'}</TableCell>
                        <TableCell>
                          <Badge className={STATUS_COLORS[prop.status] || 'bg-gray-100'}>
                            {STATUS_LABELS[prop.status] || prop.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{prop.owner_name || '-'}</TableCell>
                        {canManage && (
                          <TableCell className="text-center" onClick={e => e.stopPropagation()}>
                            <div className="flex justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(prop)}
                                title="تعديل"
                              >
                                <PencilSimple size={16} />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                                onClick={() => handleDelete(prop)}
                                title="حذف"
                              >
                                <Trash size={16} />
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                  عرض {page * PAGE_SIZE + 1} - {Math.min((page + 1) * PAGE_SIZE, totalCount)} من {totalCount}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    السابق
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= totalPages - 1}
                  >
                    التالي
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit dialog */}
      <PropertyFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editData={editTarget}
        onSuccess={fetchProperties}
      />
    </Layout>
  );
}
