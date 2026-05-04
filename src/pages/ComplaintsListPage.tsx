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
  new: 'قيد المعالجة', under_review: 'قيد المعالجة', assigned: 'قيد المعالجة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};

const statusTones: Record<string, StatusTone> = {
  new: 'progress', under_review: 'progress', assigned: 'progress',
  in_progress: 'progress', resolved: 'success', rejected: 'danger',
};

// Filter options use individual backend values; قيد المعالجة maps to 'new'
// (the default initial state for all new complaints).
const statusFilterOptions = [
  { value: 'new', label: 'قيد المعالجة' },
  { value: 'in_progress', label: 'قيد التنفيذ' },
  { value: 'resolved', label: 'تم الحل' },
  { value: 'rejected', label: 'مرفوضة' },
];

const priorityLabels: Record<string, string> = {
  low: 'منخفضة', medium: 'متوسطة', high: 'عالية', urgent: 'عاجلة',
};

const typeLabels: Record<string, string> = {
  infrastructure: 'البنية التحتية', cleaning: 'النظافة', electricity: 'الكهرباء',
  water: 'المياه', roads: 'الطرق', lighting: 'الإنارة',
  heating_network: 'صيانة شبكة التدفئة', corruption: 'شكوى فساد', other: 'أخرى',
};

const PAGE_SIZE = 15;

export default function ComplaintsListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProject = searchParams.get('project_id') || 'all';
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [areaFilter, setAreaFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState(initialProject);
  const [page, setPage] = useState(0);

  // Keep URL in sync when project filter changes so deep links remain shareable.
  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (projectFilter === 'all') next.delete('project_id');
    else next.set('project_id', projectFilter);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectFilter]);

  // Shared selector lookups — cached across pages via stable query keys
  // so navigating between Complaints/Tasks does not refetch them.
  const areasQuery = useQuery({
    queryKey: queryKeys.areas.all(),
    queryFn: () => apiService.getAreas(),
    staleTime: 5 * 60_000,
  });
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects.selector(),
    queryFn: () => apiService.getProjects({ limit: 200 }).then((d) => d.items || []),
    staleTime: 5 * 60_000,
  });
  const areas = areasQuery.data ?? [];
  const projects = projectsQuery.data ?? [];

  const listParams = useMemo(() => {
    const params: Record<string, unknown> = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (areaFilter !== 'all') params.area_id = Number(areaFilter);
    if (projectFilter !== 'all') params.project_id = Number(projectFilter);
    if (search) params.search = search;
    return params;
  }, [page, statusFilter, areaFilter, projectFilter, search]);

  const complaintsQuery = useQuery({
    queryKey: queryKeys.complaints.list(listParams),
    queryFn: () => apiService.getComplaints(listParams as any),
    placeholderData: keepPreviousData,
  });

  const data = complaintsQuery.data;
  const complaints = data?.items ?? [];
  const totalCount = data?.total_count ?? 0;
  const firstLoad = complaintsQuery.isPending && !data;
  const refreshing = complaintsQuery.isFetching && !!data;
  const refreshFailed = complaintsQuery.isError && !!data;
  const fullPageError = complaintsQuery.isError && !data;
  const error = fullPageError
    ? describeLoadError(complaintsQuery.error, 'الشكاوى').message
    : '';

  const areaMap = Object.fromEntries(areas.map((a: any) => [a.id, a.name_ar || a.name]));
  const projectMap = Object.fromEntries(projects.map((p: any) => [p.id, p.title]));

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const hasActiveFilters = search.length > 0
    || statusFilter !== 'all'
    || areaFilter !== 'all'
    || projectFilter !== 'all';

  return (
    <Layout>
      <Card className="border-[#D8E2EF]">
        <CardHeader>
          <CardTitle className="text-2xl text-[#0F2A4A]">الشكاوى</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataToolbar
            search={(
              <div className="relative">
                <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                <Input
                  placeholder="بحث برقم التتبع أو الاسم..."
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
                    {statusFilterOptions.map(({ value: k, label: v }) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={areaFilter} onValueChange={(v) => { setAreaFilter(v); setPage(0); }}>
                  <SelectTrigger className="flex-1 sm:w-[170px]"><SelectValue placeholder="المنطقة / الحي" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">جميع المناطق</SelectItem>
                    {areas.map((a: any) => (
                      <SelectItem key={a.id} value={String(a.id)}>{a.name_ar || a.name}</SelectItem>
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
              </>
            )}
          />

          {error && (
            <ErrorState message={error} onRetry={() => complaintsQuery.refetch()} retrying={complaintsQuery.isFetching} />
          )}

          {refreshFailed && (
            <StaleDataNotice onRetry={() => complaintsQuery.refetch()} retrying={refreshing} />
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
                {complaints.length === 0 ? (
                  <EmptyState
                    title={hasActiveFilters ? 'لم يتم العثور على نتائج مطابقة' : 'لا توجد شكاوى حالياً'}
                  />
                ) : (
                  <DataTableShell>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-right">رقم التتبع</TableHead>
                          <TableHead className="text-right">مقدم الشكوى</TableHead>
                          <TableHead className="text-right">النوع</TableHead>
                          <TableHead className="text-right">الحالة</TableHead>
                          <TableHead className="text-right">الأولوية</TableHead>
                          <TableHead className="text-right">المنطقة / الحي</TableHead>
                          <TableHead className="text-right">العنوان التفصيلي</TableHead>
                          <TableHead className="text-right">المشروع</TableHead>
                          <TableHead className="text-right">التاريخ</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {complaints.map((c) => (
                          <TableRow
                            key={c.id}
                            className="cursor-pointer"
                            onClick={() => navigate(`/complaints/${c.id}`)}
                          >
                            <TableCell className="font-mono text-[#0F2A4A] font-medium">{c.tracking_number}</TableCell>
                            <TableCell>{c.full_name}</TableCell>
                            <TableCell>
                              <span className="flex items-center gap-2">
                                <span>{typeLabels[c.complaint_type] || c.complaint_type}</span>
                                {c.complaint_type === 'corruption' && (
                                  <span
                                    className="inline-flex items-center rounded-md border border-[#0F2A4A]/20 bg-[#0F2A4A]/5 px-2 py-0.5 text-[11px] font-medium text-[#0F2A4A]"
                                    title="شكوى فساد - حساسة"
                                  >
                                    حساسة
                                  </span>
                                )}
                              </span>
                            </TableCell>
                            <TableCell>
                              <StatusBadge tone={statusTones[c.status] ?? 'neutral'}>
                                {statusLabels[c.status] || c.status}
                              </StatusBadge>
                            </TableCell>
                            <TableCell>
                              <PriorityBadge
                                priority={c.priority}
                                label={priorityLabels[c.priority] || c.priority}
                              />
                            </TableCell>
                            <TableCell>{areaMap[c.area_id] || '-'}</TableCell>
                            <TableCell className="max-w-[240px] truncate">{c.location_text || '-'}</TableCell>
                            <TableCell>{c.project_id ? (projectMap[c.project_id] || `#${c.project_id}`) : 'غير مرتبط بمشروع'}</TableCell>
                            <TableCell>{c.created_at ? format(new Date(c.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </DataTableShell>
                )}
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {complaints.length === 0 ? (
                  <EmptyState
                    title={hasActiveFilters ? 'لم يتم العثور على نتائج مطابقة' : 'لا توجد شكاوى حالياً'}
                  />
                ) : (
                  complaints.map((c) => (
                    <MobileEntityCard
                      key={c.id}
                      onClick={() => navigate(`/complaints/${c.id}`)}
                      title={
                        <span className="font-mono text-[#1D4ED8]">{c.tracking_number}</span>
                      }
                      badge={
                        <StatusBadge tone={statusTones[c.status] ?? 'neutral'}>
                          {statusLabels[c.status] || c.status}
                        </StatusBadge>
                      }
                      subtitle={c.full_name}
                      meta={(
                        <>
                          <span>{typeLabels[c.complaint_type] || c.complaint_type}</span>
                          {c.complaint_type === 'corruption' && (
                            <>
                              <span aria-hidden>•</span>
                              <span className="inline-flex items-center rounded-md border border-[#0F2A4A]/20 bg-[#0F2A4A]/5 px-2 py-0.5 text-[11px] font-medium text-[#0F2A4A]">
                                حساسة
                              </span>
                            </>
                          )}
                          <span aria-hidden>•</span>
                          <PriorityBadge
                            priority={c.priority}
                            label={priorityLabels[c.priority] || c.priority}
                          />
                          {areaMap[c.area_id] && (
                            <>
                              <span aria-hidden>•</span>
                              <span>{areaMap[c.area_id]}</span>
                            </>
                          )}
                          {c.location_text && (
                            <>
                              <span aria-hidden>•</span>
                              <span className="truncate max-w-[180px]">{c.location_text}</span>
                            </>
                          )}
                          {c.project_id && (
                            <>
                              <span aria-hidden>•</span>
                              <span>{projectMap[c.project_id] || `مشروع #${c.project_id}`}</span>
                            </>
                          )}
                          <span aria-hidden>•</span>
                          <span>{c.created_at ? format(new Date(c.created_at), 'yyyy/MM/dd') : '-'}</span>
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
                entityLabel="شكوى"
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
