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
import { describeLoadError } from '@/lib/loadError';

const statusLabels: Record<string, string> = {
  draft: 'مسودة', under_review: 'قيد المراجعة', approved: 'مُعتمد',
  active: 'نشط', suspended: 'معلق', completed: 'مكتمل',
  expired: 'منتهي', cancelled: 'ملغى',
};

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800', under_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800', active: 'bg-green-100 text-green-800',
  suspended: 'bg-orange-100 text-orange-800', completed: 'bg-emerald-100 text-emerald-800',
  expired: 'bg-red-100 text-red-800', cancelled: 'bg-red-100 text-red-800',
};

const typeLabels: Record<string, string> = {
  construction: 'إنشاء', maintenance: 'صيانة', supply: 'توريد',
  consulting: 'استشارات', other: 'أخرى',
};

function formatValue(value: number | string | null | undefined): string {
  if (value == null) return '-';
  return Number(value).toLocaleString('en-US');
}

const PAGE_SIZE = 15;

export default function ContractsListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProject = searchParams.get('project_id') || 'all';
  const [contracts, setContracts] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState(initialProject);
  const [page, setPage] = useState(0);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (projectFilter === 'all') next.delete('project_id');
    else next.set('project_id', projectFilter);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectFilter]);

  useEffect(() => {
    apiService.getProjects({ limit: 200 })
      .then((data) => setProjects(data.items || []))
      .catch((err) => {
        if (import.meta.env?.DEV) console.warn('[load:projects-selector]', err);
        setProjects([]);
      });
  }, []);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (typeFilter !== 'all') params.contract_type = typeFilter;
    if (projectFilter !== 'all') params.project_id = Number(projectFilter);
    if (search) params.search = search;
    apiService.getContracts(params)
      .then((data) => {
        setContracts(data.items);
        setTotalCount(data.total_count);
      })
      .catch((err) => setError(describeLoadError(err, 'العقود').message))
      .finally(() => setLoading(false));
  }, [statusFilter, typeFilter, projectFilter, search, page]);

  const projectMap = Object.fromEntries(projects.map((p: any) => [p.id, p.title]));

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">العقود</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث برقم العقد أو العنوان أو المقاول..."
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
              <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="النوع" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الأنواع</SelectItem>
                  {Object.entries(typeLabels).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
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
                      <TableHead className="text-right">رقم العقد</TableHead>
                      <TableHead className="text-right">العنوان</TableHead>
                      <TableHead className="text-right">المقاول</TableHead>
                      <TableHead className="text-right">النوع</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-right">القيمة</TableHead>
                      <TableHead className="text-right">الحالة</TableHead>
                      <TableHead className="text-right">تاريخ الانتهاء</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {contracts.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                          لا توجد عقود
                        </TableCell>
                      </TableRow>
                    ) : (
                      contracts.map((c) => (
                        <TableRow
                          key={c.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/contracts/${c.id}`)}
                        >
                          <TableCell className="font-mono">{c.contract_number}</TableCell>
                          <TableCell>{c.title}</TableCell>
                          <TableCell>{c.contractor_name}</TableCell>
                          <TableCell>{typeLabels[c.contract_type] || c.contract_type || '-'}</TableCell>
                          <TableCell>{c.project_id ? (projectMap[c.project_id] || `#${c.project_id}`) : '-'}</TableCell>
                          <TableCell>{formatValue(c.contract_value)}</TableCell>
                          <TableCell>
                            <Badge className={statusColors[c.status] || 'bg-gray-100 text-gray-800'}>
                              {statusLabels[c.status] || c.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{c.end_date ? format(new Date(c.end_date), 'yyyy/MM/dd') : '-'}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {contracts.length === 0 ? (
                  <p className="text-center py-8 text-muted-foreground">لا توجد عقود</p>
                ) : (
                  contracts.map((c) => (
                    <div
                      key={c.id}
                      className="border rounded-lg p-3 cursor-pointer hover:bg-muted/50 active:bg-muted/70 transition-colors"
                      onClick={() => navigate(`/contracts/${c.id}`)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-sm font-bold text-primary">{c.contract_number}</span>
                        <Badge className={statusColors[c.status] || 'bg-gray-100 text-gray-800'}>
                          {statusLabels[c.status] || c.status}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium mb-1">{c.title}</p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{c.contractor_name}</span>
                        <span>•</span>
                        <span>{typeLabels[c.contract_type] || c.contract_type || '-'}</span>
                        <span>•</span>
                        <span>{formatValue(c.contract_value)}</span>
                        {c.project_id && (
                          <>
                            <span>•</span>
                            <span>{projectMap[c.project_id] || `مشروع #${c.project_id}`}</span>
                          </>
                        )}
                        {c.end_date && (
                          <>
                            <span>•</span>
                            <span>ينتهي: {format(new Date(c.end_date), 'yyyy/MM/dd')}</span>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>السابق</Button>
                  <span className="text-sm text-muted-foreground">
                    صفحة {page + 1} من {totalPages} ({totalCount} عقد)
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
