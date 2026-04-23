import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Spinner, ArrowLeft } from '@phosphor-icons/react';
import { toast } from 'sonner';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const statusLabels: Record<string, string> = {
  planned: 'مخطط', active: 'نشط', on_hold: 'متوقف مؤقتاً',
  completed: 'مكتمل', cancelled: 'ملغى',
};

export default function ProjectDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(!id || id === 'new');

  const [formData, setFormData] = useState({
    title: '',
    code: '',
    description: '',
    status: 'active',
    start_date: '',
    end_date: '',
  });

  useEffect(() => {
    if (id && id !== 'new') {
      apiService.getProject(Number(id))
        .then((data) => {
          setProject(data);
          setFormData({
            title: data.title || '',
            code: data.code || '',
            description: data.description || '',
            status: data.status || 'active',
            start_date: data.start_date || '',
            end_date: data.end_date || '',
          });
        })
        .catch(() => toast.error('فشل تحميل بيانات المشروع'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [id]);

  const handleSave = async () => {
    try {
      if (id && id !== 'new') {
        await apiService.updateProject(Number(id), formData);
        toast.success('تم تحديث المشروع');
        setEditing(false);
        const updated = await apiService.getProject(Number(id));
        setProject(updated);
      } else {
        const created = await apiService.createProject(formData);
        toast.success('تم إنشاء المشروع');
        navigate(`/projects/${created.id}`);
      }
    } catch {
      toast.error('فشل حفظ المشروع');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin text-primary" size={32} />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/projects')}>
          <ArrowLeft size={20} className="ml-1" />
          العودة إلى المشاريع
        </Button>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>{id === 'new' ? 'مشروع جديد' : editing ? 'تعديل المشروع' : 'تفاصيل المشروع'}</CardTitle>
              {!editing && project && (
                <Button onClick={() => setEditing(true)}>تعديل</Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>العنوان *</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  disabled={!editing}
                />
              </div>
              <div>
                <Label>الكود *</Label>
                <Input
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  disabled={!editing || (id !== 'new')}
                />
              </div>
              <div>
                <Label>الحالة</Label>
                <Select
                  value={formData.status}
                  onValueChange={(v) => setFormData({ ...formData, status: v })}
                  disabled={!editing}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(statusLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>تاريخ البدء</Label>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  disabled={!editing}
                />
              </div>
              <div>
                <Label>تاريخ الانتهاء</Label>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  disabled={!editing}
                />
              </div>
            </div>
            <div>
              <Label>الوصف</Label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                disabled={!editing}
                rows={4}
              />
            </div>

            {editing && (
              <div className="flex gap-2">
                <Button onClick={handleSave}>حفظ</Button>
                {id !== 'new' && (
                  <Button variant="outline" onClick={() => { setEditing(false); }}>
                    إلغاء
                  </Button>
                )}
              </div>
            )}

            {!editing && project && (
              <div className="grid gap-4 md:grid-cols-3 pt-4 border-t">
                <Card>
                  <CardHeader><CardTitle className="text-sm">المهام</CardTitle></CardHeader>
                  <CardContent><p className="text-2xl font-bold">{project.task_count || 0}</p></CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle className="text-sm">الشكاوى</CardTitle></CardHeader>
                  <CardContent><p className="text-2xl font-bold">{project.complaint_count || 0}</p></CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle className="text-sm">الفرق</CardTitle></CardHeader>
                  <CardContent><p className="text-2xl font-bold">{project.team_count || 0}</p></CardContent>
                </Card>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
