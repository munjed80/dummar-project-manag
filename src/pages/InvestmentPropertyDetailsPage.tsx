import { useState, useEffect } from 'react';
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
import { Spinner, ArrowLeft, Buildings, PencilSimple, Trash } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { format } from 'date-fns';

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

// ── Page component ─────────────────────────────────────────────────────────

export default function InvestmentPropertyDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { role } = useAuth();

  const [property, setProperty] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const canManage = role && ['project_director', 'property_manager'].includes(role);

  const [form, setForm] = useState({
    property_type: 'building',
    address: '',
    area: '',
    status: 'available',
    description: '',
    owner_name: '',
    owner_info: '',
    notes: '',
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    apiService.getInvestmentProperty(Number(id))
      .then(data => {
        setProperty(data);
        setForm({
          property_type: data.property_type || 'building',
          address: data.address || '',
          area: data.area !== null && data.area !== undefined ? String(data.area) : '',
          status: data.status || 'available',
          description: data.description || '',
          owner_name: data.owner_name || '',
          owner_info: data.owner_info || '',
          notes: data.notes || '',
        });
      })
      .catch(() => setError('فشل تحميل بيانات العقار'))
      .finally(() => setLoading(false));
  }, [id]);

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
      setFormErrors(e);
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
        notes: form.notes.trim() || null,
      };
      if (form.area.trim()) payload.area = Number(form.area);

      const updated = await apiService.updateInvestmentProperty(Number(id), payload);
      setProperty(updated);
      setEditing(false);
      toast.success('تم تحديث العقار بنجاح');
    } catch (err) {
      const message = err instanceof ApiError
        ? (err.detail ? `فشل التحديث: ${err.detail}` : 'فشل تحديث العقار')
        : 'فشل تحديث العقار';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!property) return;
    if (!window.confirm(`هل تريد حذف العقار: "${property.address}"؟`)) return;
    try {
      await apiService.deleteInvestmentProperty(property.id);
      toast.success('تم حذف العقار');
      navigate('/investment-properties');
    } catch {
      toast.error('فشل حذف العقار');
    }
  };

  const setField = (field: string, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setFormErrors(prev => ({ ...prev, [field]: '' }));
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin text-primary" size={32} />
        </div>
      </Layout>
    );
  }

  if (error || !property) {
    return (
      <Layout>
        <div className="space-y-4">
          <Button variant="ghost" onClick={() => navigate('/investment-properties')}>
            <ArrowLeft size={20} className="ml-1" />
            العودة إلى الأملاك
          </Button>
          <Card>
            <CardContent className="py-12 text-center text-destructive">
              {error || 'العقار غير موجود'}
            </CardContent>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/investment-properties')}>
          <ArrowLeft size={20} className="ml-1" />
          العودة إلى الأملاك
        </Button>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-start flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <Buildings size={28} className="text-primary" />
                <div>
                  <CardTitle className="text-xl">
                    {PROPERTY_TYPE_LABELS[property.property_type] || property.property_type}
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-0.5">{property.address}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={STATUS_COLORS[property.status] || 'bg-gray-100'}>
                  {STATUS_LABELS[property.status] || property.status}
                </Badge>
                {canManage && !editing && (
                  <>
                    <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                      <PencilSimple size={16} className="ml-1" />
                      تعديل
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive border-destructive hover:bg-destructive/10"
                      onClick={handleDelete}
                    >
                      <Trash size={16} className="ml-1" />
                      حذف
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {!editing ? (
              // ── View mode ────────────────────────────────────────────────
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-muted-foreground text-xs">نوع العقار</Label>
                  <p className="mt-1">{PROPERTY_TYPE_LABELS[property.property_type] || property.property_type}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">الحالة</Label>
                  <p className="mt-1">
                    <Badge className={STATUS_COLORS[property.status] || 'bg-gray-100'}>
                      {STATUS_LABELS[property.status] || property.status}
                    </Badge>
                  </p>
                </div>
                <div className="md:col-span-2">
                  <Label className="text-muted-foreground text-xs">العنوان التفصيلي</Label>
                  <p className="mt-1">{property.address}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">المساحة (م²)</Label>
                  <p className="mt-1">
                    {property.area !== null && property.area !== undefined
                      ? Number(property.area).toLocaleString('ar')
                      : '-'}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">اسم المالك</Label>
                  <p className="mt-1">{property.owner_name || '-'}</p>
                </div>
                {property.owner_info && (
                  <div className="md:col-span-2">
                    <Label className="text-muted-foreground text-xs">معلومات المالك</Label>
                    <p className="mt-1 whitespace-pre-wrap">{property.owner_info}</p>
                  </div>
                )}
                {property.description && (
                  <div className="md:col-span-2">
                    <Label className="text-muted-foreground text-xs">الوصف</Label>
                    <p className="mt-1 whitespace-pre-wrap">{property.description}</p>
                  </div>
                )}
                {property.notes && (
                  <div className="md:col-span-2">
                    <Label className="text-muted-foreground text-xs">ملاحظات</Label>
                    <p className="mt-1 whitespace-pre-wrap">{property.notes}</p>
                  </div>
                )}
                <div>
                  <Label className="text-muted-foreground text-xs">تاريخ الإضافة</Label>
                  <p className="mt-1 text-sm">
                    {property.created_at
                      ? format(new Date(property.created_at), 'yyyy-MM-dd HH:mm')
                      : '-'}
                  </p>
                </div>
                {property.updated_at && (
                  <div>
                    <Label className="text-muted-foreground text-xs">آخر تعديل</Label>
                    <p className="mt-1 text-sm">
                      {format(new Date(property.updated_at), 'yyyy-MM-dd HH:mm')}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              // ── Edit mode ────────────────────────────────────────────────
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  {/* نوع العقار */}
                  <div className="space-y-1">
                    <Label>نوع العقار *</Label>
                    <Select value={form.property_type} onValueChange={v => setField('property_type', v)}>
                      <SelectTrigger className={formErrors.property_type ? 'border-destructive' : ''}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(PROPERTY_TYPE_LABELS).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {formErrors.property_type && (
                      <p className="text-xs text-destructive">{formErrors.property_type}</p>
                    )}
                  </div>

                  {/* الحالة */}
                  <div className="space-y-1">
                    <Label>الحالة</Label>
                    <Select value={form.status} onValueChange={v => setField('status', v)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(STATUS_LABELS).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* العنوان */}
                  <div className="space-y-1 md:col-span-2">
                    <Label>العنوان التفصيلي *</Label>
                    <Input
                      value={form.address}
                      onChange={e => setField('address', e.target.value)}
                      className={formErrors.address ? 'border-destructive' : ''}
                    />
                    {formErrors.address && (
                      <p className="text-xs text-destructive">{formErrors.address}</p>
                    )}
                  </div>

                  {/* المساحة */}
                  <div className="space-y-1">
                    <Label>المساحة (م²)</Label>
                    <Input
                      type="number"
                      value={form.area}
                      onChange={e => setField('area', e.target.value)}
                      className={formErrors.area ? 'border-destructive' : ''}
                    />
                    {formErrors.area && (
                      <p className="text-xs text-destructive">{formErrors.area}</p>
                    )}
                  </div>

                  {/* اسم المالك */}
                  <div className="space-y-1">
                    <Label>اسم المالك</Label>
                    <Input
                      value={form.owner_name}
                      onChange={e => setField('owner_name', e.target.value)}
                    />
                  </div>

                  {/* معلومات المالك */}
                  <div className="space-y-1 md:col-span-2">
                    <Label>معلومات المالك</Label>
                    <Input
                      value={form.owner_info}
                      onChange={e => setField('owner_info', e.target.value)}
                    />
                  </div>

                  {/* الوصف */}
                  <div className="space-y-1 md:col-span-2">
                    <Label>الوصف</Label>
                    <Textarea
                      value={form.description}
                      onChange={e => setField('description', e.target.value)}
                      rows={3}
                    />
                  </div>

                  {/* ملاحظات */}
                  <div className="space-y-1 md:col-span-2">
                    <Label>ملاحظات</Label>
                    <Textarea
                      value={form.notes}
                      onChange={e => setField('notes', e.target.value)}
                      rows={3}
                    />
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button onClick={handleSave} disabled={saving}>
                    {saving && <Spinner className="animate-spin ml-1" size={16} />}
                    حفظ التعديلات
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => { setEditing(false); setFormErrors({}); }}
                    disabled={saving}
                  >
                    إلغاء
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
