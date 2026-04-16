import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Spinner, ClockCounterClockwise, MapPin, Image, Warning } from '@phosphor-icons/react';
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
  const [areas, setAreas] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newStatus, setNewStatus] = useState('');
  const [assignee, setAssignee] = useState('');
  const [notes, setNotes] = useState('');
  const [updating, setUpdating] = useState(false);
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    setError('');
    const numId = Number(id);
    Promise.all([
      apiService.getComplaint(numId),
      apiService.getComplaintActivities(numId).catch(() => []),
      apiService.getAreas().catch(() => []),
      apiService.getUsers({ limit: 100 }).catch(() => ({ items: [] })),
    ])
      .then(([complaintData, activitiesData, areasData, usersData]) => {
        setComplaint(complaintData);
        setActivities(Array.isArray(activitiesData) ? activitiesData : []);
        setAreas(areasData);
        setUsers(usersData.items || []);
      })
      .catch(() => setError('فشل تحميل بيانات الشكوى'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleStatusUpdate = async () => {
    if (!id) return;
    setUpdating(true);
    try {
      const updateData: any = {};
      if (newStatus) updateData.status = newStatus;
      if (notes) updateData.notes = notes;
      if (assignee) updateData.assigned_to_id = Number(assignee);
      await apiService.updateComplaint(Number(id), updateData);
      toast.success('تم تحديث الشكوى بنجاح');
      setNewStatus('');
      setNotes('');
      setAssignee('');
      setConfirmAction(null);
      fetchData();
    } catch {
      toast.error('فشل تحديث الشكوى');
    } finally {
      setUpdating(false);
    }
  };

  const handleImagesUpdate = async (images: string[]) => {
    if (!id) return;
    try {
      await apiService.updateComplaint(Number(id), { images: images });
      toast.success('تم تحديث الصور');
      fetchData();
    } catch {
      toast.error('فشل تحديث الصور');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12"><Spinner className="animate-spin" size={32} /></div>
      </Layout>
    );
  }

  if (error || !complaint) {
    return (
      <Layout>
        <div className="text-center py-12">
          <Warning size={48} className="mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">{error || 'لم يتم العثور على الشكوى'}</p>
          <Link to="/complaints" className="text-primary hover:underline mt-2 inline-block">العودة للقائمة</Link>
        </div>
      </Layout>
    );
  }

  const areaObj = areas.find((a: any) => a.id === complaint.area_id);
  const assignedUser = users.find((u: any) => u.id === complaint.assigned_to_id);
  const destructiveStatuses = ['rejected'];

  const detail = (label: string, value: React.ReactNode) => (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '-'}</span>
    </div>
  );

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-3 flex-wrap">
              تفاصيل الشكوى
              <Badge className={statusColors[complaint.status] || 'bg-gray-100 text-gray-800'}>
                {statusLabels[complaint.status] || complaint.status}
              </Badge>
              <Badge className={priorityColors[complaint.priority] || 'bg-gray-100 text-gray-800'}>
                {priorityLabels[complaint.priority] || complaint.priority}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {detail('رقم التتبع', <span className="font-mono text-lg">{complaint.tracking_number}</span>)}
              {detail('مقدم الشكوى', complaint.full_name)}
              {detail('رقم الهاتف', complaint.phone)}
              {detail('النوع', (
                <Badge variant="outline">{typeLabels[complaint.complaint_type] || complaint.complaint_type}</Badge>
              ))}
              {detail('الأولوية', (
                <Badge className={priorityColors[complaint.priority] || 'bg-gray-100 text-gray-800'}>
                  {priorityLabels[complaint.priority] || complaint.priority}
                </Badge>
              ))}
              {detail('المنطقة', areaObj ? (
                <span className="flex items-center gap-1"><MapPin size={14} /> {areaObj.name_ar || areaObj.name}</span>
              ) : '-')}
              {detail('الموقع', complaint.location_text)}
              {complaint.latitude && complaint.longitude && detail('الإحداثيات', `${complaint.latitude}, ${complaint.longitude}`)}
              {detail('المسؤول المعين', assignedUser ? assignedUser.full_name : '-')}
              {detail('تاريخ الإنشاء', complaint.created_at ? format(new Date(complaint.created_at), 'yyyy/MM/dd HH:mm') : '-')}
              {detail('تاريخ التحديث', complaint.updated_at ? format(new Date(complaint.updated_at), 'yyyy/MM/dd HH:mm') : '-')}
              {complaint.resolved_at && detail('تاريخ الحل', format(new Date(complaint.resolved_at), 'yyyy/MM/dd HH:mm'))}
            </div>
            {complaint.description && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">الوصف</span>
                  <p className="mt-1 whitespace-pre-wrap">{complaint.description}</p>
                </div>
              </>
            )}
            {complaint.notes && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">ملاحظات</span>
                  <p className="mt-1 whitespace-pre-wrap">{complaint.notes}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Images / Attachments */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Image size={20} />
              الصور والمرفقات
            </CardTitle>
          </CardHeader>
          <CardContent>
            <FileUpload
              category="complaints"
              accept="images"
              existingFiles={complaint.images || []}
              onUploadComplete={handleImagesUpdate}
              label="صور الشكوى"
            />
          </CardContent>
        </Card>

        {/* Status Update */}
        <Card>
          <CardHeader>
            <CardTitle>تحديث الشكوى</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">الحالة الجديدة</label>
                <Select value={newStatus} onValueChange={setNewStatus}>
                  <SelectTrigger><SelectValue placeholder="اختر الحالة" /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(statusLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">تعيين إلى</label>
                <Select value={assignee} onValueChange={setAssignee}>
                  <SelectTrigger><SelectValue placeholder="اختر المسؤول" /></SelectTrigger>
                  <SelectContent>
                    {users.filter((u: any) => u.is_active).map((u: any) => (
                      <SelectItem key={u.id} value={String(u.id)}>{u.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Textarea
              placeholder="ملاحظات..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <Button
              onClick={() => {
                if (newStatus && destructiveStatuses.includes(newStatus)) {
                  setConfirmAction('update');
                } else {
                  handleStatusUpdate();
                }
              }}
              disabled={(!newStatus && !notes && !assignee) || updating}
            >
              {updating ? <Spinner className="animate-spin ml-2" size={16} /> : null}
              تحديث الشكوى
            </Button>
          </CardContent>
        </Card>

        {/* Activity History */}
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
                      {act.description && act.action && <p className="text-sm text-muted-foreground mt-1">{act.description}</p>}
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

      {/* Confirmation Dialog for destructive actions */}
      <AlertDialog open={!!confirmAction} onOpenChange={(open) => { if (!open) setConfirmAction(null); }}>
        <AlertDialogContent dir="rtl">
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد الإجراء</AlertDialogTitle>
            <AlertDialogDescription>
              هل أنت متأكد من تغيير حالة الشكوى إلى "{statusLabels[newStatus] || newStatus}"؟
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction onClick={handleStatusUpdate}>تأكيد</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
