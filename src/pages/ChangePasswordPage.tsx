import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card';
import { apiService } from '@/services/api';
import { toast } from 'sonner';

/**
 * Self-service password change page.
 *
 * Reachable in two ways:
 *   1. The user is forced here right after login when the backend reports
 *      `must_change_password=true` (admin-created accounts and admin-reset
 *      passwords).
 *   2. The user explicitly navigates here from settings / nav.
 *
 * Calls POST /auth/change-password, which verifies the current password,
 * stores the new hash, and clears the must_change_password flag.
 */
export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const mustChange = localStorage.getItem('must_change_password') === '1';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword) {
      toast.error('يرجى ملء جميع الحقول');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('يجب أن تكون كلمة المرور 8 أحرف على الأقل');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('كلمتا المرور غير متطابقتين');
      return;
    }
    if (newPassword === currentPassword) {
      toast.error('يجب أن تختلف كلمة المرور الجديدة عن الحالية');
      return;
    }
    setSaving(true);
    try {
      await apiService.changeMyPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success('تم تغيير كلمة المرور بنجاح');
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err?.message || 'فشل تغيير كلمة المرور');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 to-accent/10 p-4"
      dir="rtl"
    >
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">تغيير كلمة المرور</CardTitle>
          <CardDescription>
            {mustChange
              ? 'يجب تغيير كلمة المرور المؤقتة قبل متابعة استخدام النظام'
              : 'تحديث كلمة مرور حسابك'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current_password">كلمة المرور الحالية</Label>
              <Input
                id="current_password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                disabled={saving}
                autoComplete="current-password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">كلمة المرور الجديدة</Label>
              <Input
                id="new_password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                disabled={saving}
                autoComplete="new-password"
                minLength={8}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">تأكيد كلمة المرور الجديدة</Label>
              <Input
                id="confirm_password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={saving}
                autoComplete="new-password"
                minLength={8}
              />
            </div>
            <Button type="submit" className="w-full" disabled={saving}>
              {saving ? 'جارٍ الحفظ...' : 'حفظ كلمة المرور الجديدة'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
