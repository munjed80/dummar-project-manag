import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Spinner, Gear, User as UserIcon } from '@phosphor-icons/react';

const roleLabels: Record<string, string> = {
  project_director: 'مدير المشروع',
  contracts_manager: 'مدير العقود',
  engineer_supervisor: 'مهندس مشرف',
  complaints_officer: 'مسؤول الشكاوى',
  area_supervisor: 'مشرف منطقة',
  field_team: 'فريق ميداني',
  contractor_user: 'مستخدم مقاول',
  citizen: 'مواطن',
};

export default function SettingsPage() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiService.getCurrentUser()
      .then(setUser)
      .catch((err) => setError(err.message || 'فشل تحميل بيانات المستخدم'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
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

  if (!user) {
    return (
      <Layout>
        <div className="text-center py-12 text-muted-foreground">لم يتم العثور على بيانات المستخدم</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6 max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Gear size={28} />
          الإعدادات
        </h2>

        {/* User profile */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserIcon size={20} />
              الملف الشخصي
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">الاسم الكامل</p>
                <p className="font-medium">{user.full_name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">اسم المستخدم</p>
                <p className="font-mono">{user.username}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">البريد الإلكتروني</p>
                <p>{user.email || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">رقم الهاتف</p>
                <p dir="ltr" className="text-right">{user.phone || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">الدور</p>
                <Badge className="mt-1">{roleLabels[user.role] || user.role}</Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">الحالة</p>
                <Badge className={user.is_active ? 'bg-green-100 text-green-800 mt-1' : 'bg-red-100 text-red-800 mt-1'}>
                  {user.is_active ? 'نشط' : 'معطّل'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* System info */}
        <Card>
          <CardHeader>
            <CardTitle>معلومات النظام</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between py-1 border-b border-muted">
              <span className="text-muted-foreground">إصدار النظام</span>
              <span className="font-mono">1.0.0</span>
            </div>
            <div className="flex justify-between py-1 border-b border-muted">
              <span className="text-muted-foreground">المشروع</span>
              <span>مشروع دمّر - دمشق</span>
            </div>
            <div className="flex justify-between py-1 border-b border-muted">
              <span className="text-muted-foreground">اللغة</span>
              <span>العربية (RTL)</span>
            </div>
            <Separator className="my-2" />
            <p className="text-xs text-muted-foreground text-center">
              منصة إدارة مشروع دمّر © 2024 - جميع الحقوق محفوظة
            </p>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
