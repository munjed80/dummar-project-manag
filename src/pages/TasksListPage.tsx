import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Input } from '@/components/ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MagnifyingGlass } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { describeLoadError } from '@/lib/loadError';
import { queryKeys } from '@/lib/queryKeys';
import {
  DataTableShell, DataToolbar, StatusBadge, PriorityBadge,
  EmptyState, ErrorState, LoadingSkeleton, PaginationBar, MobileEntityCard,
  RefreshingIndicator, StaleDataNotice,
  type StatusTone,
} from '@/components/data';

const statusLabels: Record<string, string> = {
  pending: 'معلقة', assigned: 'مُعينة', in_progress: 'قيد التنفيذ',
  completed: 'مكتملة', cancelled: 'ملغاة',
};

const statusTones: Record<string, StatusTone> = {
  pending: 'warning', assigned: 'progress', in_progress: 'progress',
  completed: 'success', cancelled: 'neutral',
};

const priorityLabels: Record<string, string> = {
  low: 'منخفضة', medium: 'متوسطة', high: 'عالية', urgent: 'عاجلة',
};

const sourceLabels: Record<string, string> = {
  complaint: 'شكوى', internal: 'داخلي', contract: 'عقد',
};

const PAGE_SIZE = 15;

export default function TasksListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProject = searchParams.get('project_id') || 'all';
  const initialTeam = searchParams.get('team_id') || 'all';
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState(initialProject);
  const [teamFilter, setTeamFilter] = useState(initialTeam);
  const [page, setPage] = useState(0);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (projectFilter === 'all') next.delete('project_id');
    else next.set('project_id', projectFilter);
    if (teamFilter === 'all') next.delete('team_id');
    else next.set('team_id', teamFilter);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectFilter, teamFilter]);

  // Selector lookups — shared cache across pages.
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects.selector(),
    queryFn: () => apiService.getProjects({ limit: 200 }).then((d) => d.items || []),
    staleTime: 5 * 60_000,
  });
  const teamsQuery = useQuery({
    queryKey: queryKeys.teams.active(),
    queryFn: () => apiService.getActiveTeams().then((d) => Array.isArray(d) ? d : []),
    staleTime: 5 * 60_000,
  });
  const projects = projectsQuery.data ?? [];
  const teams = teamsQuery.data ?? [];

  const listParams = useMemo(() => {
    const params: Record<string, unknown> = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (priorityFilter !== 'all') params.priority = priorityFilter;
    if (projectFilter !== 'all') params.project_id = Number(projectFilter);
    if (teamFilter !== 'all') params.team_id = Number(teamFilter);
    if (search) params.search = search;
    return params;
  }, [page, statusFilter, priorityFilter, projectFilter, teamFilter, search]);

  const tasksQuery = useQuery({
    queryKey: queryKeys.tasks.list(listParams),
    queryFn: () => apiService.getTasks(listParams as any),
    placeholderData: keepPreviousData,
  });

  const data = tasksQuery.data;
  const tasks = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const firstLoad = tasksQuery.isPending && !data;
  const refreshing = tasksQuery.isFetching && !!data;
  const refreshFailed = tasksQuery.isError && !!data;
  const fullPageError = tasksQuery.isError && !data;
  const error = fullPageError
    ? describeLoadError(tasksQuery.error, 'المهام').message
    : '';

  const projectMap = Object.fromEntries(projects.map((p: any) => [p.id, p.title]));
  const teamMap = Object.fromEntries(teams.map((t: any) => [t.id, t.name]));

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const hasActiveFilters = search.length > 0
    || statusFilter !== 'all'
    || priorityFilter !== 'all'
    || projectFilter !== 'all'
    || teamFilter !== 'all';

  return (
    <Layout>
      <Card className="border-[#D8E2EF]">
        <CardHeader>
          <CardTitle className="text-2xl text-[#0F2A4A]">المهام</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataToolbar
            search={(
              <div className="relative">
                <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                <Input
                  placeholder="بحث بالعنوان..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                  className="pr-10"
                />
              </div>
            )}
            filters={(
              <>
                <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[170px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الحالات</SelectItem>
                    {Object.entries(statusLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={priorityFilter} onValueChange={(v) => { setPriorityFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[170px]"><SelectValue placeholder="الأولوية" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الأولويات</SelectItem>
                    {Object.entries(priorityLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={projectFilter} onValueChange={(v) => { setProjectFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[170px]"><SelectValue placeholder="المشروع" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع المشاريع</SelectItem>
                    {projects.map((p: any) => (
                      <SelectItem key={p.id} value={String(p.id)}>{p.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={teamFilter} onValueChange={(v) => { setTeamFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[170px]"><SelectValue placeholder="الفريق" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع الفرق</SelectItem>
                    {teams.map((t: any) => (
                      <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </>
            )}
          />

          {error && (
            <ErrorState message={error} onRetry={() => tasksQuery.refetch()} retrying={tasksQuery.isFetching} />
          )}

          {refreshFailed && (
            <StaleDataNotice onRetry={() => tasksQuery.refetch()} retrying={refreshing} />
          )}
          {refreshing && !refreshFailed && (
            <RefreshingIndicator />
          )}

          {firstLoad && !error && (
            <>
              <div className="responsive-table-desktop">
                <DataTableShell>
                  <LoadingSkeleton rows={6} columns={8} />
                </DataTableShell>
              </div>
              <div className="responsive-cards-mobile">
                <LoadingSkeleton rows={5} variant="cards" />
              </div>
            </>
          )}

          {!firstLoad && !error && (
            <>
              {/* Desktop table view */}
              <div className="responsive-table-desktop">
                {tasks.length === 0 ? (
                  <EmptyState
                    title={hasActiveFilters ? 'لم يتم العثور على نتائج مطابقة' : 'لا توجد مهام حالياً'}
                  />
                ) : (
                  <DataTableShell>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-right">العنوان</TableHead>
                          <TableHead className="text-right">المصدر</TableHead>
                          <TableHead className="text-right">الحالة</TableHead>
                          <TableHead className="text-right">الأولوية</TableHead>
                          <TableHead className="text-right">المشروع</TableHead>
                          <TableHead className="text-right">الفريق</TableHead>
                          <TableHead className="text-right">تاريخ الاستحقاق</TableHead>
                          <TableHead className="text-right">التاريخ</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {tasks.map((t) => (
                          <TableRow
                            key={t.id}
                            className="cursor-pointer"
                            onClick={() => navigate(`/tasks/${t.id}`)}
                          >
                            <TableCell className="font-medium text-[#0F2A4A]">{t.title}</TableCell>
                            <TableCell>{sourceLabels[t.source_type] || t.source_type || '-'}</TableCell>
                            <TableCell>
                              <StatusBadge tone={statusTones[t.status] ?? 'neutral'}>
                                {statusLabels[t.status] || t.status}
                              </StatusBadge>
                            </TableCell>
                            <TableCell>
                              <PriorityBadge
                                priority={t.priority}
                                label={priorityLabels[t.priority] || t.priority}
                              />
                            </TableCell>
                            <TableCell>{t.project_id ? (projectMap[t.project_id] || `#${t.project_id}`) : '-'}</TableCell>
                            <TableCell>{t.team_id ? (teamMap[t.team_id] || `#${t.team_id}`) : '-'}</TableCell>
                            <TableCell>{t.due_date ? format(new Date(t.due_date), 'yyyy/MM/dd') : '-'}</TableCell>
                            <TableCell>{t.created_at ? format(new Date(t.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </DataTableShell>
                )}
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {tasks.length === 0 ? (
                  <EmptyState
                    title={hasActiveFilters ? 'لم يتم العثور على نتائج مطابقة' : 'لا توجد مهام حالياً'}
                  />
                ) : (
                  tasks.map((t) => (
                    <MobileEntityCard
                      key={t.id}
                      onClick={() => navigate(`/tasks/${t.id}`)}
                      title={t.title}
                      badge={
                        <StatusBadge tone={statusTones[t.status] ?? 'neutral'}>
                          {statusLabels[t.status] || t.status}
                        </StatusBadge>
                      }
                      meta={(
                        <>
                          <span>{sourceLabels[t.source_type] || t.source_type || '-'}</span>
                          <span aria-hidden>•</span>
                          <PriorityBadge
                            priority={t.priority}
                            label={priorityLabels[t.priority] || t.priority}
                          />
                          {t.due_date && (
                            <>
                              <span aria-hidden>•</span>
                              <span>استحقاق: {format(new Date(t.due_date), 'yyyy/MM/dd')}</span>
                            </>
                          )}
                          {t.team_id && (
                            <>
                              <span aria-hidden>•</span>
                              <span>{teamMap[t.team_id] || `فريق #${t.team_id}`}</span>
                            </>
                          )}
                          {t.project_id && (
                            <>
                              <span aria-hidden>•</span>
                              <span>{projectMap[t.project_id] || `مشروع #${t.project_id}`}</span>
                            </>
                          )}
                          <span aria-hidden>•</span>
                          <span>{t.created_at ? format(new Date(t.created_at), 'yyyy/MM/dd') : '-'}</span>
                        </>
                      )}
                    />
                  ))
                )}
              </div>

              <PaginationBar
                page={page}
                totalPages={totalPages}
                totalCount={totalCount}
                pageSize={PAGE_SIZE}
                entityLabel="مهمة"
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
