import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MagnifyingGlass, Spinner, Warning, Plus } from '@phosphor-icons/react';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';

const typeLabels: Record<string, string> = {
  internal_team: 'فريق داخلي', contractor: 'مقاول', field_crew: 'طاقم ميداني', supervision_unit: 'وحدة إشراف',
};

const PAGE_SIZE = 15;

export default function TeamsListPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const [teams, setTeams] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [activeFilter, setActiveFilter] = useState('all');
  const [page, setPage] = useState(0);

  const canCreate = role && ['project_director', 'contracts_manager', 'engineer_supervisor'].includes(role);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (typeFilter !== 'all') params.team_type = typeFilter;
    if (activeFilter !== 'all') params.is_active = activeFilter === 'active';
    if (search) params.search = search;
    apiService.getTeams(params)
      .then((data) => {
        setTeams(data.items);
        setTotalCount(data.total_count);
      })
      .catch((err) => setError(describeLoadError(err, 'الفرق').message))
      .finally(() => setLoading(false));
  }, [typeFilter, activeFilter, search, page]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Layout>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="text-2xl">الفرق التنفيذية</CardTitle>
            {canCreate && (
              <Button onClick={() => navigate('/teams/new')}>
                <Plus size={20} className="ml-1" />
                إضافة فريق
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث باسم الفريق..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                className="pr-10"
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="النوع" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الأنواع</SelectItem>
                  {Object.entries(typeLabels).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={activeFilter} onValueChange={(v) => { setActiveFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[140px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">الكل</SelectItem>
                  <SelectItem value="active">نشط</SelectItem>
                  <SelectItem value="inactive">غير نشط</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {loading && (
            <div className="flex justify-center py-8">
              <Spinner className="animate-spin text-primary" size={32} />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-destructive py-4">
              <Warning size={20} />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && teams.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg mb-2">لا توجد فرق بعد</p>
              {canCreate && (
                <Button onClick={() => navigate('/teams/new')} className="mt-4">
                  إضافة أول فريق
                </Button>
              )}
            </div>
          )}

          {!loading && !error && teams.length > 0 && (
            <>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>اسم الفريق</TableHead>
                      <TableHead>النوع</TableHead>
                      <TableHead>جهة الاتصال</TableHead>
                      <TableHead>المهام</TableHead>
                      <TableHead>الحالة</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {teams.map((team) => (
                      <TableRow key={team.id} onClick={() => navigate(`/teams/${team.id}`)} className="cursor-pointer hover:bg-muted/50">
                        <TableCell className="font-semibold">{team.name}</TableCell>
                        <TableCell>{typeLabels[team.team_type] || team.team_type}</TableCell>
                        <TableCell>{team.contact_name || '-'}</TableCell>
                        <TableCell>{team.task_count || 0}</TableCell>
                        <TableCell>
                          <Badge className={team.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {team.is_active ? 'نشط' : 'غير نشط'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                  عرض {page * PAGE_SIZE + 1} - {Math.min((page + 1) * PAGE_SIZE, totalCount)} من {totalCount}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
                    السابق
                  </Button>
                  <Button variant="outline" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>
                    التالي
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
