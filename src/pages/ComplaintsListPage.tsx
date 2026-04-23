import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
import { MagnifyingGlass, Spinner, Warning } from '@phosphor-icons/react';
import { format } from 'date-fns';

const statusLabels: Record<string, string> = {
  new: 'جديدة', under_review: 'قيد المراجعة', assigned: 'مُعينة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};

const statusColors: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800', under_review: 'bg-yellow-100 text-yellow-800',
  assigned: 'bg-orange-100 text-orange-800', in_progress: 'bg-purple-100 text-purple-800',
  resolved: 'bg-green-100 text-green-800', rejected: 'bg-red-100 text-red-800',
};

const priorityLabels: Record<string, string> = {
  low: 'منخفضة', medium: 'متوسطة', high: 'عالية', urgent: 'عاجلة',
};

const priorityColors: Record<string, string> = {
  low: 'bg-gray-100 text-gray-800', medium: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800', urgent: 'bg-red-100 text-red-800',
};

const typeLabels: Record<string, string> = {
  infrastructure: 'البنية التحتية', cleaning: 'النظافة', electricity: 'الكهرباء',
  water: 'المياه', roads: 'الطرق', lighting: 'الإنارة', other: 'أخرى',
};

const PAGE_SIZE = 15;

export default function ComplaintsListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProject = searchParams.get('project_id') || 'all';
  const [complaints, setComplaints] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [areas, setAreas] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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

  useEffect(() => {
    apiService.getAreas().then(setAreas).catch(() => {});
    apiService.getProjects({ limit: 200 })
      .then((data) => setProjects(data.items || []))
      .catch(() => setProjects([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (areaFilter !== 'all') params.area_id = Number(areaFilter);
    if (projectFilter !== 'all') params.project_id = Number(projectFilter);
    if (search) params.search = search;
    apiService.getComplaints(params)
      .then((data) => {
        setComplaints(data.items);
        setTotalCount(data.total_count);
      })
      .catch(() => setError('فشل تحميل الشكاوى'))
      .finally(() => setLoading(false));
  }, [statusFilter, areaFilter, projectFilter, search, page]);

  const areaMap = Object.fromEntries(areas.map((a: any) => [a.id, a.name_ar || a.name]));
  const projectMap = Object.fromEntries(projects.map((p: any) => [p.id, p.title]));

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">الشكاوى</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث برقم التتبع أو الاسم..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                className="pr-10"
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الحالات</SelectItem>
                  {Object.entries(statusLabels).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={areaFilter} onValueChange={(v) => { setAreaFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="المنطقة" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع المناطق</SelectItem>
                  {areas.map((a: any) => (
                    <SelectItem key={a.id} value={String(a.id)}>{a.name_ar || a.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={projectFilter} onValueChange={(v) => { setProjectFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="المشروع" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع المشاريع</SelectItem>
                  {projects.map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>{p.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {error && (
            <div className="text-center py-8 text-destructive flex flex-col items-center gap-2">
              <Warning size={32} />
              <p>{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner className="animate-spin" size={32} />
            </div>
          ) : (
            <>
              {/* Desktop table view */}
              <div className="responsive-table-desktop">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">رقم التتبع</TableHead>
                      <TableHead className="text-right">مقدم الشكوى</TableHead>
                      <TableHead className="text-right">النوع</TableHead>
                      <TableHead className="text-right">الحالة</TableHead>
                      <TableHead className="text-right">الأولوية</TableHead>
                      <TableHead className="text-right">المنطقة</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-right">التاريخ</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {complaints.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                          لا توجد شكاوى
                        </TableCell>
                      </TableRow>
                    ) : (
                      complaints.map((c) => (
                        <TableRow
                          key={c.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/complaints/${c.id}`)}
                        >
                          <TableCell className="font-mono">{c.tracking_number}</TableCell>
                          <TableCell>{c.full_name}</TableCell>
                          <TableCell>{typeLabels[c.complaint_type] || c.complaint_type}</TableCell>
                          <TableCell>
                            <Badge className={statusColors[c.status] || 'bg-gray-100 text-gray-800'}>
                              {statusLabels[c.status] || c.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={priorityColors[c.priority] || 'bg-gray-100 text-gray-800'}>
                              {priorityLabels[c.priority] || c.priority}
                            </Badge>
                          </TableCell>
                          <TableCell>{areaMap[c.area_id] || '-'}</TableCell>
                          <TableCell>{c.project_id ? (projectMap[c.project_id] || `#${c.project_id}`) : '-'}</TableCell>
                          <TableCell>{c.created_at ? format(new Date(c.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {complaints.length === 0 ? (
                  <p className="text-center py-8 text-muted-foreground">لا توجد شكاوى</p>
                ) : (
                  complaints.map((c) => (
                    <div
                      key={c.id}
                      className="border rounded-lg p-3 cursor-pointer hover:bg-muted/50 active:bg-muted/70 transition-colors"
                      onClick={() => navigate(`/complaints/${c.id}`)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-sm font-bold text-primary">{c.tracking_number}</span>
                        <Badge className={statusColors[c.status] || 'bg-gray-100 text-gray-800'}>
                          {statusLabels[c.status] || c.status}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium mb-1">{c.full_name}</p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{typeLabels[c.complaint_type] || c.complaint_type}</span>
                        <span>•</span>
                        <Badge className={`text-xs ${priorityColors[c.priority] || 'bg-gray-100 text-gray-800'}`}>
                          {priorityLabels[c.priority] || c.priority}
                        </Badge>
                        {areaMap[c.area_id] && (
                          <>
                            <span>•</span>
                            <span>{areaMap[c.area_id]}</span>
                          </>
                        )}
                        {c.project_id && (
                          <>
                            <span>•</span>
                            <span>{projectMap[c.project_id] || `مشروع #${c.project_id}`}</span>
                          </>
                        )}
                        <span>•</span>
                        <span>{c.created_at ? format(new Date(c.created_at), 'yyyy/MM/dd') : '-'}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>السابق</Button>
                  <span className="text-sm text-muted-foreground">
                    صفحة {page + 1} من {totalPages} ({totalCount} شكوى)
                  </span>
                  <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>التالي</Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
