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
import { MagnifyingGlass, Spinner, UserPlus, PencilSimple, UserMinus } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

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

const roleColors: Record<string, string> = {
  project_director: 'bg-purple-100 text-purple-800',
  contracts_manager: 'bg-blue-100 text-blue-800',
  engineer_supervisor: 'bg-cyan-100 text-cyan-800',
  complaints_officer: 'bg-orange-100 text-orange-800',
  area_supervisor: 'bg-green-100 text-green-800',
  field_team: 'bg-yellow-100 text-yellow-800',
  contractor_user: 'bg-red-100 text-red-800',
  citizen: 'bg-gray-100 text-gray-800',
};

const ROLES = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user', 'citizen',
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
  const [formData, setFormData] = useState({ username: '', email: '', full_name: '', password: '', role: 'field_team', phone: '' });
  const [saving, setSaving] = useState(false);

  const [deactivateTarget, setDeactivateTarget] = useState<User | null>(null);

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
    } catch {
      setError('فشل تحميل المستخدمين');
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const openCreateDialog = () => {
    setEditingUser(null);
    setFormData({ username: '', email: '', full_name: '', password: '', role: 'field_team', phone: '' });
    setDialogOpen(true);
  };

  const openEditDialog = (user: User) => {
    setEditingUser(user);
    setFormData({ username: user.username, email: user.email || '', full_name: user.full_name, password: '', role: user.role, phone: user.phone || '' });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingUser) {
        const updateData: any = { full_name: formData.full_name, email: formData.email || undefined, phone: formData.phone || undefined, role: formData.role };
        await apiService.updateUser(editingUser.id, updateData);
        toast.success('تم تحديث المستخدم بنجاح');
      } else {
        if (!formData.username || !formData.password || !formData.full_name) {
          toast.error('يرجى ملء الحقول المطلوبة');
          setSaving(false);
          return;
        }
        await apiService.createUser(formData);
        toast.success('تم إنشاء المستخدم بنجاح');
      }
      setDialogOpen(false);
      fetchUsers();
    } catch (err: any) {
      toast.error(err.message || 'فشل حفظ المستخدم');
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateTarget) return;
    try {
      await apiService.deactivateUser(deactivateTarget.id);
      toast.success('تم إلغاء تفعيل المستخدم');
      setDeactivateTarget(null);
      fetchUsers();
    } catch {
      toast.error('فشل إلغاء تفعيل المستخدم');
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
                placeholder="بحث بالاسم أو البريد..."
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
                    <TableHead className="text-right">البريد</TableHead>
                    <TableHead className="text-right">الدور</TableHead>
                    <TableHead className="text-right">الحالة</TableHead>
                    <TableHead className="text-right">تاريخ الإنشاء</TableHead>
                    <TableHead className="text-right">إجراءات</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        لا يوجد مستخدمون
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell className="font-medium">{u.full_name}</TableCell>
                        <TableCell className="font-mono text-sm">{u.username}</TableCell>
                        <TableCell className="text-sm">{u.email || '-'}</TableCell>
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
                            <Button variant="ghost" size="sm" onClick={() => openEditDialog(u)}>
                              <PencilSimple size={16} />
                            </Button>
                            {u.is_active ? (
                              <Button variant="ghost" size="sm" onClick={() => setDeactivateTarget(u)} className="text-destructive">
                                <UserMinus size={16} />
                              </Button>
                            ) : null}
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
            <div className="space-y-2">
              <Label>البريد الإلكتروني</Label>
              <Input type="email" value={formData.email} onChange={(e) => setFormData(f => ({ ...f, email: e.target.value }))} />
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
    </Layout>
  );
}
