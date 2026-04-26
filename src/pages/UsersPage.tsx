import { useState, useEffect, useCallback } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import type { User } from '@/services/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { MagnifyingGlass, Spinner, UserPlus, PencilSimple, UserMinus, Key } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { describeLoadError } from '@/lib/loadError';
import { ApiError } from '@/services/api';

const roleLabels: Record<string, string> = {
  project_director: 'مدير المشروع',
  contracts_manager: 'مدير العقود',
  engineer_supervisor: 'مشرف هندسي',
  complaints_officer: 'مسؤول الشكاوى',
  area_supervisor: 'مشرف المنطقة',
  field_team: 'فريق ميداني',
  contractor_user: 'مستخدم مقاول',
  citizen: 'مواطن',
  property_manager: 'مسؤول الأملاك',
  investment_manager: 'مسؤول الاستثمار',
};

const roleColors: Record<string, string> = {
  project_director: 'bg-purple-100 text-purple-800',
  contracts_manager: 'bg-blue-100 text-blue-800',
  engineer_supervisor: 'bg-cyan-100 text-cyan-800',
  complaints_officer: 'bg-orange-100 text-orange-800',
  area_supervisor: 'bg-green-100 text-green-800',
  field_team: 'bg-yellow-100 text-yellow-800',
  contractor_user: 'bg-red-100 text-red-800',
  citizen: 'bg-gray-100 text-gray-800',
  property_manager: 'bg-indigo-100 text-indigo-800',
  investment_manager: 'bg-pink-100 text-pink-800',
};

const ROLES = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'property_manager', 'investment_manager',
  'field_team', 'contractor_user', 'citizen',
];

const PAGE_SIZE = 15;

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [page, setPage] = useState(0);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({ username: '', full_name: '', password: '', role: 'field_team', phone: '' });
  const [saving, setSaving] = useState(false);

  const [deactivateTarget, setDeactivateTarget] = useState<User | null>(null);
  const [activateTarget, setActivateTarget] = useState<User | null>(null);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetForceChange, setResetForceChange] = useState(true);
  const [resetting, setResetting] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
      if (search) params.search = search;
      if (roleFilter !== 'all') params.role_filter = roleFilter;
      const result = await apiService.getUsers(params);
      setUsers(result.items);
      setTotalCount(result.total_count);
    } catch (err) {
      setError(describeLoadError(err, 'المستخدمين').message);
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter]);

  const toArabicActionError = (err: unknown, fallback: string): string => {
    if (err instanceof ApiError) {
      if (err.status === 401) return 'انتهت الجلسة. يرجى تسجيل الدخول مرة أخرى.';
      if (err.status === 403) return 'ليس لديك صلاحية لتنفيذ هذا الإجراء.';
      if (err.status === 400 && err.detail) return `تعذّر تنفيذ الطلب: ${err.detail}`;
      if (err.detail) return `تعذّر تنفيذ الطلب: ${err.detail}`;
    }
    return fallback;
  };

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const openCreateDialog = () => {
    setEditingUser(null);
    setFormData({ username: '', full_name: '', password: '', role: 'field_team', phone: '' });
    setDialogOpen(true);
  };

  const openEditDialog = (user: User) => {
    setEditingUser(user);
    setFormData({ username: user.username, full_name: user.full_name, password: '', role: user.role, phone: user.phone || '' });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingUser) {
        // Admin edit: full_name, phone, role, active status.
        // Password is NOT changed here — use the dedicated reset action.
        const updateData: any = {
          full_name: formData.full_name,
          phone: formData.phone || undefined,
          role: formData.role,
          is_active: editingUser.is_active,
        };
        await apiService.updateUser(editingUser.id, updateData);
        toast.success('تم تحديث المستخدم بنجاح');
      } else {
        if (!formData.username || !formData.password || !formData.full_name) {
          toast.error('يرجى ملء الحقول المطلوبة');
          setSaving(false);
          return;
        }
        if (formData.password.length < 8) {
          toast.error('يجب أن تكون كلمة المرور 8 أحرف على الأقل');
          setSaving(false);
          return;
        }
        const createPayload: any = {
          username: formData.username,
          full_name: formData.full_name,
          password: formData.password,
          role: formData.role,
          phone: formData.phone || undefined,
          must_change_password: true,
        };
        await apiService.createUser(createPayload);
        toast.success('تم إنشاء المستخدم بنجاح');
      }
      setDialogOpen(false);
      await fetchUsers();
    } catch (err: any) {
      toast.error(toArabicActionError(err, 'فشل حفظ المستخدم'));
    } finally {
      setSaving(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resetTarget) return;
    if (resetPassword.length < 8) {
      toast.error('يجب أن تكون كلمة المرور 8 أحرف على الأقل');
      return;
    }
    setResetting(true);
    try {
      await apiService.resetUserPassword(resetTarget.id, {
        new_password: resetPassword,
        require_change_on_next_login: resetForceChange,
      });
      toast.success('تم تغيير كلمة المرور بنجاح');
      setResetTarget(null);
      setResetPassword('');
      setResetForceChange(true);
      await fetchUsers();
    } catch (err) {
      toast.error(toArabicActionError(err, 'فشل تغيير كلمة المرور'));
    } finally {
      setResetting(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateTarget) return;
    try {
      await apiService.deactivateUser(deactivateTarget.id);
      toast.success('تم إلغاء تفعيل المستخدم');
      setDeactivateTarget(null);
      await fetchUsers();
    } catch (err) {
      toast.error(toArabicActionError(err, 'فشل إلغاء تفعيل المستخدم'));
    }
  };

  const handleActivate = async () => {
    if (!activateTarget) return;
    try {
      await apiService.updateUser(activateTarget.id, { is_active: 1 });
      toast.success('تم تفعيل المستخدم');
      setActivateTarget(null);
      await fetchUsers();
    } catch (err) {
      toast.error(toArabicActionError(err, 'فشل تفعيل المستخدم'));
    }
  };

  return (
    <Layout>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-3">
          <CardTitle className="text-2xl">إدارة المستخدمين</CardTitle>
          <Button onClick={openCreateDialog}>
            <UserPlus className="ml-2" size={18} />
            إضافة مستخدم
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث بالاسم أو اسم المستخدم..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                className="pr-10"
              />
            </div>
            <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v); setPage(0); }}>
              <SelectTrigger className="w-[200px]"><SelectValue placeholder="الدور" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع الأدوار</SelectItem>
                {ROLES.map((r) => (
                  <SelectItem key={r} value={r}>{roleLabels[r] || r}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <div className="text-center py-8 text-destructive">{error}</div>
          )}

          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner className="animate-spin" size={32} />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-right">الاسم الكامل</TableHead>
                    <TableHead className="text-right">اسم المستخدم</TableHead>
                    <TableHead className="text-right">الدور</TableHead>
                    <TableHead className="text-right">الحالة</TableHead>
                    <TableHead className="text-right">تاريخ الإنشاء</TableHead>
                    <TableHead className="text-right">إجراءات</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        لا يوجد مستخدمون
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell className="font-medium">{u.full_name}</TableCell>
                        <TableCell className="font-mono text-sm">{u.username}</TableCell>
                        <TableCell>
                          <Badge className={roleColors[u.role] || 'bg-gray-100 text-gray-800'}>
                            {roleLabels[u.role] || u.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                            {u.is_active ? 'نشط' : 'معطل'}
                          </Badge>
                        </TableCell>
                        <TableCell>{u.created_at ? format(new Date(u.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openEditDialog(u)} title="تعديل">
                              <PencilSimple size={16} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => { setResetTarget(u); setResetPassword(''); setResetForceChange(true); }}
                              title="إعادة تعيين كلمة المرور"
                            >
                              <Key size={16} />
                            </Button>
                            {u.is_active ? (
                              <Button variant="ghost" size="sm" onClick={() => setDeactivateTarget(u)} className="text-destructive" title="إلغاء التفعيل">
                                <UserMinus size={16} />
                              </Button>
                            ) : (
                              <Button variant="ghost" size="sm" onClick={() => setActivateTarget(u)} title="تفعيل المستخدم">
                                تفعيل
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>السابق</Button>
                  <span className="text-sm text-muted-foreground">
                    صفحة {page + 1} من {totalPages} ({totalCount} مستخدم)
                  </span>
                  <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>التالي</Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[500px]" dir="rtl">
          <DialogHeader>
            <DialogTitle>{editingUser ? 'تعديل المستخدم' : 'إضافة مستخدم جديد'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {!editingUser && (
              <div className="space-y-2">
                <Label>اسم المستخدم *</Label>
                <Input value={formData.username} onChange={(e) => setFormData(f => ({ ...f, username: e.target.value }))} />
              </div>
            )}
            <div className="space-y-2">
              <Label>الاسم الكامل *</Label>
              <Input value={formData.full_name} onChange={(e) => setFormData(f => ({ ...f, full_name: e.target.value }))} />
            </div>
            {!editingUser && (
              <div className="space-y-2">
                <Label>كلمة المرور *</Label>
                <Input type="password" value={formData.password} onChange={(e) => setFormData(f => ({ ...f, password: e.target.value }))} />
              </div>
            )}
            <div className="space-y-2">
              <Label>رقم الهاتف</Label>
              <Input value={formData.phone} onChange={(e) => setFormData(f => ({ ...f, phone: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>الدور</Label>
              <Select value={formData.role} onValueChange={(v) => setFormData(f => ({ ...f, role: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r} value={r}>{roleLabels[r] || r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Spinner className="animate-spin ml-2" size={16} />}
              {editingUser ? 'حفظ التغييرات' : 'إنشاء'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={!!resetTarget} onOpenChange={(open) => { if (!open) { setResetTarget(null); setResetPassword(''); } }}>
        <DialogContent className="sm:max-w-[450px]" dir="rtl">
          <DialogHeader>
            <DialogTitle>إعادة تعيين كلمة المرور</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-muted-foreground">
              تعيين كلمة مرور جديدة للمستخدم{' '}
              <span className="font-semibold">{resetTarget?.full_name}</span> ({resetTarget?.username}).
            </p>
            <div className="space-y-2">
              <Label>كلمة المرور الجديدة *</Label>
              <Input
                type="password"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                minLength={8}
                placeholder="8 أحرف على الأقل"
                autoComplete="new-password"
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={resetForceChange}
                onChange={(e) => setResetForceChange(e.target.checked)}
                className="h-4 w-4"
              />
              مطالبة المستخدم بتغيير كلمة المرور عند تسجيل الدخول التالي
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetTarget(null)}>إلغاء</Button>
            <Button onClick={handleResetPassword} disabled={resetting}>
              {resetting && <Spinner className="animate-spin ml-2" size={16} />}
              تعيين كلمة المرور
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deactivate Confirmation */}
      <AlertDialog open={!!deactivateTarget} onOpenChange={(open) => { if (!open) setDeactivateTarget(null); }}>
        <AlertDialogContent dir="rtl">
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد إلغاء التفعيل</AlertDialogTitle>
            <AlertDialogDescription>
              هل أنت متأكد من إلغاء تفعيل المستخدم "{deactivateTarget?.full_name}"؟ لن يتمكن من تسجيل الدخول بعد ذلك.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeactivate} className="bg-destructive text-destructive-foreground">
              إلغاء التفعيل
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Activate Confirmation */}
      <AlertDialog open={!!activateTarget} onOpenChange={(open) => { if (!open) setActivateTarget(null); }}>
        <AlertDialogContent dir="rtl">
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد تفعيل المستخدم</AlertDialogTitle>
            <AlertDialogDescription>
              هل تريد تفعيل المستخدم "{activateTarget?.full_name}" ليتمكن من تسجيل الدخول؟
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction onClick={handleActivate}>
              تفعيل
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
