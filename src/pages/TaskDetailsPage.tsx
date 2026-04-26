import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { FileUpload } from '@/components/FileUpload';
import { useAuth } from '@/hooks/useAuth';
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
import { Spinner, ClockCounterClockwise, Camera, Warning, MapPin, LinkSimple } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

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

// Field-team / contractor users may only flip status to one of these values
// when reporting progress on a task assigned to them.
const FIELD_TEAM_STATUS_OPTIONS: Array<[string, string]> = [
  ['in_progress', statusLabels['in_progress']],
  ['completed', statusLabels['completed']],
];

export default function TaskDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const { canManageTasks, user, role } = useAuth();
  const [task, setTask] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [areas, setAreas] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [sourceComplaint, setSourceComplaint] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newStatus, setNewStatus] = useState('');
  const [assignee, setAssignee] = useState('');
  const [teamId, setTeamId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [notes, setNotes] = useState('');
  const [updating, setUpdating] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [afterRepairFiles, setAfterRepairFiles] = useState<File[]>([]);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    setError('');
    const numId = Number(id);
    Promise.all([
      apiService.getTask(numId),
      apiService.getTaskActivities(numId).catch(() => []),
      apiService.getAreas().catch(() => []),
      apiService.getUsers({ limit: 100 }).catch(() => ({ items: [] })),
      apiService.getActiveTeams().catch(() => []),
      apiService.getProjects({ status: 'active', limit: 200 }).catch(() => ({ items: [] })),
    ])
      .then(([taskData, activitiesData, areasData, usersData, teamsData, projectsData]) => {
        setTask(taskData);
        setActivities(Array.isArray(activitiesData) ? activitiesData : []);
        setAreas(areasData);
        setUsers(usersData.items || []);
        setTeams(Array.isArray(teamsData) ? teamsData : []);
        setProjects((projectsData as any).items || []);
        // Pre-fill selectors from current task values so the user sees current
        // assignment without needing to re-pick.
        setTeamId(taskData?.team_id ? String(taskData.team_id) : '');
        setProjectId(taskData?.project_id ? String(taskData.project_id) : '');
        // Fetch the linked complaint (if any) so we can render its tracking
        // number instead of a bare numeric id — gives operators a citizen-
        // facing identifier on the task page.
        if (taskData?.complaint_id) {
          apiService.getComplaint(taskData.complaint_id)
            .then((c) => setSourceComplaint(c))
            .catch(() => setSourceComplaint(null));
        } else {
          setSourceComplaint(null);
        }
      })
      .catch(() => setError('فشل تحميل بيانات المهمة'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleUpdate = async () => {
    if (!id) return;
    setUpdating(true);
    try {
      const updateData: any = {};
      if (newStatus) updateData.status = newStatus;
      if (notes) updateData.notes = notes;
      if (assignee) updateData.assigned_to_id = Number(assignee);
      // Team and project: send only when value differs from the persisted task
      // so an unchanged form does not blank existing values.
      if (teamId !== (task?.team_id ? String(task.team_id) : '')) {
        updateData.team_id = teamId ? Number(teamId) : null;
      }
      if (projectId !== (task?.project_id ? String(task.project_id) : '')) {
        updateData.project_id = projectId ? Number(projectId) : null;
      }
      const result = await apiService.updateTask(Number(id), updateData, { afterRepairPhotos: afterRepairFiles });
      if (result?.queued) {
        toast.success('تم حفظ الطلب محليًا وسيتم إرساله عند عودة الاتصال');
      } else {
        toast.success('تم تحديث المهمة بنجاح');
      }
      setNewStatus('');
      setNotes('');
      setAssignee('');
      setAfterRepairFiles([]);
      setConfirmCancel(false);
      if (!result?.queued) fetchData();
    } catch {
      toast.error('فشل تحديث المهمة');
    } finally {
      setUpdating(false);
    }
  };

  const handleBeforePhotos = async (photos: string[]) => {
    if (!id) return;
    try {
      await apiService.updateTask(Number(id), { before_photos: photos });
      toast.success('تم تحديث صور قبل');
      fetchData();
    } catch {
      toast.error('فشل تحديث الصور');
    }
  };

  const handleAfterPhotos = async (photos: string[]) => {
    if (!id) return;
    try {
      await apiService.updateTask(Number(id), { after_photos: photos });
      toast.success('تم تحديث صور بعد');
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

  if (error || !task) {
    return (
      <Layout>
        <div className="text-center py-12">
          <Warning size={48} className="mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">{error || 'لم يتم العثور على المهمة'}</p>
          <Link to="/tasks" className="text-primary hover:underline mt-2 inline-block">العودة للقائمة</Link>
        </div>
      </Layout>
    );
  }

  const areaObj = areas.find((a: any) => a.id === task.area_id);
  const assignedUser = users.find((u: any) => u.id === task.assigned_to_id);

  // Field-team / contractor users get a restricted update card on tasks
  // assigned to them: status (in_progress/completed only), notes, and the
  // before/after photo uploads. They cannot reassign or re-scope the task.
  const isFieldRole = role === 'field_team' || role === 'contractor_user';
  const isAssignedToMe = !!user && task.assigned_to_id === user.id;
  const showFullUpdateCard = canManageTasks;
  const showFieldUpdateCard = !canManageTasks && isFieldRole && isAssignedToMe;
  const canUploadPhotos = canManageTasks || (isFieldRole && isAssignedToMe);

  const detail = (label: string, value: React.ReactNode) => (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '-'}</span>
    </div>
  );

  return (
    <Layout>
      <div className="space-y-6">
        {/* Task Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-3 flex-wrap">
              تفاصيل المهمة
              <Badge className={statusColors[task.status] || 'bg-gray-100 text-gray-800'}>
                {statusLabels[task.status] || task.status}
              </Badge>
              <Badge className={priorityColors[task.priority] || 'bg-gray-100 text-gray-800'}>
                {priorityLabels[task.priority] || task.priority}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {detail('العنوان', task.title)}
              {detail('المصدر', (
                <Badge variant="outline">{sourceLabels[task.source_type] || task.source_type || '-'}</Badge>
              ))}
              {detail('الأولوية', (
                <Badge className={priorityColors[task.priority] || 'bg-gray-100 text-gray-800'}>
                  {priorityLabels[task.priority] || task.priority}
                </Badge>
              ))}
              {detail('المنطقة', areaObj ? (
                <span className="flex items-center gap-1"><MapPin size={14} /> {areaObj.name_ar || areaObj.name}</span>
              ) : '-')}
              {detail('الموقع', task.location_text)}
              {detail('المسؤول المعين', assignedUser ? assignedUser.full_name : '-')}
              {detail('الفريق التنفيذي', task.team_id ? (
                <Link to={`/teams/${task.team_id}`} className="text-primary hover:underline">
                  {teams.find((t: any) => t.id === task.team_id)?.name || `#${task.team_id}`}
                </Link>
              ) : '-')}
              {detail('المشروع', task.project_id ? (
                <Link to={`/projects/${task.project_id}`} className="text-primary hover:underline">
                  {projects.find((p: any) => p.id === task.project_id)?.title || `#${task.project_id}`}
                </Link>
              ) : '-')}
              {detail('تاريخ الاستحقاق', task.due_date ? format(new Date(task.due_date), 'yyyy/MM/dd') : '-')}
              {detail('تاريخ الإنجاز', task.completed_at ? format(new Date(task.completed_at), 'yyyy/MM/dd HH:mm') : '-')}
              {detail('تاريخ الإنشاء', task.created_at ? format(new Date(task.created_at), 'yyyy/MM/dd HH:mm') : '-')}
              {detail('تاريخ التحديث', task.updated_at ? format(new Date(task.updated_at), 'yyyy/MM/dd HH:mm') : '-')}
            </div>

            {/* Linked complaint/contract */}
            {(task.complaint_id || task.contract_id) && (
              <>
                <Separator className="my-4" />
                <div className="flex flex-wrap gap-4">
                  {task.complaint_id && (
                    <div className="flex items-center gap-2">
                      <LinkSimple size={16} />
                      <span className="text-sm text-muted-foreground">مصدر هذه المهمة — شكوى:</span>
                      <Link to={`/complaints/${task.complaint_id}`} className="text-primary hover:underline text-sm font-mono">
                        {sourceComplaint?.tracking_number || `#${task.complaint_id}`}
                      </Link>
                      {sourceComplaint?.full_name && (
                        <span className="text-xs text-muted-foreground">— {sourceComplaint.full_name}</span>
                      )}
                    </div>
                  )}
                  {task.contract_id && (
                    <div className="flex items-center gap-2">
                      <LinkSimple size={16} />
                      <span className="text-sm text-muted-foreground">عقد مرتبط:</span>
                      <Link to={`/contracts/${task.contract_id}`} className="text-primary hover:underline text-sm">
                        #{task.contract_id}
                      </Link>
                    </div>
                  )}
                </div>
              </>
            )}

            {task.description && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">الوصف</span>
                  <p className="mt-1 whitespace-pre-wrap">{task.description}</p>
                </div>
              </>
            )}
            {task.notes && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">ملاحظات</span>
                  <p className="mt-1 whitespace-pre-wrap">{task.notes}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Before/After Photos */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Camera size={20} />
                صور قبل التنفيذ
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FileUpload
                category="tasks"
                accept="images"
                existingFiles={task.before_photos || []}
                onUploadComplete={canUploadPhotos ? handleBeforePhotos : undefined}
                disabled={!canUploadPhotos}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Camera size={20} />
                صور بعد التنفيذ
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FileUpload
                category="tasks"
                accept="images"
                existingFiles={task.after_photos || []}
                onUploadComplete={canUploadPhotos ? handleAfterPhotos : undefined}
                disabled={!canUploadPhotos}
              />
            </CardContent>
          </Card>
        </div>

        {/* Restricted update card for field team / contractor on assigned tasks */}
        {showFieldUpdateCard && (
        <Card>
          <CardHeader>
            <CardTitle>تحديث حالة المهمة</CardTitle>
            <p className="text-xs text-muted-foreground">
              يمكنك تحديث حالة المهمة إلى "قيد التنفيذ" أو "مكتملة" وإضافة ملاحظات الإصلاح ورفع صور بعد التنفيذ.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">الحالة الجديدة</label>
                <Select value={newStatus} onValueChange={setNewStatus}>
                  <SelectTrigger><SelectValue placeholder="اختر الحالة" /></SelectTrigger>
                  <SelectContent>
                    {FIELD_TEAM_STATUS_OPTIONS.map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Textarea
              placeholder="ملاحظات الإصلاح..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div className="space-y-2">
              <label className="text-sm font-medium">صور بعد الإصلاح (اختياري)</label>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.gif"
                multiple
                onChange={(e) => setAfterRepairFiles(Array.from(e.target.files || []))}
              />
              {afterRepairFiles.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  سيتم مزامنة {afterRepairFiles.length} صورة تلقائياً عند توفر الاتصال.
                </p>
              )}
            </div>
            <Button
              onClick={handleUpdate}
              disabled={(!newStatus && !notes && afterRepairFiles.length === 0) || updating}
            >
              {updating ? <Spinner className="animate-spin ml-2" size={16} /> : null}
              حفظ التحديث
            </Button>
          </CardContent>
        </Card>
        )}

        {/* Update Status – only for authorized roles */}
        {showFullUpdateCard && (
        <Card>
          <CardHeader>
            <CardTitle>تحديث المهمة</CardTitle>
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
              <div className="space-y-2">
                <label className="text-sm font-medium">الفريق التنفيذي</label>
                <Select value={teamId || '__none__'} onValueChange={(v) => setTeamId(v === '__none__' ? '' : v)}>
                  <SelectTrigger><SelectValue placeholder="بدون فريق" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">— بدون فريق —</SelectItem>
                    {teams.map((t: any) => (
                      <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">المشروع</label>
                <Select value={projectId || '__none__'} onValueChange={(v) => setProjectId(v === '__none__' ? '' : v)}>
                  <SelectTrigger><SelectValue placeholder="بدون مشروع" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">— بدون مشروع —</SelectItem>
                    {projects.map((p: any) => (
                      <SelectItem key={p.id} value={String(p.id)}>{p.title}</SelectItem>
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
            <div className="space-y-2">
              <label className="text-sm font-medium">صور بعد الإصلاح (اختياري)</label>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.gif"
                multiple
                onChange={(e) => setAfterRepairFiles(Array.from(e.target.files || []))}
              />
              {afterRepairFiles.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  سيتم رفع الصور الآن أو حفظها محلياً إذا كان الاتصال ضعيفاً.
                </p>
              )}
            </div>
            <Button
              onClick={() => {
                if (newStatus === 'cancelled') {
                  setConfirmCancel(true);
                } else {
                  handleUpdate();
                }
              }}
              disabled={
                !newStatus && !notes && !assignee && afterRepairFiles.length === 0 &&
                teamId === (task?.team_id ? String(task.team_id) : '') &&
                projectId === (task?.project_id ? String(task.project_id) : '') ||
                updating
              }
            >
              {updating ? <Spinner className="animate-spin ml-2" size={16} /> : null}
              تحديث المهمة
            </Button>
          </CardContent>
        </Card>
        )}

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

      {/* Cancel Confirmation */}
      <AlertDialog open={confirmCancel} onOpenChange={setConfirmCancel}>
        <AlertDialogContent dir="rtl">
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد الإلغاء</AlertDialogTitle>
            <AlertDialogDescription>
              هل أنت متأكد من إلغاء هذه المهمة؟ لا يمكن التراجع عن هذا الإجراء.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>تراجع</AlertDialogCancel>
            <AlertDialogAction onClick={handleUpdate} className="bg-destructive text-destructive-foreground">
              تأكيد الإلغاء
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
