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
import { format } from 'date-fns';
import { useAuth } from '@/hooks/useAuth';

const statusLabels: Record<string, string> = {
  planned: 'مخطط', active: 'نشط', on_hold: 'متوقف مؤقتاً',
  completed: 'مكتمل', cancelled: 'ملغى',
};

const statusColors: Record<string, string> = {
  planned: 'bg-blue-100 text-blue-800', active: 'bg-green-100 text-green-800',
  on_hold: 'bg-yellow-100 text-yellow-800', completed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-red-100 text-red-800',
};

const PAGE_SIZE = 15;

export default function ProjectsListPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const [projects, setProjects] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);

  const canCreate = role && ['project_director', 'contracts_manager', 'engineer_supervisor'].includes(role);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (search) params.search = search;
    apiService.getProjects(params)
      .then((data) => {
        setProjects(data.items);
        setTotalCount(data.total_count);
      })
      .catch(() => setError('فشل تحميل المشاريع'))
      .finally(() => setLoading(false));
  }, [statusFilter, search, page]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Layout>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="text-2xl">المشاريع</CardTitle>
            {canCreate && (
              <Button onClick={() => navigate('/projects/new')}>
                <Plus size={20} className="ml-1" />
                إضافة مشروع
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث بالعنوان أو الكود..."
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

          {!loading && !error && projects.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg mb-2">لا توجد مشاريع بعد</p>
              {canCreate && (
                <Button onClick={() => navigate('/projects/new')} className="mt-4">
                  إضافة أول مشروع
                </Button>
              )}
            </div>
          )}

          {!loading && !error && projects.length > 0 && (
            <>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>الكود</TableHead>
                      <TableHead>العنوان</TableHead>
                      <TableHead>الحالة</TableHead>
                      <TableHead>تاريخ البدء</TableHead>
                      <TableHead>المهام</TableHead>
                      <TableHead>الشكاوى</TableHead>
                      <TableHead>الفرق</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {projects.map((proj) => (
                      <TableRow key={proj.id} onClick={() => navigate(`/projects/${proj.id}`)} className="cursor-pointer hover:bg-muted/50">
                        <TableCell className="font-mono">{proj.code}</TableCell>
                        <TableCell className="font-semibold">{proj.title}</TableCell>
                        <TableCell>
                          <Badge className={statusColors[proj.status] || 'bg-gray-100'}>
                            {statusLabels[proj.status] || proj.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{proj.start_date ? format(new Date(proj.start_date), 'yyyy-MM-dd') : '-'}</TableCell>
                        <TableCell>{proj.task_count || 0}</TableCell>
                        <TableCell>{proj.complaint_count || 0}</TableCell>
                        <TableCell>{proj.team_count || 0}</TableCell>
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
