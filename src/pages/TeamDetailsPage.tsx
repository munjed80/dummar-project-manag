import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService, ApiError } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Spinner, ArrowLeft, ListChecks } from '@phosphor-icons/react';
import { toast } from 'sonner';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const typeLabels: Record<string, string> = {
  internal_team: 'فريق داخلي', contractor: 'مقاول', field_crew: 'طاقم ميداني', supervision_unit: 'وحدة إشراف',
};

export default function TeamDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [team, setTeam] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(!id || id === 'new');

  const [formData, setFormData] = useState({
    name: '',
    team_type: 'internal_team',
    contact_name: '',
    contact_phone: '',
    notes: '',
    is_active: true,
  });

  useEffect(() => {
    if (id && id !== 'new') {
      apiService.getTeam(Number(id))
        .then((data) => {
          setTeam(data);
          setFormData({
            name: data.name || '',
            team_type: data.team_type || 'internal_team',
            contact_name: data.contact_name || '',
            contact_phone: data.contact_phone || '',
            notes: data.notes || '',
            is_active: data.is_active !== undefined ? data.is_active : true,
          });
        })
        .catch(() => toast.error('فشل تحميل بيانات الفريق'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [id]);

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error('اسم الفريق مطلوب');
      return;
    }
    try {
      if (id && id !== 'new') {
        await apiService.updateTeam(Number(id), formData);
        toast.success('تم تحديث الفريق');
        setEditing(false);
        const updated = await apiService.getTeam(Number(id));
        setTeam(updated);
      } else {
        const created = await apiService.createTeam(formData);
        toast.success('تم إنشاء الفريق');
        navigate(`/teams/${created.id}`);
      }
    } catch (err) {
      const message = err instanceof ApiError
        ? (err.detail ? `فشل حفظ الفريق: ${err.detail}` : 'فشل حفظ الفريق')
        : 'فشل حفظ الفريق';
      toast.error(message);
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
        <Button variant="ghost" onClick={() => navigate('/teams')}>
          <ArrowLeft size={20} className="ml-1" />
          العودة إلى الفرق
        </Button>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>{id === 'new' ? 'فريق جديد' : editing ? 'تعديل الفريق' : 'تفاصيل الفريق'}</CardTitle>
              {!editing && team && (
                <Button onClick={() => setEditing(true)}>تعديل</Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>اسم الفريق *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  disabled={!editing}
                />
              </div>
              <div>
                <Label>النوع</Label>
                <Select
                  value={formData.team_type}
                  onValueChange={(v) => setFormData({ ...formData, team_type: v })}
                  disabled={!editing}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(typeLabels).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>جهة الاتصال</Label>
                <Input
                  value={formData.contact_name}
                  onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                  disabled={!editing}
                />
              </div>
              <div>
                <Label>رقم الهاتف</Label>
                <Input
                  value={formData.contact_phone}
                  onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                  disabled={!editing}
                />
              </div>
              <div>
                <Label>الحالة</Label>
                <Select
                  value={formData.is_active ? 'active' : 'inactive'}
                  onValueChange={(v) => setFormData({ ...formData, is_active: v === 'active' })}
                  disabled={!editing}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">نشط</SelectItem>
                    <SelectItem value="inactive">غير نشط</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>ملاحظات</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
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

            {!editing && team && (
              <div className="pt-4 border-t">
                <Link to={`/tasks?team_id=${team.id}`} className="block">
                  <Card className="hover:bg-muted/50 transition-colors">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <ListChecks size={16} />
                        المهام المسندة
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold">{team.task_count || 0}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        عرض كل المهام المسندة لهذا الفريق
                      </p>
                    </CardContent>
                  </Card>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
