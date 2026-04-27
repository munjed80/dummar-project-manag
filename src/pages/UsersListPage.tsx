import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { MagnifyingGlass, Spinner, UserCircle } from '@phosphor-icons/react';
import { format } from 'date-fns';

const roleLabels: Record<string, string> = {
  project_director: 'مدير المشروع',
  contracts_manager: 'مدير العقود',
  engineer_supervisor: 'مهندس مشرف',
  complaints_officer: 'مسؤول الشكاوى',
  area_supervisor: 'مشرف منطقة',
  field_team: 'فريق ميداني',
  contractor_user: 'مستخدم مقاول',
  citizen: 'مواطن',
  property_manager: 'مسؤول الأصول',
  investment_manager: 'مسؤول الاستثمار',
};

const roleColors: Record<string, string> = {
  project_director: 'bg-purple-100 text-purple-800',
  contracts_manager: 'bg-blue-100 text-blue-800',
  engineer_supervisor: 'bg-teal-100 text-teal-800',
  complaints_officer: 'bg-orange-100 text-orange-800',
  area_supervisor: 'bg-cyan-100 text-cyan-800',
  field_team: 'bg-green-100 text-green-800',
  contractor_user: 'bg-yellow-100 text-yellow-800',
  citizen: 'bg-gray-100 text-gray-800',
  property_manager: 'bg-indigo-100 text-indigo-800',
  investment_manager: 'bg-pink-100 text-pink-800',
};

export default function UsersListPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    apiService.getUsers()
      .then((data) => setUsers(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message || 'فشل تحميل المستخدمين'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = users.filter((u) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      u.full_name?.toLowerCase().includes(q) ||
      u.username?.toLowerCase().includes(q) ||
      u.phone?.includes(q)
    );
  });

  if (error) {
    return (
      <Layout>
        <div className="text-center py-12 text-destructive">{error}</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <UserCircle size={28} />
            المستخدمون
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative max-w-md">
            <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
            <Input
              placeholder="بحث بالاسم أو اسم المستخدم أو الهاتف..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pr-10"
            />
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner className="animate-spin" size={32} />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-right">الاسم الكامل</TableHead>
                  <TableHead className="text-right">اسم المستخدم</TableHead>
                  <TableHead className="text-right">الهاتف</TableHead>
                  <TableHead className="text-right">الدور</TableHead>
                  <TableHead className="text-right">الحالة</TableHead>
                  <TableHead className="text-right">تاريخ الإنشاء</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      لا يوجد مستخدمون
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell className="font-medium">{u.full_name}</TableCell>
                      <TableCell className="font-mono text-sm">{u.username}</TableCell>
                      <TableCell dir="ltr" className="text-right">{u.phone || '-'}</TableCell>
                      <TableCell>
                        <Badge className={roleColors[u.role] || 'bg-gray-100 text-gray-800'}>
                          {roleLabels[u.role] || u.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {u.is_active ? 'نشط' : 'معطّل'}
                        </Badge>
                      </TableCell>
                      <TableCell>{u.created_at ? format(new Date(u.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
