import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { MagnifyingGlass, UserCircle } from '@phosphor-icons/react';
import { format } from 'date-fns';
import {
  DataTableShell, DataToolbar, StatusBadge,
  EmptyState, ErrorState, LoadingSkeleton, MobileEntityCard,
  type StatusTone,
} from '@/components/data';

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

// Soft, semantic tones — no saturated brand colors on a per-row basis.
const roleTones: Record<string, StatusTone> = {
  project_director: 'accent',
  contracts_manager: 'info',
  engineer_supervisor: 'progress',
  complaints_officer: 'warning',
  area_supervisor: 'info',
  field_team: 'success',
  contractor_user: 'warning',
  citizen: 'neutral',
  property_manager: 'progress',
  investment_manager: 'info',
};

export default function UsersListPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError('');
    apiService.getUsers()
      .then((data) => setUsers(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message || 'فشل تحميل المستخدمين'))
      .finally(() => setLoading(false));
  }, [reloadTick]);

  const filtered = users.filter((u) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      u.full_name?.toLowerCase().includes(q) ||
      u.username?.toLowerCase().includes(q) ||
      u.phone?.includes(q)
    );
  });

  return (
    <Layout>
      <Card className="border-[#D8E2EF]">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2 text-[#0F2A4A]">
            <UserCircle size={26} weight="duotone" />
            المستخدمون
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataToolbar
            search={(
              <div className="relative">
                <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                <Input
                  placeholder="بحث بالاسم أو اسم المستخدم أو الهاتف..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pr-10"
                />
              </div>
            )}
          />

          {error && (
            <ErrorState message={error} onRetry={() => setReloadTick((t) => t + 1)} retrying={loading} />
          )}

          {loading && !error && (
            <>
              <div className="responsive-table-desktop">
                <DataTableShell>
                  <LoadingSkeleton rows={6} columns={6} />
                </DataTableShell>
              </div>
              <div className="responsive-cards-mobile">
                <LoadingSkeleton rows={5} variant="cards" />
              </div>
            </>
          )}

          {!loading && !error && (
            <>
              {/* Desktop table view */}
              <div className="responsive-table-desktop">
                {filtered.length === 0 ? (
                  <EmptyState title={search ? 'لم يتم العثور على نتائج مطابقة' : 'لا يوجد مستخدمون'} />
                ) : (
                  <DataTableShell>
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
                        {filtered.map((u) => (
                          <TableRow key={u.id}>
                            <TableCell className="font-medium text-[#0F2A4A]">{u.full_name}</TableCell>
                            <TableCell className="font-mono text-sm">{u.username}</TableCell>
                            <TableCell dir="ltr" className="text-right">{u.phone || '-'}</TableCell>
                            <TableCell>
                              <StatusBadge tone={roleTones[u.role] ?? 'neutral'}>
                                {roleLabels[u.role] || u.role}
                              </StatusBadge>
                            </TableCell>
                            <TableCell>
                              <StatusBadge tone={u.is_active ? 'success' : 'danger'}>
                                {u.is_active ? 'نشط' : 'معطّل'}
                              </StatusBadge>
                            </TableCell>
                            <TableCell>{u.created_at ? format(new Date(u.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </DataTableShell>
                )}
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {filtered.length === 0 ? (
                  <EmptyState title={search ? 'لم يتم العثور على نتائج مطابقة' : 'لا يوجد مستخدمون'} />
                ) : (
                  filtered.map((u) => (
                    <MobileEntityCard
                      key={u.id}
                      title={u.full_name}
                      badge={
                        <StatusBadge tone={u.is_active ? 'success' : 'danger'}>
                          {u.is_active ? 'نشط' : 'معطّل'}
                        </StatusBadge>
                      }
                      subtitle={
                        <span className="font-mono text-xs text-slate-600">{u.username}</span>
                      }
                      meta={(
                        <>
                          <StatusBadge tone={roleTones[u.role] ?? 'neutral'}>
                            {roleLabels[u.role] || u.role}
                          </StatusBadge>
                          {u.phone && (
                            <>
                              <span aria-hidden>•</span>
                              <span dir="ltr">{u.phone}</span>
                            </>
                          )}
                          {u.created_at && (
                            <>
                              <span aria-hidden>•</span>
                              <span>{format(new Date(u.created_at), 'yyyy/MM/dd')}</span>
                            </>
                          )}
                        </>
                      )}
                    />
                  ))
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
