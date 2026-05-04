import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MagnifyingGlass, Plus, UsersThree } from '@phosphor-icons/react';
import { useAuth } from '@/hooks/useAuth';
import { describeLoadError } from '@/lib/loadError';
import { queryKeys } from '@/lib/queryKeys';
import {
  DataTableShell, DataToolbar, StatusBadge,
  EmptyState, ErrorState, LoadingSkeleton, PaginationBar, MobileEntityCard,
  RefreshingIndicator, StaleDataNotice,
} from '@/components/data';

const typeLabels: Record<string, string> = {
  internal_team: 'فريق داخلي', contractor: 'مقاول', field_crew: 'طاقم ميداني', supervision_unit: 'وحدة إشراف',
};

const PAGE_SIZE = 15;

export default function TeamsListPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [activeFilter, setActiveFilter] = useState('all');
  const [page, setPage] = useState(0);

  const canCreate = role && ['project_director', 'contracts_manager', 'engineer_supervisor'].includes(role);

  const listParams = useMemo(() => {
    const params: Record<string, unknown> = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (typeFilter !== 'all') params.team_type = typeFilter;
    if (activeFilter !== 'all') params.is_active = activeFilter === 'active';
    if (search) params.search = search;
    return params;
  }, [page, typeFilter, activeFilter, search]);

  const teamsQuery = useQuery({
    queryKey: queryKeys.teams.list(listParams),
    queryFn: () => apiService.getTeams(listParams as any),
    placeholderData: keepPreviousData,
  });

  const data = teamsQuery.data;
  const teams = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const firstLoad = teamsQuery.isPending && !data;
  const refreshing = teamsQuery.isFetching && !!data;
  const refreshFailed = teamsQuery.isError && !!data;
  const fullPageError = teamsQuery.isError && !data;
  const error = fullPageError
    ? describeLoadError(teamsQuery.error, 'الفرق').message
    : '';

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const hasActiveFilters = search.length > 0 || typeFilter !== 'all' || activeFilter !== 'all';

  return (
    <Layout>
      <Card className="border-[#D8E2EF]">
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-2">
            <CardTitle className="text-2xl text-[#0F2A4A]">الفرق التنفيذية</CardTitle>
            {canCreate && (
              <Button onClick={() => navigate('/teams/new')}>
                <Plus size={18} className="ml-1" />
                إضافة فريق
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataToolbar
            search={(
              <div className="relative">
                <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                <Input
                  placeholder="بحث باسم الفريق..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                  className="pr-10"
                />
              </div>
            )}
            filters={(
              <>
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
              </>
            )}
          />

          {error && (
            <ErrorState message={error} onRetry={() => teamsQuery.refetch()} retrying={teamsQuery.isFetching} />
          )}

          {refreshFailed && (
            <StaleDataNotice onRetry={() => teamsQuery.refetch()} retrying={refreshing} />
          )}
          {refreshing && !refreshFailed && (
            <RefreshingIndicator />
          )}

          {firstLoad && !error && (
            <>
              <div className="responsive-table-desktop">
                <DataTableShell>
                  <LoadingSkeleton rows={5} columns={5} />
                </DataTableShell>
              </div>
              <div className="responsive-cards-mobile">
                <LoadingSkeleton rows={4} variant="cards" />
              </div>
            </>
          )}

          {!firstLoad && !error && teams.length === 0 && (
            <EmptyState
              icon={<UsersThree size={40} weight="duotone" />}
              title={hasActiveFilters ? 'لم يتم العثور على نتائج مطابقة' : 'لا توجد فرق بعد'}
              action={canCreate && !hasActiveFilters && (
                <Button onClick={() => navigate('/teams/new')}>إضافة أول فريق</Button>
              )}
            />
          )}

          {!firstLoad && !error && teams.length > 0 && (
            <>
              {/* Desktop table view */}
              <div className="responsive-table-desktop">
                <DataTableShell>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-right">اسم الفريق</TableHead>
                        <TableHead className="text-right">النوع</TableHead>
                        <TableHead className="text-right">جهة الاتصال</TableHead>
                        <TableHead className="text-right">المهام</TableHead>
                        <TableHead className="text-right">الحالة</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {teams.map((team) => (
                        <TableRow
                          key={team.id}
                          onClick={() => navigate(`/teams/${team.id}`)}
                          className="cursor-pointer"
                        >
                          <TableCell className="font-semibold text-[#0F2A4A]">{team.name}</TableCell>
                          <TableCell>{typeLabels[team.team_type] || team.team_type}</TableCell>
                          <TableCell>{team.contact_name || '-'}</TableCell>
                          <TableCell>{team.task_count || 0}</TableCell>
                          <TableCell>
                            <StatusBadge tone={team.is_active ? 'success' : 'neutral'}>
                              {team.is_active ? 'نشط' : 'غير نشط'}
                            </StatusBadge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </DataTableShell>
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {teams.map((team) => (
                  <MobileEntityCard
                    key={team.id}
                    onClick={() => navigate(`/teams/${team.id}`)}
                    title={team.name}
                    badge={
                      <StatusBadge tone={team.is_active ? 'success' : 'neutral'}>
                        {team.is_active ? 'نشط' : 'غير نشط'}
                      </StatusBadge>
                    }
                    meta={(
                      <>
                        <span>{typeLabels[team.team_type] || team.team_type}</span>
                        {team.contact_name && (
                          <>
                            <span aria-hidden>•</span>
                            <span>{team.contact_name}</span>
                          </>
                        )}
                        <span aria-hidden>•</span>
                        <span>{team.task_count || 0} مهمة</span>
                      </>
                    )}
                  />
                ))}
              </div>

              <PaginationBar
                page={page}
                totalPages={totalPages}
                totalCount={totalCount}
                pageSize={PAGE_SIZE}
                entityLabel="فريق"
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
