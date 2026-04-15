import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MagnifyingGlass, Spinner } from '@phosphor-icons/react';
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

export default function TasksListPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');

  useEffect(() => {
    apiService.getTasks()
      .then(setTasks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = tasks.filter((t) => {
    const matchesSearch = !search ||
      t.title?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
    const matchesPriority = priorityFilter === 'all' || t.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">المهام</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث بالعنوان..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pr-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع الحالات</SelectItem>
                {Object.entries(statusLabels).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="الأولوية" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع الأولويات</SelectItem>
                {Object.entries(priorityLabels).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner className="animate-spin" size={32} />
            </div>
          ) : (
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
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      لا توجد مهام
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((t) => (
                    <TableRow
                      key={t.id}
                      className="cursor-pointer"
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
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
