import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService, ApiError } from '@/services/api';
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
import { Spinner, ClockCounterClockwise, MapPin, Image, Warning, ListChecks, Robot } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ContextMessagesPanel } from '@/components/messages/ContextMessagesPanel';
import { SmartAssistantDrawer } from '@/components/SmartAssistantDrawer';

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
  water: 'المياه', roads: 'الطرق', lighting: 'الإنارة',
  heating_network: 'صيانة شبكة التدفئة', corruption: 'شكوى فساد', other: 'أخرى',
};

const responsibleAuthorityOptions = [
  { value: 'project_director', label: 'مدير المشروع', userRoles: ['project_director', 'contracts_manager'], allowsTeam: false },
  { value: 'engineer_supervisor', label: 'مشرف هندسي', userRoles: ['engineer_supervisor'], allowsTeam: false },
  { value: 'area_supervisor', label: 'مشرف المنطقة', userRoles: ['area_supervisor'], allowsTeam: false },
  { value: 'field_team', label: 'فريق ميداني', userRoles: ['field_team'], allowsTeam: true },
  { value: 'contractor_user', label: 'مستخدم مقاول', userRoles: ['contractor_user'], allowsTeam: false },
] as const;

const filterTeamsByAuthority = (authority: string, allTeams: any[]) => {
  if (!authority) return [];
  if (authority === 'field_team') {
    return allTeams.filter((team: any) => {
      const type = String(team?.team_type || '').toLowerCase();
      const name = String(team?.name || '').toLowerCase();
      return type === 'field_crew' || name.includes('صيانة') || name.includes('maintenance');
    });
  }
  return [];
};

export default function ComplaintDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const { canManageComplaints } = useAuth();
  const [complaint, setComplaint] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [linkedTasks, setLinkedTasks] = useState<any[]>([]);
  const [areas, setAreas] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newStatus, setNewStatus] = useState('');
  const [assignee, setAssignee] = useState('');
  const [responsibleAuthority, setResponsibleAuthority] = useState('');
  const [responsibleTeam, setResponsibleTeam] = useState('');
  const [notes, setNotes] = useState('');
  const [updating, setUpdating] = useState(false);
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  // Convert-to-task dialog state
  const [convertOpen, setConvertOpen] = useState(false);
  const [convertTitle, setConvertTitle] = useState('');
  const [convertDescription, setConvertDescription] = useState('');
  const [convertDueDate, setConvertDueDate] = useState('');
  const [convertAssignee, setConvertAssignee] = useState('');
  const [convertAuthority, setConvertAuthority] = useState('');
  const [convertTeam, setConvertTeam] = useState('');
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [convertPriority, setConvertPriority] = useState('');
  const [converting, setConverting] = useState(false);

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
      apiService.getActiveTeams().catch(() => []),
      apiService.getProjects({ limit: 200 }).catch(() => ({ items: [] })),
      apiService.getTasks({ complaint_id: numId, limit: 50 }).catch(() => ({ items: [], total_count: 0 })),
    ])
      .then(([complaintData, activitiesData, areasData, usersData, teamsData, projectsData, linkedTasksData]) => {
        setComplaint(complaintData);
        setActivities(Array.isArray(activitiesData) ? activitiesData : []);
        setAreas(areasData);
        setUsers(usersData.items || []);
        setTeams(Array.isArray(teamsData) ? teamsData : []);
        setProjects((projectsData as any).items || []);
        setLinkedTasks((linkedTasksData as any).items || []);
        const matchedAuthority = responsibleAuthorityOptions.find((opt) => opt.userRoles.includes(complaintData?.assigned_to?.role));
        if (matchedAuthority) {
          setResponsibleAuthority(matchedAuthority.value);
        }
      })
      .catch(() => setError('فشل تحميل بيانات الشكوى'))
      .finally(() => setLoading(false));
  };


  const refreshLinkedTasks = async () => {
    if (!id) return;
    try {
      const linkedTasksData = await apiService.getTasks({ complaint_id: Number(id), limit: 50 });
      setLinkedTasks((linkedTasksData as any).items || []);
    } catch {
      // keep previous list if refresh fails
    }
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
      setResponsibleTeam('');
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

  const openConvertDialog = () => {
    if (!complaint) return;
    setConvertTitle(`معالجة شكوى ${complaint.tracking_number || ''}`.trim());
    setConvertDescription(complaint.description || '');
    setConvertDueDate('');
    setConvertAuthority('');
    setConvertAssignee('');
    setConvertTeam('');
    setConvertPriority(complaint.priority || '');
    setConvertOpen(true);
  };

  const handleConvertSubmit = async (force: boolean = false) => {
    if (!id || !complaint || !convertTitle.trim() || !convertDescription.trim()) {
      toast.error('العنوان والوصف مطلوبان');
      return;
    }
    if (!convertDueDate) {
      toast.error('يرجى تحديد تاريخ الاستحقاق.');
      return;
    }
    if (!convertPriority) {
      toast.error('يرجى اختيار أولوية المهمة.');
      return;
    }

    const hasProjectOwnerUser = users.some((u: any) => u.is_active && ['project_director', 'contracts_manager'].includes(u.role));
    const selectedAssignee = users.find((u: any) => String(u.id) === convertAssignee);

    if (!convertAuthority) {
      toast.error('يرجى اختيار الجهة المسؤولة.');
      return;
    }

    if (convertAuthority === 'field_team') {
      if (!convertAssignee && !convertTeam) {
        toast.error('لفريق ميداني يجب اختيار مستخدم ميداني أو فريق مسؤول على الأقل.');
        return;
      }
      if (convertAssignee && selectedAssignee?.role !== 'field_team') {
        toast.error('المستخدم المسؤول يجب أن يكون من الفريق الميداني.');
        return;
      }
    } else if (convertAuthority === 'contractor_user') {
      if (!convertAssignee) {
        toast.error('يرجى اختيار مستخدم مقاول مسؤول.');
        return;
      }
      if (selectedAssignee?.role !== 'contractor_user') {
        toast.error('المستخدم المسؤول يجب أن يكون مستخدم مقاول.');
        return;
      }
    } else if (convertAuthority === 'engineer_supervisor') {
      if (!convertAssignee) {
        toast.error('يرجى اختيار مشرف هندسي مسؤول.');
        return;
      }
      if (selectedAssignee?.role !== 'engineer_supervisor') {
        toast.error('المستخدم المسؤول يجب أن يكون مشرفاً هندسياً.');
        return;
      }
    } else if (convertAuthority === 'area_supervisor') {
      if (!convertAssignee) {
        toast.error('يرجى اختيار مشرف منطقة مسؤول.');
        return;
      }
      if (selectedAssignee?.role !== 'area_supervisor') {
        toast.error('المستخدم المسؤول يجب أن يكون مشرف منطقة.');
        return;
      }
    } else if (convertAuthority === 'project_director') {
      if (hasProjectOwnerUser && !convertAssignee) {
        toast.error('يرجى اختيار مدير مشروع/مدير عقود مسؤول.');
        return;
      }
      if (convertAssignee && !['project_director', 'contracts_manager'].includes(selectedAssignee?.role)) {
        toast.error('المستخدم المسؤول يجب أن يكون مدير مشروع أو مدير عقود.');
        return;
      }
    }

    // Global guard: authority alone is not enough.
    if (convertAuthority && !convertAssignee && !convertTeam) {
      toast.error('لا يمكن إنشاء مهمة بجهة مسؤولة فقط دون تعيين مسؤول فعلي.');
      return;
    }

    setConverting(true);
    try {
      const payload: any = {
        complaint_id: Number(id),
        title: convertTitle.trim(),
        description: convertDescription.trim(),
        location_text: complaint.location_text || '',
        before_photos: Array.isArray(complaint.images) && complaint.images.length > 0 ? complaint.images : undefined,
        due_date: convertDueDate,
        priority: convertPriority,
      };
      if (convertAssignee) payload.assigned_to_id = Number(convertAssignee);
      if (convertTeam) payload.team_id = Number(convertTeam);
      if (force) payload.force = true;
      await apiService.createTaskFromComplaint(Number(id), payload);
      toast.success('تم إنشاء المهمة وربطها بالشكوى وإسنادها بنجاح');
      setConvertOpen(false);
      await refreshLinkedTasks();
      fetchData();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const proceed = window.confirm(
          (err.detail || 'توجد مهمة مرتبطة بهذه الشكوى مسبقاً.') +
            '\n\nهل ترغب في إنشاء مهمة إضافية على أي حال؟'
        );
        if (proceed) {
          await handleConvertSubmit(true);
          return;
        }
      } else {
        toast.error('فشل تحويل الشكوى إلى مهمة');
      }
    } finally {
      setConverting(false);
    }
  };

  // Convert action is shown only while the complaint is still actionable.
  const canConvertToTask =
    canManageComplaints &&
    complaint &&
    (complaint.status === 'new' || complaint.status === 'under_review');

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
  const selectedAuthority = responsibleAuthorityOptions.find((opt) => opt.value === responsibleAuthority);
  const selectedConvertAuthority = responsibleAuthorityOptions.find((opt) => opt.value === convertAuthority);
  const filteredUsers = users.filter((u: any) => (
    u.is_active && (!selectedAuthority?.userRoles || selectedAuthority.userRoles.includes(u.role))
  ));
  const filteredConvertUsers = users.filter((u: any) => (
    u.is_active && (!!selectedConvertAuthority?.userRoles && selectedConvertAuthority.userRoles.includes(u.role))
  ));
  const filteredTeams = filterTeamsByAuthority(responsibleAuthority, teams);
  const filteredConvertTeams = filterTeamsByAuthority(convertAuthority, teams);
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
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <CardTitle className="text-2xl flex items-center gap-3 flex-wrap">
                تفاصيل الشكوى
                <Badge className={statusColors[complaint.status] || 'bg-gray-100 text-gray-800'}>
                  {statusLabels[complaint.status] || complaint.status}
                </Badge>
                <Badge className={priorityColors[complaint.priority] || 'bg-gray-100 text-gray-800'}>
                  {priorityLabels[complaint.priority] || complaint.priority}
                </Badge>
              </CardTitle>
              {canConvertToTask && (
                <Button onClick={openConvertDialog} className="gap-2">
                  <ListChecks size={18} />
                  تحويل إلى مهمة
                </Button>
              )}
              <Button
                onClick={() => setAssistantOpen(true)}
                variant="outline"
                className="gap-2 border-sky-500/40 text-sky-700 hover:bg-sky-50"
              >
                <Robot size={18} />
                تحليل ذكي للشكوى
              </Button>
            </div>
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
              {detail('المنطقة / الحي', areaObj ? (
                <span className="flex items-center gap-1"><MapPin size={14} /> {areaObj.name_ar || areaObj.name}</span>
              ) : '-')}
              {detail('العنوان التفصيلي', complaint.location_text)}
              {complaint.latitude && complaint.longitude && detail('الإحداثيات', `${complaint.latitude}, ${complaint.longitude}`)}
              {detail('المسؤول المعين', assignedUser ? assignedUser.full_name : '-')}
              {detail('المشروع المرتبط', complaint.project_id ? (
                <Link to={`/projects/${complaint.project_id}`} className="text-primary hover:underline">
                  {projects.find((p: any) => p.id === complaint.project_id)?.title || `#${complaint.project_id}`}
                </Link>
              ) : 'غير مرتبط بمشروع')}
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

        {/* Status Update – only for authorized roles */}
        {canManageComplaints && (
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
                <label className="text-sm font-medium">الجهة المسؤولة</label>
                <Select value={responsibleAuthority} onValueChange={(value) => {
                  setResponsibleAuthority(value);
                  setAssignee('');
                  setResponsibleTeam('');
                }}>
                  <SelectTrigger><SelectValue placeholder="اختر الجهة المسؤولة" /></SelectTrigger>
                  <SelectContent>
                    {responsibleAuthorityOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">المستخدم المسؤول</label>
                <Select value={assignee} onValueChange={setAssignee} disabled={!selectedAuthority}>
                  <SelectTrigger>
                    <SelectValue placeholder={selectedAuthority ? 'اختر المستخدم المسؤول' : 'اختر الجهة المسؤولة أولاً'} />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredUsers.map((u: any) => (
                      <SelectItem key={u.id} value={String(u.id)}>{u.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedAuthority?.allowsTeam && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">الفريق المسؤول (عند توفره)</label>
                  <Select value={responsibleTeam || '__none__'} onValueChange={(v) => setResponsibleTeam(v === '__none__' ? '' : v)}>
                    <SelectTrigger><SelectValue placeholder="اختر الفريق (اختياري)" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">— بدون فريق —</SelectItem>
                      {filteredTeams.map((t: any) => (
                        <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            <Textarea
              placeholder="ملاحظات (اختياري)..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              التسلسل المعتمد: الطلب/الشكوى ← الجهة المسؤولة ← المستخدم/الفريق المسؤول ← التنفيذ.
            </p>
            <Button
              onClick={() => {
                if (newStatus && destructiveStatuses.includes(newStatus)) {
                  setConfirmAction('update');
                } else {
                  handleStatusUpdate();
                }
              }}
              disabled={
                (!newStatus && !notes && !assignee) ||
                updating
              }
            >
              {updating ? <Spinner className="animate-spin ml-2" size={16} /> : null}
              تحديث الشكوى
            </Button>
          </CardContent>
        </Card>
        )}

        {/* Linked tasks (created from this complaint) */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListChecks size={20} />
              المهام المرتبطة
              <Badge variant="outline">{linkedTasks.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {linkedTasks.length === 0 ? (
              <div className="text-sm text-muted-foreground py-4 text-center">
                لا توجد مهام مرتبطة بهذه الشكوى بعد.
                {canConvertToTask && (
                  <span className="block mt-1">
                    استخدم زر "تحويل إلى مهمة" أعلى الصفحة لإنشاء مهمة تنفيذية مرتبطة.
                  </span>
                )}
              </div>
            ) : (
              <div className="divide-y">
                {linkedTasks.map((t: any) => {
                  const tStatusColors: Record<string, string> = {
                    pending: 'bg-yellow-100 text-yellow-800',
                    assigned: 'bg-orange-100 text-orange-800',
                    in_progress: 'bg-purple-100 text-purple-800',
                    completed: 'bg-green-100 text-green-800',
                    cancelled: 'bg-red-100 text-red-800',
                  };
                  const tStatusLabels: Record<string, string> = {
                    pending: 'معلقة', assigned: 'مُعينة', in_progress: 'قيد التنفيذ',
                    completed: 'مكتملة', cancelled: 'ملغاة',
                  };
                  return (
                    <Link
                      key={t.id}
                      to={`/tasks/${t.id}`}
                      className="flex items-center justify-between gap-3 py-3 hover:bg-muted/40 px-2 -mx-2 rounded transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{t.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          مهمة #{t.id}
                          {t.due_date && ` • الاستحقاق ${format(new Date(t.due_date), 'yyyy/MM/dd')}`}
                        </p>
                      </div>
                      <Badge className={tStatusColors[t.status] || 'bg-gray-100 text-gray-800'}>
                        {tStatusLabels[t.status] || t.status}
                      </Badge>
                    </Link>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Internal discussion (Phase 2 — context-linked thread) */}
        <ContextMessagesPanel
          contextType="complaint"
          contextId={complaint.id}
          contextTitle={complaint.tracking_number ? `شكوى ${complaint.tracking_number}` : `شكوى #${complaint.id}`}
        />

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

      {/* Convert complaint to task dialog */}
      <Dialog open={convertOpen} onOpenChange={setConvertOpen}>
        <DialogContent dir="rtl" className="max-w-lg">
          <DialogHeader>
            <DialogTitle>تحويل الشكوى إلى مهمة تنفيذية</DialogTitle>
            <DialogDescription>
              ستُنشأ مهمة جديدة مرتبطة بهذه الشكوى وسيتم تحديث حالة الشكوى إلى "مُعينة".
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">عنوان المهمة *</label>
              <Input value={convertTitle} onChange={(e) => setConvertTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">وصف المهمة *</label>
              <Textarea value={convertDescription} onChange={(e) => setConvertDescription(e.target.value)} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">تاريخ الاستحقاق</label>
                <Input type="date" value={convertDueDate} onChange={(e) => setConvertDueDate(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">الأولوية</label>
                <Select value={convertPriority} onValueChange={setConvertPriority}>
                  <SelectTrigger><SelectValue placeholder="الأولوية" /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(priorityLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">الجهة المسؤولة</label>
                <Select value={convertAuthority} onValueChange={(value) => {
                  setConvertAuthority(value);
                  setConvertAssignee('');
                  setConvertTeam('');
                }}>
                  <SelectTrigger><SelectValue placeholder="اختر الجهة المسؤولة" /></SelectTrigger>
                  <SelectContent>
                    {responsibleAuthorityOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">المستخدم المسؤول</label>
                <Select value={convertAssignee} onValueChange={setConvertAssignee} disabled={!selectedConvertAuthority}>
                  <SelectTrigger>
                    <SelectValue placeholder={selectedConvertAuthority ? 'اختر المستخدم المسؤول' : 'اختر الجهة المسؤولة أولاً'} />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredConvertUsers.map((u: any) => (
                      <SelectItem key={u.id} value={String(u.id)}>{u.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedConvertAuthority?.allowsTeam && (
              <div className="space-y-2">
                <label className="text-sm font-medium">الفريق المسؤول (عند توفره)</label>
                <Select value={convertTeam || '__none__'} onValueChange={(v) => setConvertTeam(v === '__none__' ? '' : v)}>
                  <SelectTrigger><SelectValue placeholder="اختر الفريق (اختياري)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">— بدون فريق —</SelectItem>
                    {filteredConvertTeams.map((t: any) => (
                      <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConvertOpen(false)} disabled={converting}>إلغاء</Button>
            <Button onClick={() => handleConvertSubmit()} disabled={converting}>
              {converting ? <Spinner className="animate-spin ml-2" size={16} /> : null}
              إنشاء المهمة
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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

      {/* Phase-3 context-aware smart assistant */}
      <SmartAssistantDrawer
        open={assistantOpen}
        onOpenChange={setAssistantOpen}
        context={{
          contextType: 'complaint',
          contextId: complaint.id,
          contextTitle: complaint.tracking_number || `#${complaint.id}`,
        }}
      />
    </Layout>
  );
}
