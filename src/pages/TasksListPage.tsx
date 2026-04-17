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
import { MagnifyingGlass, Spinner, Warning } from '@phosphor-icons/react';
import { format } from 'date-fns';

const statusLabels: Record<string, string> = {
  pending: 'معلقة', assigned: 'مُعينة', in_progress: 'قيد التنفيذ',
  completed: 'مكتملة', cancelled: 'ملغاة',
};

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800', assigned: 'bg-orange-100 text-orange-800',
  in_progress: 'bg-purple-100 text-purple-800', completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
};

const priorityLabels: Record<string, string> = {
  low: 'منخفضة', medium: 'متوسطة', high: 'عالية', urgent: 'عاجلة',
};

const priorityColors: Record<string, string> = {
  low: 'bg-gray-100 text-gray-800', medium: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800', urgent: 'bg-red-100 text-red-800',
};

const sourceLabels: Record<string, string> = {
  complaint: 'شكوى', internal: 'داخلي', contract: 'عقد',
};

const PAGE_SIZE = 15;

export default function TasksListPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [page, setPage] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: any = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (priorityFilter !== 'all') params.priority = priorityFilter;
    if (search) params.search = search;
    apiService.getTasks(params)
      .then((data) => {
        setTasks(data.items);
        setTotalCount(data.total_count);
      })
      .catch(() => setError('فشل تحميل المهام'))
      .finally(() => setLoading(false));
  }, [statusFilter, search, priorityFilter, page]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">المهام</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
            <div className="relative flex-1 min-w-0 sm:min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث بالعنوان..."
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
              <Select value={priorityFilter} onValueChange={(v) => { setPriorityFilter(v); setPage(0); }}>
                <SelectTrigger className="flex-1 sm:w-[180px]"><SelectValue placeholder="الأولوية" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الأولويات</SelectItem>
                  {Object.entries(priorityLabels).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
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
                      <TableHead className="text-right">العنوان</TableHead>
                      <TableHead className="text-right">المصدر</TableHead>
                      <TableHead className="text-right">الحالة</TableHead>
                      <TableHead className="text-right">الأولوية</TableHead>
                      <TableHead className="text-right">تاريخ الاستحقاق</TableHead>
                      <TableHead className="text-right">التاريخ</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tasks.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          لا توجد مهام
                        </TableCell>
                      </TableRow>
                    ) : (
                      tasks.map((t) => (
                        <TableRow
                          key={t.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/tasks/${t.id}`)}
                        >
                          <TableCell>{t.title}</TableCell>
                          <TableCell>{sourceLabels[t.source_type] || t.source_type || '-'}</TableCell>
                          <TableCell>
                            <Badge className={statusColors[t.status] || 'bg-gray-100 text-gray-800'}>
                              {statusLabels[t.status] || t.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={priorityColors[t.priority] || 'bg-gray-100 text-gray-800'}>
                              {priorityLabels[t.priority] || t.priority}
                            </Badge>
                          </TableCell>
                          <TableCell>{t.due_date ? format(new Date(t.due_date), 'yyyy/MM/dd') : '-'}</TableCell>
                          <TableCell>{t.created_at ? format(new Date(t.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile card view */}
              <div className="responsive-cards-mobile space-y-3">
                {tasks.length === 0 ? (
                  <p className="text-center py-8 text-muted-foreground">لا توجد مهام</p>
                ) : (
                  tasks.map((t) => (
                    <div
                      key={t.id}
                      className="border rounded-lg p-3 cursor-pointer hover:bg-muted/50 active:bg-muted/70 transition-colors"
                      onClick={() => navigate(`/tasks/${t.id}`)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <p className="text-sm font-medium flex-1 ml-2">{t.title}</p>
                        <Badge className={statusColors[t.status] || 'bg-gray-100 text-gray-800'}>
                          {statusLabels[t.status] || t.status}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{sourceLabels[t.source_type] || t.source_type || '-'}</span>
                        <span>•</span>
                        <Badge className={`text-xs ${priorityColors[t.priority] || 'bg-gray-100 text-gray-800'}`}>
                          {priorityLabels[t.priority] || t.priority}
                        </Badge>
                        {t.due_date && (
                          <>
                            <span>•</span>
                            <span>استحقاق: {format(new Date(t.due_date), 'yyyy/MM/dd')}</span>
                          </>
                        )}
                        <span>•</span>
                        <span>{t.created_at ? format(new Date(t.created_at), 'yyyy/MM/dd') : '-'}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>السابق</Button>
                  <span className="text-sm text-muted-foreground">
                    صفحة {page + 1} من {totalPages} ({totalCount} مهمة)
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
