import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiService } from '@/services/api';
import { toast } from 'sonner';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      toast.error('يرجى إدخال اسم المستخدم وكلمة المرور');
      return;
    }
    setLoading(true);

    try {
      await apiService.login({ username, password });
      if (localStorage.getItem('must_change_password') === '1') {
        toast.info('يجب تغيير كلمة المرور قبل المتابعة');
        navigate('/change-password');
      } else {
        toast.success('تم تسجيل الدخول بنجاح');
        navigate('/dashboard');
      }
    } catch (error) {
      toast.error('فشل تسجيل الدخول. تحقق من اسم المستخدم وكلمة المرور.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 to-accent/10 p-4" dir="rtl">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">منصة إدارة مشروع دمر</CardTitle>
          <CardDescription>تسجيل الدخول إلى لوحة التحكم</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">اسم المستخدم</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="أدخل اسم المستخدم"
                required
                disabled={loading}
                autoComplete="username"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">كلمة المرور</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="أدخل كلمة المرور"
                required
                disabled={loading}
                autoComplete="current-password"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'جاري تسجيل الدخول...' : 'تسجيل الدخول'}
            </Button>
          </form>
          <div className="mt-6 text-center">
            <button
              type="button"
              className="text-xs text-muted-foreground underline hover:text-foreground transition-colors"
              onClick={() => setShowHelp(!showHelp)}
            >
              {showHelp ? 'إخفاء المساعدة' : 'هل تحتاج مساعدة في تسجيل الدخول؟'}
            </button>
            {showHelp && (
              <p className="text-xs text-muted-foreground mt-2">
                تواصل مع مدير النظام للحصول على بيانات تسجيل الدخول الخاصة بك.
              </p>
            )}
          </div>

          {/* Public-flow shortcuts so a citizen who lands here can still
              reach the complaint submit / track pages without typing URLs. */}
          <div className="mt-6 pt-4 border-t text-center space-y-2">
            <p className="text-xs text-muted-foreground">هل أنت مواطن وتريد تقديم أو تتبع شكوى؟</p>
            <div className="flex flex-col sm:flex-row gap-2 justify-center">
              <Link to="/complaints/new" className="text-sm text-primary hover:underline">تقديم شكوى جديدة</Link>
              <span className="hidden sm:inline text-muted-foreground">·</span>
              <Link to="/complaints/track" className="text-sm text-primary hover:underline">تتبع شكوى سابقة</Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
