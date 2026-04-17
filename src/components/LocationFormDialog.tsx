import { useState, useEffect } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { apiService } from '@/services/api';
import { Spinner } from '@phosphor-icons/react';

const LOCATION_TYPES = [
  { value: 'island', label: 'جزيرة' },
  { value: 'sector', label: 'قطاع' },
  { value: 'block', label: 'بلوك' },
  { value: 'building', label: 'مبنى' },
  { value: 'tower', label: 'برج' },
  { value: 'street', label: 'شارع' },
  { value: 'service_point', label: 'نقطة خدمة' },
  { value: 'other', label: 'أخرى' },
];

const LOCATION_STATUSES = [
  { value: 'active', label: 'نشط' },
  { value: 'inactive', label: 'غير نشط' },
  { value: 'under_construction', label: 'قيد الإنشاء' },
  { value: 'demolished', label: 'مهدّم' },
];

interface LocationFormData {
  name: string;
  code: string;
  location_type: string;
  parent_id: number | null;
  status: string;
  description: string;
  latitude: string;
  longitude: string;
  is_active: boolean;
  metadata_json: string;
}

interface LocationFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editData?: any; // Location object for editing, null for creating
  parentId?: number | null; // Pre-set parent for creating under a location
  onSuccess: () => void;
}

const emptyForm: LocationFormData = {
  name: '',
  code: '',
  location_type: 'island',
  parent_id: null,
  status: 'active',
  description: '',
  latitude: '',
  longitude: '',
  is_active: true,
  metadata_json: '',
};

export function LocationFormDialog({
  open, onOpenChange, editData, parentId, onSuccess,
}: LocationFormDialogProps) {
  const isEdit = !!editData;
  const [form, setForm] = useState<LocationFormData>(emptyForm);
  const [parentOptions, setParentOptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load parent location options
  useEffect(() => {
    if (!open) return;
    apiService.getLocations({ is_active: 1, limit: 500 }).then(setParentOptions).catch((err) => {
      console.error('Failed to load parent options:', err);
    });
  }, [open]);

  // Populate form when editing or when parentId changes
  useEffect(() => {
    if (!open) return;
    if (editData) {
      setForm({
        name: editData.name || '',
        code: editData.code || '',
        location_type: editData.location_type || 'island',
        parent_id: editData.parent_id || null,
        status: editData.status || 'active',
        description: editData.description || '',
        latitude: editData.latitude != null ? String(editData.latitude) : '',
        longitude: editData.longitude != null ? String(editData.longitude) : '',
        is_active: editData.is_active === 1,
        metadata_json: editData.metadata_json || '',
      });
    } else {
      setForm({
        ...emptyForm,
        parent_id: parentId ?? null,
      });
    }
    setError(null);
  }, [open, editData, parentId]);

  const handleSubmit = async () => {
    // Validation
    if (!form.name.trim()) { setError('الاسم مطلوب'); return; }
    if (!form.code.trim()) { setError('الرمز مطلوب'); return; }
    if (!form.location_type) { setError('النوع مطلوب'); return; }

    const payload: any = {
      name: form.name.trim(),
      code: form.code.trim(),
      location_type: form.location_type,
      parent_id: form.parent_id || null,
      status: form.status,
      description: form.description.trim() || null,
      latitude: form.latitude ? parseFloat(form.latitude) : null,
      longitude: form.longitude ? parseFloat(form.longitude) : null,
      metadata_json: form.metadata_json.trim() || null,
    };

    if (isEdit) {
      payload.is_active = form.is_active ? 1 : 0;
    }

    // Validate coordinates
    if (payload.latitude !== null && (isNaN(payload.latitude) || payload.latitude < -90 || payload.latitude > 90)) {
      setError('خط العرض يجب أن يكون بين -90 و 90'); return;
    }
    if (payload.longitude !== null && (isNaN(payload.longitude) || payload.longitude < -180 || payload.longitude > 180)) {
      setError('خط الطول يجب أن يكون بين -180 و 180'); return;
    }

    setLoading(true);
    setError(null);

    try {
      if (isEdit) {
        await apiService.updateLocation(editData.id, payload);
      } else {
        await apiService.createLocation(payload);
      }
      onSuccess();
      onOpenChange(false);
    } catch (err: any) {
      setError(err.message || 'حدث خطأ');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto" dir="rtl">
        <DialogHeader>
          <DialogTitle className="text-right">
            {isEdit ? 'تعديل الموقع' : 'إضافة موقع جديد'}
          </DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Name */}
          <div className="grid gap-2">
            <Label htmlFor="loc-name">الاسم *</Label>
            <Input
              id="loc-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="مثال: جزيرة 1"
              dir="rtl"
            />
          </div>

          {/* Code */}
          <div className="grid gap-2">
            <Label htmlFor="loc-code">الرمز *</Label>
            <Input
              id="loc-code"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="مثال: ISL-001"
              dir="ltr"
              className="text-left"
            />
          </div>

          {/* Type + Status row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label>النوع *</Label>
              <Select value={form.location_type} onValueChange={(v) => setForm({ ...form, location_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LOCATION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>الحالة</Label>
              <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LOCATION_STATUSES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Parent */}
          <div className="grid gap-2">
            <Label>الموقع الأب</Label>
            <Select
              value={form.parent_id ? String(form.parent_id) : '__none__'}
              onValueChange={(v) => setForm({ ...form, parent_id: v === '__none__' ? null : parseInt(v) })}
            >
              <SelectTrigger><SelectValue placeholder="بدون أب (مستوى أعلى)" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">بدون أب (مستوى أعلى)</SelectItem>
                {parentOptions
                  .filter((p: any) => !isEdit || p.id !== editData?.id)
                  .map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.name} ({p.code})
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="grid gap-2">
            <Label htmlFor="loc-desc">الوصف</Label>
            <Textarea
              id="loc-desc"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="وصف الموقع..."
              dir="rtl"
              rows={3}
            />
          </div>

          {/* Coordinates row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="loc-lat">خط العرض</Label>
              <Input
                id="loc-lat"
                type="number"
                step="any"
                value={form.latitude}
                onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                placeholder="33.5365"
                dir="ltr"
                className="text-left"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="loc-lng">خط الطول</Label>
              <Input
                id="loc-lng"
                type="number"
                step="any"
                value={form.longitude}
                onChange={(e) => setForm({ ...form, longitude: e.target.value })}
                placeholder="36.2204"
                dir="ltr"
                className="text-left"
              />
            </div>
          </div>

          {/* Metadata */}
          <div className="grid gap-2">
            <Label htmlFor="loc-meta">بيانات إضافية (JSON)</Label>
            <Textarea
              id="loc-meta"
              value={form.metadata_json}
              onChange={(e) => setForm({ ...form, metadata_json: e.target.value })}
              placeholder='{"floors": 5, "capacity": 200}'
              dir="ltr"
              className="text-left font-mono text-sm"
              rows={2}
            />
          </div>

          {/* Active toggle (edit mode only) */}
          {isEdit && (
            <div className="flex items-center justify-between border rounded-lg p-3">
              <Label htmlFor="loc-active">نشط</Label>
              <Switch
                id="loc-active"
                checked={form.is_active}
                onCheckedChange={(v) => setForm({ ...form, is_active: v })}
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-800 text-sm text-right">
              {error}
            </div>
          )}
        </div>

        <DialogFooter className="flex gap-2 sm:justify-start">
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Spinner className="ml-2 animate-spin" size={16} />}
            {isEdit ? 'حفظ التعديلات' : 'إضافة الموقع'}
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            إلغاء
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default LocationFormDialog;
