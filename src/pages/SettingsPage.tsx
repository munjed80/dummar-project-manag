import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { config } from '@/config';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner, GearSix, Buildings, Info, Upload, Database, Heartbeat, CheckCircle, XCircle, Warning, FloppyDisk } from '@phosphor-icons/react';
import { toast } from 'sonner';

interface HealthData {
  status: string;
  database: { status: string; latency_ms?: number };
  smtp: { status: string; message?: string };
  version: string;
}

interface SettingItem {
  key: string;
  value: string | null;
  value_type: string;
  category: string;
  description?: string | null;
}

const CATEGORY_LABELS: Record<string, string> = {
  project: 'بيانات المشروع',
  organization: 'بيانات المنظمة',
  defaults: 'القيم التشغيلية الافتراضية',
  general: 'عام',
};

// Strip a trailing /api segment so /health/* (mounted at root) is reachable
// even when the API is served under /api in production.
function buildHealthUrl(): string {
  const base = (config.API_BASE_URL || '').replace(/\/?api\/?$/, '').replace(/\/$/, '');
  return `${base}/health/detailed`;
}

export default function SettingsPage() {
  const [user, setUser] = useState<any>(null);
  const [areas, setAreas] = useState<any[]>([]);
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [settings, setSettings] = useState<Record<string, SettingItem[]>>({});
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { role } = useAuth();
  const canEditSettings = role === 'project_director' || role === 'contracts_manager';

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiService.getCurrentUser().catch(() => null),
      apiService.getAreas().catch(() => []),
      apiService.getSettings().catch(() => ({})),
    ])
      .then(([userData, areasData, settingsData]) => {
        setUser(userData);
        setAreas(areasData);
        setSettings(settingsData as Record<string, SettingItem[]>);
      })
      .catch(() => setError('فشل تحميل الإعدادات'))
      .finally(() => setLoading(false));
  }, []);

  const fetchHealth = async () => {
    setHealthLoading(true);
    try {
      const resp = await fetch(buildHealthUrl(), {
        headers: {
          'Content-Type': 'application/json',
          // Health endpoint requires authenticated internal user.
          ...(localStorage.getItem('access_token')
            ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
            : {}),
        },
      });
      if (resp.ok) {
        setHealthData(await resp.json());
      } else {
        // Quietly hide the card on auth/permission failure rather than show a
        // misleading "broken" state.
        setHealthData(null);
      }
    } catch {
      setHealthData(null);
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    if (role === 'project_director' || role === 'contracts_manager') {
      fetchHealth();
    }
  }, [role]);

  const onFieldChange = (key: string, value: string) => {
    setEdited((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveSettings = async () => {
    if (Object.keys(edited).length === 0) {
      toast.info('لا توجد تغييرات للحفظ');
      return;
    }
    // Build merged items list: all known settings, with edited values applied.
    const flat: SettingItem[] = Object.values(settings).flat();
    const items = flat.map((s) => ({
      key: s.key,
      value: s.key in edited ? edited[s.key] : s.value,
      value_type: s.value_type,
      category: s.category,
      description: s.description,
    }));
    setSaving(true);
    try {
      await apiService.updateSettings(items);
      // Reload to reflect canonical persisted values.
      const fresh = await apiService.getSettings();
      setSettings(fresh as Record<string, SettingItem[]>);
      setEdited({});
      toast.success('تم حفظ الإعدادات');
    } catch {
      toast.error('فشل حفظ الإعدادات');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12"><Spinner className="animate-spin" size={32} /></div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="text-center py-12 text-destructive">{error}</div>
      </Layout>
    );
  }

  const detail = (label: string, value: React.ReactNode) => (
    <div className="flex justify-between items-center py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium text-sm">{value || '-'}</span>
    </div>
  );

  const roleLabels: Record<string, string> = {
    project_director: 'مدير المشروع',
    contracts_manager: 'مدير العقود',
    engineer_supervisor: 'مشرف هندسي',
    complaints_officer: 'مسؤول الشكاوى',
    area_supervisor: 'مشرف المنطقة',
    field_team: 'فريق ميداني',
    contractor_user: 'مستخدم مقاول',
    citizen: 'مواطن',
  };

  const renderSettingInput = (item: SettingItem) => {
    const currentValue = item.key in edited ? edited[item.key] : (item.value ?? '');
    if (!canEditSettings) {
      return <span className="font-medium text-sm">{currentValue || '-'}</span>;
    }
    if (item.value_type === 'boolean') {
      return (
        <select
          className="border rounded-md px-2 py-1 text-sm bg-background"
          value={currentValue}
          onChange={(e) => onFieldChange(item.key, e.target.value)}
        >
          <option value="true">نعم</option>
          <option value="false">لا</option>
        </select>
      );
    }
    if (item.value_type === 'number') {
      return (
        <Input
          type="number"
          value={currentValue}
          onChange={(e) => onFieldChange(item.key, e.target.value)}
          className="max-w-[12rem]"
        />
      );
    }
    return (
      <Input
        value={currentValue}
        onChange={(e) => onFieldChange(item.key, e.target.value)}
        className="max-w-md"
      />
    );
  };

  const categoryKeys = Object.keys(settings);
  const hasSettings = categoryKeys.length > 0;
  const hasUnsavedChanges = Object.keys(edited).length > 0;

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <GearSix size={24} />
          الإعدادات
        </h1>

        {/* System Health — visible to project_director and contracts_manager */}
        {(role === 'project_director' || role === 'contracts_manager') && healthData && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Heartbeat size={20} />
                صحة النظام
              </CardTitle>
            </CardHeader>
            <CardContent>
              {healthLoading ? (
                <div className="flex justify-center py-4"><Spinner className="animate-spin" size={24} /></div>
              ) : (
                <div className="space-y-1">
                  {detail('الحالة العامة', (
                    <Badge className={
                      healthData.status === 'healthy' ? 'bg-green-100 text-green-800' :
                      healthData.status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }>
                      {healthData.status === 'healthy' ? (
                        <><CheckCircle size={14} className="ml-1" /> سليم</>
                      ) : healthData.status === 'degraded' ? (
                        <><Warning size={14} className="ml-1" /> متدهور</>
                      ) : (
                        <><XCircle size={14} className="ml-1" /> غير سليم</>
                      )}
                    </Badge>
                  ))}
                  {detail('قاعدة البيانات', (
                    <Badge className={healthData.database.status === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                      {healthData.database.status === 'ok' ? 'متصلة' : 'غير متصلة'}
                      {healthData.database.latency_ms && ` (${healthData.database.latency_ms}ms)`}
                    </Badge>
                  ))}
                  {detail('البريد الإلكتروني (SMTP)', (
                    <Badge className={
                      healthData.smtp.status === 'ok' ? 'bg-green-100 text-green-800' :
                      healthData.smtp.status === 'disabled' ? 'bg-gray-100 text-gray-800' :
                      'bg-red-100 text-red-800'
                    }>
                      {healthData.smtp.status === 'ok' ? 'متصل' :
                       healthData.smtp.status === 'disabled' ? 'معطّل' : 'خطأ'}
                    </Badge>
                  ))}
                  {detail('إصدار API', healthData.version)}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Configurable settings — read-only for non-privileged roles */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <CardTitle className="flex items-center gap-2">
                <Buildings size={20} />
                إعدادات المشروع والمنظمة
                {!canEditSettings && (
                  <Badge variant="outline" className="text-xs">للقراءة فقط</Badge>
                )}
              </CardTitle>
              {canEditSettings && hasSettings && (
                <Button
                  onClick={handleSaveSettings}
                  disabled={saving || !hasUnsavedChanges}
                  className="gap-2"
                >
                  {saving ? <Spinner className="animate-spin" size={16} /> : <FloppyDisk size={16} />}
                  حفظ التغييرات
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!hasSettings ? (
              <div className="text-center py-6 text-muted-foreground text-sm">
                لا توجد إعدادات مُعرَّفة بعد.
              </div>
            ) : (
              <div className="space-y-6">
                {categoryKeys.map((category) => (
                  <div key={category}>
                    <h3 className="text-sm font-semibold text-muted-foreground mb-2">
                      {CATEGORY_LABELS[category] || category}
                    </h3>
                    <div className="space-y-2">
                      {settings[category].map((item) => (
                        <div key={item.key} className="flex items-start justify-between gap-3 py-2 border-b border-border/50 last:border-0">
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium">
                              {item.description || item.key}
                            </div>
                            <code className="text-xs text-muted-foreground">{item.key}</code>
                          </div>
                          <div className="flex-shrink-0">
                            {renderSettingInput(item)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                <Separator />
                <div className="text-sm">
                  {detail('عدد المناطق المسجلة', <Badge variant="secondary">{areas.length}</Badge>)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Current User Info */}
        {user && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info size={20} />
                معلومات الحساب الحالي
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {detail('اسم المستخدم', user.username)}
              {detail('الاسم الكامل', user.full_name)}
              {detail('البريد الإلكتروني', user.email)}
              {detail('الدور', <Badge>{roleLabels[user.role] || user.role}</Badge>)}
              {detail('رقم الهاتف', user.phone)}
            </CardContent>
          </Card>
        )}

        {/* Upload Limits */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload size={20} />
              حدود الرفع
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {detail('الحجم الأقصى للملف', '10 ميغابايت')}
            {detail('الامتدادات المسموحة (صور)', '.jpg, .jpeg, .png, .gif')}
            {detail('الامتدادات المسموحة (مستندات)', '.pdf, .doc, .docx')}
            {detail('فئات الرفع', 'عام، عقود، شكاوى، مهام، ملفات شخصية')}
          </CardContent>
        </Card>

        {/* System Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database size={20} />
              معلومات النظام
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {detail('إصدار الواجهة الأمامية', '1.0.0')}
            {detail('إصدار الواجهة الخلفية', '1.0.0')}
            {detail('قاعدة البيانات', 'PostgreSQL + PostGIS')}
            {detail('المصادقة', 'JWT Bearer Token (24 ساعة)')}
            {detail('اللغة الافتراضية', 'العربية (RTL)')}
            {detail('إطار العمل', 'React 19 + FastAPI')}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
