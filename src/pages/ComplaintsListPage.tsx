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

export default function ComplaintsListPage() {
  const navigate = useNavigate();
  const [complaints, setComplaints] = useState<any[]>([]);
  const [areas, setAreas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [areaFilter, setAreaFilter] = useState('all');

  useEffect(() => {
    Promise.all([apiService.getComplaints(), apiService.getAreas()])
      .then(([complaintsData, areasData]) => {
        setComplaints(complaintsData);
        setAreas(areasData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const areaMap = Object.fromEntries(areas.map((a: any) => [a.id, a.name]));

  const filtered = complaints.filter((c) => {
    const matchesSearch = !search ||
      c.tracking_number?.toLowerCase().includes(search.toLowerCase()) ||
      c.full_name?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    const matchesArea = areaFilter === 'all' || String(c.area_id) === areaFilter;
    return matchesSearch && matchesStatus && matchesArea;
  });

  return (
    <Layout>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">الشكاوى</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <MagnifyingGlass className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="بحث برقم التتبع أو الاسم..."
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
            <Select value={areaFilter} onValueChange={setAreaFilter}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="المنطقة" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع المناطق</SelectItem>
                {areas.map((a: any) => (
                  <SelectItem key={a.id} value={String(a.id)}>{a.name}</SelectItem>
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
                  <TableHead className="text-right">رقم التتبع</TableHead>
                  <TableHead className="text-right">مقدم الشكوى</TableHead>
                  <TableHead className="text-right">النوع</TableHead>
                  <TableHead className="text-right">الحالة</TableHead>
                  <TableHead className="text-right">الأولوية</TableHead>
                  <TableHead className="text-right">المنطقة</TableHead>
                  <TableHead className="text-right">التاريخ</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      لا توجد شكاوى
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((c) => (
                    <TableRow
                      key={c.id}
                      className="cursor-pointer"
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
                      <TableCell>{c.created_at ? format(new Date(c.created_at), 'yyyy/MM/dd') : '-'}</TableCell>
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
