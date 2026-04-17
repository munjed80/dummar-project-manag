import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Spinner, GearSix, Buildings, Info, Upload, Database, Heartbeat, CheckCircle, XCircle, Warning } from '@phosphor-icons/react';

interface HealthData {
  status: string;
  database: { status: string; latency_ms?: number };
  smtp: { status: string; message?: string };
  version: string;
}

export default function SettingsPage() {
  const [user, setUser] = useState<any>(null);
  const [areas, setAreas] = useState<any[]>([]);
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { role } = useAuth();

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiService.getCurrentUser().catch(() => null),
      apiService.getAreas().catch(() => []),
    ])
      .then(([userData, areasData]) => {
        setUser(userData);
        setAreas(areasData);
      })
      .catch(() => setError('فشل تحميل الإعدادات'))
      .finally(() => setLoading(false));
  }, []);

  const fetchHealth = async () => {
    setHealthLoading(true);
    try {
      const resp = await fetch(
        `${(window as any).__API_BASE || '/api'}/health/detailed`,
        { headers: { 'Content-Type': 'application/json' } }
      );
      if (resp.ok) {
        setHealthData(await resp.json());
      }
    } catch {
      // Health endpoint may not be available during development
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    if (role === 'project_director' || role === 'contracts_manager') {
      fetchHealth();
    }
  }, [role]);

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

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <GearSix size={24} />
          الإعدادات
        </h1>

        {/* System Health — visible to project_director and contracts_manager */}
        {(role === 'project_director' || role === 'contracts_manager') && (
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
              ) : healthData ? (
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
              ) : (
                <p className="text-sm text-muted-foreground text-center py-2">
                  لا يمكن الاتصال بخدمة الصحة
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Organization Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Buildings size={20} />
              إعدادات المشروع
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {detail('اسم المشروع', 'مشروع دمّر السكني - دمشق')}
            {detail('المنظمة', 'الهيئة العامة للإسكان')}
            {detail('المنطقة', 'دمّر - ريف دمشق')}
            <Separator className="my-2" />
            {detail('عدد المناطق المسجلة', <Badge variant="secondary">{areas.length}</Badge>)}
            {detail('قائمة المناطق', (
              <div className="flex flex-wrap gap-1 justify-end max-w-md">
                {areas.map((a: any) => (
                  <Badge key={a.id} variant="outline" className="text-xs">{a.name_ar || a.name}</Badge>
                ))}
              </div>
            ))}
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
