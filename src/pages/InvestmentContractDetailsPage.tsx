import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
import { Spinner, ArrowLeft, FileText, PencilSimple, Trash, Paperclip, Upload, DownloadSimple } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import {
  ATTACHMENT_SLOTS,
  INVESTMENT_TYPE_LABELS,
  STATUS_LABELS,
  STATUS_COLORS,
  EXPIRY_BADGE,
} from './InvestmentContractsPage';

export default function InvestmentContractDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { role } = useAuth();

  const [contract, setContract] = useState<any>(null);
  const [property, setProperty] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    contract_number: '',
    investor_name: '',
    investor_contact: '',
    investment_type: 'lease',
    start_date: '',
    end_date: '',
    contract_value: '',
    status: 'active',
    notes: '',
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const canManage = !!role && ['project_director', 'contracts_manager', 'investment_manager'].includes(role);

  const load = () => {
    if (!id) return;
    setLoading(true);
    setError('');
    apiService.getInvestmentContract(Number(id))
      .then(async data => {
        setContract(data);
        setForm({
          contract_number: data.contract_number || '',
          investor_name: data.investor_name || '',
          investor_contact: data.investor_contact || '',
          investment_type: data.investment_type || 'lease',
          start_date: data.start_date || '',
          end_date: data.end_date || '',
          contract_value: data.contract_value !== undefined && data.contract_value !== null
            ? String(data.contract_value) : '',
          status: data.status || 'active',
          notes: data.notes || '',
        });
        // Pull the linked property for context (not required to render).
        try {
          const p = await apiService.getInvestmentProperty(data.property_id);
          setProperty(p);
        } catch {
          setProperty(null);
        }
      })
      .catch(err => {
        if (err instanceof ApiError && err.detail) setError(err.detail);
        else setError('تعذر تحميل بيانات العقد');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.contract_number.trim()) e.contract_number = 'رقم العقد مطلوب';
    if (!form.investor_name.trim()) e.investor_name = 'اسم المستثمر مطلوب';
    if (!form.start_date) e.start_date = 'تاريخ بداية العقد مطلوب';
    if (!form.end_date) e.end_date = 'تاريخ نهاية العقد مطلوب';
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      e.end_date = 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية';
    }
    if (!form.contract_value || isNaN(Number(form.contract_value))) {
      e.contract_value = 'قيمة العقد مطلوبة ويجب أن تكون رقماً';
    }
    return e;
  };

  const handleSave = async () => {
    const e = validate();
    if (Object.keys(e).length > 0) {
      setFormErrors(e);
      return;
    }
    setSaving(true);
    try {
      await apiService.updateInvestmentContract(Number(id), {
        contract_number: form.contract_number.trim(),
        investor_name: form.investor_name.trim(),
        investor_contact: form.investor_contact.trim() || null,
        investment_type: form.investment_type,
        start_date: form.start_date,
        end_date: form.end_date,
        contract_value: Number(form.contract_value),
        status: form.status,
        notes: form.notes.trim() || null,
      });
      toast.success('تم حفظ التعديلات');
      setEditing(false);
      setFormErrors({});
      load();
    } catch (err) {
      const msg = err instanceof ApiError && err.detail ? err.detail : 'فشل حفظ العقد';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`هل تريد حذف/إلغاء العقد "${contract.contract_number}"؟`)) return;
    try {
      await apiService.deleteInvestmentContract(Number(id));
      toast.success('تم إلغاء العقد');
      navigate('/investment-contracts');
    } catch {
      toast.error('فشل حذف العقد');
    }
  };

  const handleAttachmentUpload = async (slot: string, file: File) => {
    try {
      const result = await apiService.uploadInvestmentContractFile(file);
      await apiService.updateInvestmentContract(Number(id), { [slot]: result.path });
      toast.success('تم رفع الملف بنجاح');
      load();
    } catch (err) {
      const msg = err instanceof ApiError && err.detail ? err.detail : 'فشل رفع الملف';
      toast.error(msg);
    }
  };

  const handleAttachmentRemove = async (slot: string) => {
    if (!window.confirm('هل تريد حذف هذا الملف؟')) return;
    try {
      await apiService.updateInvestmentContract(Number(id), { [slot]: null });
      toast.success('تم حذف الملف');
      load();
    } catch {
      toast.error('فشل حذف الملف');
    }
  };

  const handleAdditionalUpload = async (file: File) => {
    try {
      const result = await apiService.uploadInvestmentContractFile(file);
      const current: string[] = Array.isArray(contract.additional_attachments)
        ? contract.additional_attachments
        : [];
      await apiService.updateInvestmentContract(Number(id), {
        additional_attachments: [...current, result.path],
      });
      toast.success('تم رفع الملف الإضافي');
      load();
    } catch (err) {
      const msg = err instanceof ApiError && err.detail ? err.detail : 'فشل رفع الملف';
      toast.error(msg);
    }
  };

  const handleAdditionalRemove = async (path: string) => {
    if (!window.confirm('هل تريد حذف هذا المرفق؟')) return;
    try {
      const current: string[] = Array.isArray(contract.additional_attachments)
        ? contract.additional_attachments
        : [];
      await apiService.updateInvestmentContract(Number(id), {
        additional_attachments: current.filter(p => p !== path),
      });
      toast.success('تم حذف المرفق');
      load();
    } catch {
      toast.error('فشل حذف المرفق');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin text-primary" size={40} />
        </div>
      </Layout>
    );
  }

  if (error || !contract) {
    return (
      <Layout>
        <Button variant="outline" onClick={() => navigate('/investment-contracts')}>
          <ArrowLeft size={18} className="ml-1" />
          العودة إلى العقود الاستثمارية
        </Button>
        <Card className="mt-4">
          <CardContent className="py-12 text-center text-destructive">
            {error || 'تعذر تحميل العقد'}
          </CardContent>
        </Card>
      </Layout>
    );
  }

  const alert = contract.expiry_alert as keyof typeof EXPIRY_BADGE | null;

  return (
    <Layout>
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <Button variant="outline" onClick={() => navigate('/investment-contracts')}>
            <ArrowLeft size={18} className="ml-1" />
            العودة إلى العقود الاستثمارية
          </Button>
          {canManage && !editing && (
            <div className="flex gap-2">
              <Button onClick={() => setEditing(true)}>
                <PencilSimple size={18} className="ml-1" />
                تعديل
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                <Trash size={18} className="ml-1" />
                حذف
              </Button>
            </div>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 flex-wrap">
              <FileText size={28} />
              <span>عقد رقم: {contract.contract_number}</span>
              <Badge className={STATUS_COLORS[contract.status] || 'bg-gray-100'}>
                {STATUS_LABELS[contract.status] || contract.status}
              </Badge>
              {alert && EXPIRY_BADGE[alert] && (
                <Badge className={EXPIRY_BADGE[alert].cls}>
                  {EXPIRY_BADGE[alert].label}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!editing ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <DetailRow label="رقم العقد" value={contract.contract_number} />
                <DetailRow
                  label="العقار المرتبط"
                  value={
                    property ? (
                      <button
                        type="button"
                        className="text-primary underline"
                        onClick={() => navigate(`/investment-properties/${property.id}`)}
                      >
                        {property.address}
                      </button>
                    ) : `#${contract.property_id}`
                  }
                />
                <DetailRow label="اسم المستثمر" value={contract.investor_name} />
                <DetailRow label="معلومات الاتصال" value={contract.investor_contact || '-'} />
                <DetailRow
                  label="نوع الاستثمار"
                  value={INVESTMENT_TYPE_LABELS[contract.investment_type] || contract.investment_type}
                />
                <DetailRow label="قيمة العقد" value={Number(contract.contract_value).toLocaleString('ar')} />
                <DetailRow label="تاريخ بداية العقد" value={contract.start_date} />
                <DetailRow label="تاريخ نهاية العقد" value={contract.end_date} />
                <DetailRow
                  label="حالة العقد"
                  value={STATUS_LABELS[contract.status] || contract.status}
                />
                <DetailRow
                  label="الأيام المتبقية"
                  value={
                    contract.days_until_expiry !== null && contract.days_until_expiry !== undefined
                      ? `${contract.days_until_expiry} يوم`
                      : '-'
                  }
                />
                <div className="md:col-span-2">
                  <DetailRow label="ملاحظات" value={contract.notes || '-'} />
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <FormRow label="رقم العقد *" error={formErrors.contract_number}>
                  <Input
                    value={form.contract_number}
                    onChange={e => setForm({ ...form, contract_number: e.target.value })}
                  />
                </FormRow>
                <FormRow label="اسم المستثمر *" error={formErrors.investor_name}>
                  <Input
                    value={form.investor_name}
                    onChange={e => setForm({ ...form, investor_name: e.target.value })}
                  />
                </FormRow>
                <FormRow label="معلومات الاتصال">
                  <Input
                    value={form.investor_contact}
                    onChange={e => setForm({ ...form, investor_contact: e.target.value })}
                  />
                </FormRow>
                <div className="grid grid-cols-2 gap-3">
                  <FormRow label="نوع الاستثمار">
                    <Select value={form.investment_type} onValueChange={v => setForm({ ...form, investment_type: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(INVESTMENT_TYPE_LABELS).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormRow>
                  <FormRow label="حالة العقد">
                    <Select value={form.status} onValueChange={v => setForm({ ...form, status: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(STATUS_LABELS).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormRow>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <FormRow label="تاريخ بداية العقد *" error={formErrors.start_date}>
                    <Input
                      type="date"
                      value={form.start_date}
                      onChange={e => setForm({ ...form, start_date: e.target.value })}
                    />
                  </FormRow>
                  <FormRow label="تاريخ نهاية العقد *" error={formErrors.end_date}>
                    <Input
                      type="date"
                      value={form.end_date}
                      onChange={e => setForm({ ...form, end_date: e.target.value })}
                    />
                  </FormRow>
                </div>
                <FormRow label="قيمة العقد *" error={formErrors.contract_value}>
                  <Input
                    type="number"
                    step="0.01"
                    value={form.contract_value}
                    onChange={e => setForm({ ...form, contract_value: e.target.value })}
                  />
                </FormRow>
                <FormRow label="ملاحظات">
                  <Textarea
                    value={form.notes}
                    onChange={e => setForm({ ...form, notes: e.target.value })}
                    rows={3}
                  />
                </FormRow>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" onClick={() => { setEditing(false); setFormErrors({}); load(); }} disabled={saving}>
                    إلغاء
                  </Button>
                  <Button onClick={handleSave} disabled={saving}>
                    {saving && <Spinner className="animate-spin ml-1" size={16} />}
                    حفظ التعديلات
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Paperclip size={24} />
              المرفقات
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {ATTACHMENT_SLOTS.map(slot => (
              <AttachmentRow
                key={slot.field}
                label={slot.label}
                path={contract[slot.field]}
                canManage={canManage}
                onUpload={file => handleAttachmentUpload(slot.field, file)}
                onRemove={() => handleAttachmentRemove(slot.field)}
              />
            ))}

            <div className="border-t pt-3">
              <h3 className="font-medium mb-2">مرفقات إضافية</h3>
              <ul className="space-y-2">
                {Array.isArray(contract.additional_attachments) && contract.additional_attachments.length > 0
                  ? contract.additional_attachments.map((p: string, i: number) => (
                      <li key={i} className="flex items-center justify-between bg-muted/40 rounded px-3 py-2">
                        <a href={p} target="_blank" rel="noopener noreferrer" className="text-primary underline truncate">
                          <DownloadSimple size={16} className="inline ml-1" />
                          مرفق {i + 1}
                        </a>
                        {canManage && (
                          <Button variant="ghost" size="sm" onClick={() => handleAdditionalRemove(p)}>
                            <Trash size={14} />
                          </Button>
                        )}
                      </li>
                    ))
                  : <li className="text-sm text-muted-foreground">لا توجد مرفقات إضافية</li>}
              </ul>
              {canManage && (
                <FileUploadButton onSelect={handleAdditionalUpload} label="إضافة مرفق إضافي" />
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <Label className="text-muted-foreground text-xs">{label}</Label>
      <div className="font-medium">{value}</div>
    </div>
  );
}

function FormRow({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

interface AttachmentRowProps {
  label: string;
  path?: string | null;
  canManage: boolean;
  onUpload: (file: File) => void;
  onRemove: () => void;
}

function AttachmentRow({ label, path, canManage, onUpload, onRemove }: AttachmentRowProps) {
  return (
    <div className="flex items-center justify-between gap-2 bg-muted/40 rounded px-3 py-2 flex-wrap">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{label}</div>
        {path ? (
          <a href={path} target="_blank" rel="noopener noreferrer" className="text-xs text-primary underline truncate inline-block">
            <DownloadSimple size={12} className="inline ml-1" />
            عرض / تحميل
          </a>
        ) : (
          <div className="text-xs text-muted-foreground">لم يتم الرفع بعد</div>
        )}
      </div>
      {canManage && (
        <div className="flex gap-1">
          <FileUploadButton onSelect={onUpload} label={path ? 'استبدال' : 'رفع'} small />
          {path && (
            <Button variant="ghost" size="sm" onClick={onRemove} className="text-destructive">
              <Trash size={14} />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function FileUploadButton({ onSelect, label, small }: { onSelect: (file: File) => void; label: string; small?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <Button variant="outline" size={small ? 'sm' : 'default'} onClick={() => ref.current?.click()} className="mt-2">
        <Upload size={16} className="ml-1" />
        {label}
      </Button>
      <input
        ref={ref}
        type="file"
        className="hidden"
        accept=".pdf,.jpg,.jpeg,.png,.gif,.doc,.docx"
        onChange={e => {
          const file = e.target.files?.[0];
          if (file) onSelect(file);
          e.target.value = '';
        }}
      />
    </>
  );
}
