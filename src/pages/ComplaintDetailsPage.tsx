import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Spinner, ClockCounterClockwise, Image as ImageIcon, UploadSimple } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

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

export default function ComplaintDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [complaint, setComplaint] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newStatus, setNewStatus] = useState('');
  const [notes, setNotes] = useState('');
  const [updating, setUpdating] = useState(false);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    const numId = Number(id);
    Promise.all([
      apiService.getComplaint(numId),
      apiService.getComplaintActivities(numId).catch(() => []),
    ])
      .then(([complaintData, activitiesData]) => {
        setComplaint(complaintData);
        setActivities(Array.isArray(activitiesData) ? activitiesData : []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleStatusUpdate = async () => {
    if (!newStatus || !id) return;
    setUpdating(true);
    try {
      await apiService.updateComplaint(Number(id), { status: newStatus, notes });
      toast.success('تم تحديث الحالة بنجاح');
      setNewStatus('');
      setNotes('');
      fetchData();
    } catch {
      toast.error('فشل تحديث الحالة');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  if (!complaint) {
    return (
      <Layout>
        <div className="text-center py-12 text-muted-foreground">لم يتم العثور على الشكوى</div>
      </Layout>
    );
  }

  const detail = (label: string, value: React.ReactNode) => (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '-'}</span>
    </div>
  );

  return (
    <Layout>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-3">
              تفاصيل الشكوى
              <Badge className={statusColors[complaint.status] || 'bg-gray-100 text-gray-800'}>
                {statusLabels[complaint.status] || complaint.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {detail('رقم التتبع', <span className="font-mono">{complaint.tracking_number}</span>)}
              {detail('مقدم الشكوى', complaint.full_name)}
              {detail('رقم الهاتف', complaint.phone)}
              {detail('النوع', typeLabels[complaint.complaint_type] || complaint.complaint_type)}
              {detail('الأولوية', (
                <Badge className={priorityColors[complaint.priority] || 'bg-gray-100 text-gray-800'}>
                  {priorityLabels[complaint.priority] || complaint.priority}
                </Badge>
              ))}
              {detail('الموقع', complaint.location_text)}
              {detail('تاريخ الإنشاء', complaint.created_at ? format(new Date(complaint.created_at), 'yyyy/MM/dd HH:mm') : '-')}
              {detail('تاريخ التحديث', complaint.updated_at ? format(new Date(complaint.updated_at), 'yyyy/MM/dd HH:mm') : '-')}
            </div>
            {complaint.description && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">الوصف</span>
                  <p className="mt-1">{complaint.description}</p>
                </div>
              </>
            )}
            {complaint.images && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground flex items-center gap-1 mb-2">
                    <ImageIcon size={16} />
                    الصور المرفقة
                  </span>
                  <div className="flex flex-wrap gap-3">
                    {complaint.images.split(',').filter(Boolean).map((path: string, idx: number) => (
                      <a
                        key={idx}
                        href={`http://localhost:8000${path.trim()}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block border rounded-lg overflow-hidden hover:ring-2 ring-primary transition-all"
                      >
                        {path.trim().match(/\.(jpg|jpeg|png|gif)$/i) ? (
                          <img
                            src={`http://localhost:8000${path.trim()}`}
                            alt={`مرفق ${idx + 1}`}
                            className="w-32 h-32 object-cover"
                          />
                        ) : (
                          <div className="w-32 h-32 flex items-center justify-center bg-muted text-sm text-muted-foreground">
                            ملف {idx + 1}
                          </div>
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>تحديث الحالة</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select value={newStatus} onValueChange={setNewStatus}>
              <SelectTrigger className="w-full md:w-[250px]">
                <SelectValue placeholder="اختر الحالة الجديدة" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(statusLabels).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Textarea
              placeholder="ملاحظات..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <Button onClick={handleStatusUpdate} disabled={!newStatus || updating}>
              {updating ? <Spinner className="animate-spin ml-2" size={16} /> : null}
              تحديث الحالة
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClockCounterClockwise size={20} />
              سجل النشاطات
            </CardTitle>
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">لا توجد نشاطات</p>
            ) : (
              <div className="space-y-4">
                {activities.map((act: any, idx: number) => (
                  <div key={act.id || idx} className="flex gap-4 border-r-2 border-primary pr-4 pb-4">
                    <div className="flex-1">
                      <p className="font-medium">{act.action || act.description || '-'}</p>
                      {act.notes && <p className="text-sm text-muted-foreground mt-1">{act.notes}</p>}
                      <p className="text-xs text-muted-foreground mt-1">
                        {act.created_at ? format(new Date(act.created_at), 'yyyy/MM/dd HH:mm') : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
