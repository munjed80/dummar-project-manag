import { useState, useEffect, useCallback, useMemo } from 'react';
import { Layout } from '@/components/Layout';
import {
  apiService,
  ApiError,
  type Violation,
  type ViolationListResponse,
  type ViolationSeverity,
  type ViolationStatus,
  type ViolationType,
} from '@/services/api';
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
import {
  MagnifyingGlass,
  Spinner,
  Warning,
  Plus,
  ShieldWarning,
  PencilSimple,
  Trash,
  Eye,
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';

// ── Lookup maps ────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<ViolationType, string> = {
  building: 'بناء',
  occupancy: 'إشغال',
  market: 'أسواق',
  hygiene: 'نظافة',
  road: 'طرق',
  environment: 'بيئة',
  public_property: 'ممتلكات عامة',
  other: 'أخرى',
};

const SEVERITY_LABELS: Record<ViolationSeverity, string> = {
  low: 'منخفضة',
  medium: 'متوسطة',
  high: 'عالية',
  critical: 'حرجة',
};

const SEVERITY_COLORS: Record<ViolationSeverity, string> = {
  low: 'bg-slate-100 text-slate-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<ViolationStatus, string> = {
  new: 'جديدة',
  under_review: 'قيد المراجعة',
  inspection_required: 'بحاجة إلى تفتيش',
  violation_confirmed: 'مؤكدة',
  notice_sent: 'أُرسل الإشعار',
  fined: 'مفروضة عليها غرامة',
  resolved: 'محلولة',
  rejected: 'مرفوضة',
  referred_to_legal: 'محالة إلى القانوني',
};

const STATUS_COLORS: Record<ViolationStatus, string> = {
  new: 'bg-blue-100 text-blue-800',
  under_review: 'bg-indigo-100 text-indigo-800',
  inspection_required: 'bg-amber-100 text-amber-800',
  violation_confirmed: 'bg-orange-100 text-orange-800',
  notice_sent: 'bg-purple-100 text-purple-800',
  fined: 'bg-red-100 text-red-800',
  resolved: 'bg-green-100 text-green-800',
  rejected: 'bg-gray-100 text-gray-700',
  referred_to_legal: 'bg-rose-100 text-rose-800',
};

const PAGE_SIZE = 15;

// Roles that can create / edit violations.
const WRITE_ROLES = new Set([
  'project_director',
  'contracts_manager',
  'engineer_supervisor',
  'complaints_officer',
  'area_supervisor',
]);

// Only the project_director may delete.
const DELETE_ROLES = new Set(['project_director']);

// ── Empty form ─────────────────────────────────────────────────────────────

interface FormState {
  title: string;
  description: string;
  violation_type: ViolationType;
  severity: ViolationSeverity;
  status: ViolationStatus;
  location_text: string;
  legal_reference: string;
  fine_amount: string;
  deadline_date: string;
  municipality_id: string;
  district_id: string;
}

const emptyForm: FormState = {
  title: '',
  description: '',
  violation_type: 'building',
  severity: 'medium',
  status: 'new',
  location_text: '',
  legal_reference: '',
  fine_amount: '',
  deadline_date: '',
  municipality_id: '',
  district_id: '',
};

// ── Form dialog ────────────────────────────────────────────────────────────

interface ViolationFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editData?: Violation | null;
  onSuccess: () => void;
}

function ViolationFormDialog({
  open,
  onOpenChange,
  editData,
  onSuccess,
}: ViolationFormDialogProps) {
  const isEdit = !!editData;
  const [form, setForm] = useState<FormState>({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    if (editData) {
      setForm({
        title: editData.title || '',
        description: editData.description || '',
        violation_type: editData.violation_type,
        severity: editData.severity,
        status: editData.status,
        location_text: editData.location_text || '',
        legal_reference: editData.legal_reference || '',
        fine_amount:
          editData.fine_amount !== null && editData.fine_amount !== undefined
            ? String(editData.fine_amount)
            : '',
        deadline_date: editData.deadline_date
          ? editData.deadline_date.slice(0, 10)
          : '',
        municipality_id:
          editData.municipality_id !== null && editData.municipality_id !== undefined
            ? String(editData.municipality_id)
            : '',
        district_id:
          editData.district_id !== null && editData.district_id !== undefined
            ? String(editData.district_id)
            : '',
      });
    } else {
      setForm({ ...emptyForm });
    }
    setErrors({});
  }, [open, editData]);

  const set = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): Record<string, string> => {
    const e: Record<string, string> = {};
    if (!form.title.trim()) e.title = 'العنوان مطلوب';
    if (!form.description.trim()) e.description = 'الوصف مطلوب';
    if (form.fine_amount && Number.isNaN(Number(form.fine_amount))) {
      e.fine_amount = 'قيمة الغرامة يجب أن تكون رقماً';
    }
    if (form.municipality_id && !Number.isFinite(Number(form.municipality_id))) {
      e.municipality_id = 'معرّف البلدية يجب أن يكون رقماً';
    }
    if (form.district_id && !Number.isFinite(Number(form.district_id))) {
      e.district_id = 'معرّف الحي يجب أن يكون رقماً';
    }
    return e;
  };

  const handleSave = async () => {
    const e = validate();
    if (Object.keys(e).length) {
      setErrors(e);
      return;
    }
    setSaving(true);
    try {
      const payload: Partial<Violation> = {
        title: form.title.trim(),
        description: form.description.trim(),
        violation_type: form.violation_type,
        severity: form.severity,
        status: form.status,
        location_text: form.location_text.trim() || null,
        legal_reference: form.legal_reference.trim() || null,
        fine_amount: form.fine_amount ? form.fine_amount : null,
        deadline_date: form.deadline_date
          ? new Date(form.deadline_date).toISOString()
          : null,
        municipality_id: form.municipality_id ? Number(form.municipality_id) : null,
        district_id: form.district_id ? Number(form.district_id) : null,
      };
      if (isEdit && editData) {
        await apiService.updateViolation(editData.id, payload);
        toast.success('تم تحديث المخالفة بنجاح');
      } else {
        await apiService.createViolation(payload);
        toast.success('تم إنشاء المخالفة بنجاح');
      }
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof ApiError && err.detail
          ? `فشل الحفظ: ${err.detail}`
          : 'فشل حفظ المخالفة';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'تعديل المخالفة' : 'تسجيل مخالفة جديدة'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2 overflow-y-auto px-1">
          <div className="space-y-1">
            <Label>العنوان *</Label>
            <Input
              placeholder="مثال: بناء غير مرخص في الحي السابع"
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              className={errors.title ? 'border-destructive' : ''}
            />
            {errors.title && <p className="text-xs text-destructive">{errors.title}</p>}
          </div>

          <div className="space-y-1">
            <Label>الوصف التفصيلي *</Label>
            <Textarea
              rows={4}
              placeholder="اشرح المخالفة المرصودة وأي ملاحظات للمفتشين"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              className={errors.description ? 'border-destructive' : ''}
            />
            {errors.description && (
              <p className="text-xs text-destructive">{errors.description}</p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>نوع المخالفة *</Label>
              <Select
                value={form.violation_type}
                onValueChange={(v) => set('violation_type', v as ViolationType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label>درجة الخطورة *</Label>
              <Select
                value={form.severity}
                onValueChange={(v) => set('severity', v as ViolationSeverity)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(SEVERITY_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1 sm:col-span-2">
              <Label>الحالة</Label>
              <Select
                value={form.status}
                onValueChange={(v) => set('status', v as ViolationStatus)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(STATUS_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1 sm:col-span-2">
              <Label>الموقع التفصيلي</Label>
              <Input
                placeholder="مثال: شارع 12، قرب المسجد"
                value={form.location_text}
                onChange={(e) => set('location_text', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label>المرجع القانوني</Label>
              <Input
                placeholder="مثال: المادة 24 من النظام"
                value={form.legal_reference}
                onChange={(e) => set('legal_reference', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label>قيمة الغرامة</Label>
              <Input
                type="text"
                inputMode="decimal"
                placeholder="0.00"
                value={form.fine_amount}
                onChange={(e) => set('fine_amount', e.target.value)}
                className={errors.fine_amount ? 'border-destructive' : ''}
              />
              {errors.fine_amount && (
                <p className="text-xs text-destructive">{errors.fine_amount}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label>الموعد النهائي للمعالجة</Label>
              <Input
                type="date"
                value={form.deadline_date}
                onChange={(e) => set('deadline_date', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label>معرّف البلدية</Label>
              <Input
                type="number"
                placeholder="اختياري"
                value={form.municipality_id}
                onChange={(e) => set('municipality_id', e.target.value)}
                className={errors.municipality_id ? 'border-destructive' : ''}
              />
              {errors.municipality_id && (
                <p className="text-xs text-destructive">{errors.municipality_id}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label>معرّف الحي / المختار</Label>
              <Input
                type="number"
                placeholder="اختياري"
                value={form.district_id}
                onChange={(e) => set('district_id', e.target.value)}
                className={errors.district_id ? 'border-destructive' : ''}
              />
              {errors.district_id && (
                <p className="text-xs text-destructive">{errors.district_id}</p>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            إلغاء
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'جاري الحفظ...' : isEdit ? 'حفظ التعديلات' : 'إنشاء'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Status update dialog ───────────────────────────────────────────────────

interface StatusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  violation: Violation | null;
  onSuccess: () => void;
}

function StatusUpdateDialog({ open, onOpenChange, violation, onSuccess }: StatusDialogProps) {
  const [nextStatus, setNextStatus] = useState<ViolationStatus>('under_review');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && violation) {
      setNextStatus(violation.status);
      setNote('');
    }
  }, [open, violation]);

  const handleApply = async () => {
    if (!violation) return;
    setSaving(true);
    try {
      await apiService.updateViolationStatus(violation.id, {
        status: nextStatus,
        note: note.trim() || undefined,
      });
      toast.success('تم تحديث حالة المخالفة');
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof ApiError && err.detail ? err.detail : 'فشل تحديث الحالة';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>تحديث حالة المخالفة</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          {violation && (
            <p className="text-sm text-muted-foreground">
              المخالفة: <span className="font-medium">{violation.violation_number}</span>
            </p>
          )}
          <div className="space-y-1">
            <Label>الحالة الجديدة</Label>
            <Select
              value={nextStatus}
              onValueChange={(v) => setNextStatus(v as ViolationStatus)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <SelectItem key={k} value={k}>
                    {v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>ملاحظة (اختياري)</Label>
            <Textarea
              rows={3}
              placeholder="سبب التحديث، الإجراءات المتخذة..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            إلغاء
          </Button>
          <Button onClick={handleApply} disabled={saving}>
            {saving ? 'جاري الحفظ...' : 'تطبيق'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Detail dialog ──────────────────────────────────────────────────────────

interface DetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  violation: Violation | null;
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-border/50 last:border-0">
      <span className="text-muted-foreground text-sm">{label}</span>
      <span className="text-sm font-medium text-right">{value ?? '-'}</span>
    </div>
  );
}

function ViolationDetailDialog({ open, onOpenChange, violation }: DetailDialogProps) {
  if (!violation) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldWarning size={22} />
            {violation.violation_number}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-1 py-2">
          <DetailRow label="العنوان" value={violation.title} />
          <DetailRow
            label="النوع"
            value={
              <Badge variant="outline">{TYPE_LABELS[violation.violation_type]}</Badge>
            }
          />
          <DetailRow
            label="درجة الخطورة"
            value={
              <Badge className={SEVERITY_COLORS[violation.severity]}>
                {SEVERITY_LABELS[violation.severity]}
              </Badge>
            }
          />
          <DetailRow
            label="الحالة"
            value={
              <Badge className={STATUS_COLORS[violation.status]}>
                {STATUS_LABELS[violation.status]}
              </Badge>
            }
          />
          <DetailRow label="الموقع" value={violation.location_text} />
          <DetailRow label="المرجع القانوني" value={violation.legal_reference} />
          <DetailRow
            label="قيمة الغرامة"
            value={violation.fine_amount ? Number(violation.fine_amount).toLocaleString('ar') : '-'}
          />
          <DetailRow
            label="الموعد النهائي"
            value={
              violation.deadline_date
                ? new Date(violation.deadline_date).toLocaleDateString('ar')
                : '-'
            }
          />
          <DetailRow label="معرّف البلدية" value={violation.municipality_id} />
          <DetailRow label="معرّف الحي" value={violation.district_id} />
          <DetailRow
            label="تاريخ الإنشاء"
            value={new Date(violation.created_at).toLocaleDateString('ar')}
          />
          <DetailRow
            label="تاريخ الحل"
            value={
              violation.resolved_at
                ? new Date(violation.resolved_at).toLocaleDateString('ar')
                : '-'
            }
          />
          <div className="pt-3">
            <p className="text-xs text-muted-foreground mb-1">الوصف</p>
            <p className="text-sm whitespace-pre-wrap leading-6">{violation.description}</p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Stats cards ────────────────────────────────────────────────────────────

function StatsCard({
  label,
  value,
  className,
}: {
  label: string;
  value: number | string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

// ── Page component ─────────────────────────────────────────────────────────

export default function ViolationsPage() {
  const { user } = useAuth();
  const role = user?.role;
  const canWrite = !!role && WRITE_ROLES.has(role);
  const canDelete = !!role && DELETE_ROLES.has(role);

  const [violations, setViolations] = useState<Violation[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | ViolationType>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | ViolationStatus>('all');
  const [severityFilter, setSeverityFilter] = useState<'all' | ViolationSeverity>('all');
  const [page, setPage] = useState(1);

  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Violation | null>(null);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [statusTarget, setStatusTarget] = useState<Violation | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<Violation | null>(null);

  // Aggregated counts (independent of the active filters), so the stats
  // cards always reflect the full picture across the user's scope.
  const [stats, setStats] = useState({
    total: 0,
    under_review: 0,
    inspection_required: 0,
    confirmed: 0,
    resolved: 0,
  });

  const fetchViolations = useCallback(() => {
    setLoading(true);
    setError('');
    const params: Parameters<typeof apiService.listViolations>[0] = {
      page,
      page_size: PAGE_SIZE,
    };
    if (typeFilter !== 'all') params.violation_type = typeFilter;
    if (statusFilter !== 'all') params.status = statusFilter;
    if (severityFilter !== 'all') params.severity = severityFilter;
    if (search.trim()) params.q = search.trim();
    apiService
      .listViolations(params)
      .then((data: ViolationListResponse) => {
        setViolations(Array.isArray(data.items) ? data.items : []);
        setTotalCount(data.total_count ?? 0);
      })
      .catch((err) => setError(describeLoadError(err, 'المخالفات').message))
      .finally(() => setLoading(false));
  }, [page, typeFilter, statusFilter, severityFilter, search]);

  // Stats reflect the user's full violation scope, independent of the
  // table's active filters. Each card maps to a single status bucket, so
  // we issue one tiny `page_size=1` request per bucket and read just the
  // server-side `total_count`. This is correct regardless of how many
  // violations exist in the user's scope.
  const fetchStats = useCallback(() => {
    const buckets: Array<{ key: keyof typeof stats; status?: ViolationStatus }> = [
      { key: 'total' }, // no status filter ⇒ overall total
      { key: 'under_review', status: 'under_review' },
      { key: 'inspection_required', status: 'inspection_required' },
      { key: 'confirmed', status: 'violation_confirmed' },
      { key: 'resolved', status: 'resolved' },
    ];
    Promise.all(
      buckets.map((b) =>
        apiService
          .listViolations({ page: 1, page_size: 1, status: b.status })
          .then((r) => [b.key, r.total_count ?? 0] as const)
          .catch(() => [b.key, null] as const),
      ),
    ).then((results) => {
      setStats((prev) => {
        const next = { ...prev };
        for (const [key, value] of results) {
          if (value !== null) next[key] = value;
        }
        return next;
      });
    });
  }, []);

  useEffect(() => {
    fetchViolations();
  }, [fetchViolations]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(totalCount / PAGE_SIZE)), [totalCount]);

  const handleCreate = () => {
    setEditTarget(null);
    setFormOpen(true);
  };

  const handleEdit = (v: Violation) => {
    setEditTarget(v);
    setFormOpen(true);
  };

  const handleStatus = (v: Violation) => {
    setStatusTarget(v);
    setStatusDialogOpen(true);
  };

  const handleDetail = (v: Violation) => {
    setDetailTarget(v);
    setDetailOpen(true);
  };

  const handleDelete = async (v: Violation) => {
    if (!window.confirm(`هل تريد حذف المخالفة "${v.violation_number}"؟`)) return;
    try {
      await apiService.deleteViolation(v.id);
      toast.success('تم حذف المخالفة');
      fetchViolations();
      fetchStats();
    } catch (err) {
      const message =
        err instanceof ApiError && err.detail ? err.detail : 'فشل حذف المخالفة';
      toast.error(message);
    }
  };

  const onMutationSuccess = () => {
    fetchViolations();
    fetchStats();
  };

  return (
    <Layout>
      <div className="space-y-4">
        {/* Stats cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatsCard label="إجمالي المخالفات" value={stats.total} />
          <StatsCard label="قيد المراجعة" value={stats.under_review} />
          <StatsCard label="بحاجة إلى تفتيش" value={stats.inspection_required} />
          <StatsCard label="مؤكدة" value={stats.confirmed} />
          <StatsCard label="محلولة" value={stats.resolved} />
        </div>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-center flex-wrap gap-2">
              <CardTitle className="text-2xl flex items-center gap-2">
                <ShieldWarning size={28} />
                المخالفات
              </CardTitle>
              {canWrite && (
                <Button onClick={handleCreate}>
                  <Plus size={20} className="ml-1" />
                  تسجيل مخالفة جديدة
                </Button>
              )}
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Filters */}
            <div className="flex flex-col sm:flex-row flex-wrap gap-3">
              <div className="relative flex-1 min-w-0 sm:min-w-[220px]">
                <MagnifyingGlass
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  size={18}
                />
                <Input
                  placeholder="بحث بالعنوان أو الوصف أو رقم المخالفة..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pr-10"
                />
              </div>

              <div className="flex gap-2 flex-wrap">
                <Select
                  value={statusFilter}
                  onValueChange={(v) => {
                    setStatusFilter(v as 'all' | ViolationStatus);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="w-[170px]">
                    <SelectValue placeholder="الحالة" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الحالات</SelectItem>
                    {Object.entries(STATUS_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>
                        {v}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={typeFilter}
                  onValueChange={(v) => {
                    setTypeFilter(v as 'all' | ViolationType);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="w-[160px]">
                    <SelectValue placeholder="النوع" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الأنواع</SelectItem>
                    {Object.entries(TYPE_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>
                        {v}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={severityFilter}
                  onValueChange={(v) => {
                    setSeverityFilter(v as 'all' | ViolationSeverity);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="w-[160px]">
                    <SelectValue placeholder="درجة الخطورة" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الدرجات</SelectItem>
                    {Object.entries(SEVERITY_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>
                        {v}
                      </SelectItem>
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
              <div className="flex flex-col items-center gap-2 text-destructive py-4">
                <div className="flex items-center gap-2">
                  <Warning size={20} />
                  <span>{error}</span>
                </div>
                <Button variant="outline" size="sm" onClick={fetchViolations}>
                  إعادة المحاولة
                </Button>
              </div>
            )}

            {/* Empty state */}
            {!loading && !error && violations.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <ShieldWarning size={48} className="mx-auto mb-4 opacity-30" />
                <p className="text-lg mb-2">لا توجد مخالفات مسجّلة</p>
                {canWrite && (
                  <Button onClick={handleCreate} className="mt-2">
                    تسجيل أول مخالفة
                  </Button>
                )}
              </div>
            )}

            {/* Table */}
            {!loading && !error && violations.length > 0 && (
              <>
                <div className="border rounded-lg overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>رقم المخالفة</TableHead>
                        <TableHead>العنوان</TableHead>
                        <TableHead>النوع</TableHead>
                        <TableHead>درجة الخطورة</TableHead>
                        <TableHead>الحالة</TableHead>
                        <TableHead>البلدية / الحي</TableHead>
                        <TableHead>تاريخ الإنشاء</TableHead>
                        <TableHead className="text-center">الإجراءات</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {violations.map((v) => (
                        <TableRow
                          key={v.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => handleDetail(v)}
                        >
                          <TableCell className="font-mono text-xs">
                            {v.violation_number}
                          </TableCell>
                          <TableCell className="max-w-xs truncate">{v.title}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{TYPE_LABELS[v.violation_type]}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={SEVERITY_COLORS[v.severity]}>
                              {SEVERITY_LABELS[v.severity]}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={STATUS_COLORS[v.status]}>
                              {STATUS_LABELS[v.status]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {v.municipality_id ?? '-'} / {v.district_id ?? '-'}
                          </TableCell>
                          <TableCell className="text-xs">
                            {new Date(v.created_at).toLocaleDateString('ar')}
                          </TableCell>
                          <TableCell
                            className="text-center"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="flex justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDetail(v)}
                                title="عرض التفاصيل"
                              >
                                <Eye size={16} />
                              </Button>
                              {canWrite && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleStatus(v)}
                                    title="تحديث الحالة"
                                  >
                                    <ShieldWarning size={16} />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleEdit(v)}
                                    title="تعديل"
                                  >
                                    <PencilSimple size={16} />
                                  </Button>
                                </>
                              )}
                              {canDelete && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-destructive hover:text-destructive"
                                  onClick={() => handleDelete(v)}
                                  title="حذف"
                                >
                                  <Trash size={16} />
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                <div className="flex justify-between items-center">
                  <p className="text-sm text-muted-foreground">
                    عرض {(page - 1) * PAGE_SIZE + 1} -{' '}
                    {Math.min(page * PAGE_SIZE, totalCount)} من {totalCount}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      السابق
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={page >= totalPages}
                    >
                      التالي
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <ViolationFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        editData={editTarget}
        onSuccess={onMutationSuccess}
      />

      <StatusUpdateDialog
        open={statusDialogOpen}
        onOpenChange={setStatusDialogOpen}
        violation={statusTarget}
        onSuccess={onMutationSuccess}
      />

      <ViolationDetailDialog
        open={detailOpen}
        onOpenChange={setDetailOpen}
        violation={detailTarget}
      />
    </Layout>
  );
}
