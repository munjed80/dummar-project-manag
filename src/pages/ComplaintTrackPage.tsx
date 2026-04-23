import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { apiService } from '@/services/api';
import { toast } from 'sonner';
import { PublicShell } from '@/components/PublicHeader';
import { MagnifyingGlass, ArrowLeft, Info, CheckCircle, MapPin } from '@phosphor-icons/react';
import { format } from 'date-fns';

const statusLabels: Record<string, string> = {
  new: 'جديدة', under_review: 'قيد المراجعة', assigned: 'مُعينة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};

const statusColors: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800',
  under_review: 'bg-yellow-100 text-yellow-800',
  assigned: 'bg-orange-100 text-orange-800',
  in_progress: 'bg-purple-100 text-purple-800',
  resolved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
};

const typeLabels: Record<string, string> = {
  infrastructure: 'البنية التحتية', cleaning: 'النظافة', electricity: 'الكهرباء',
  water: 'المياه', roads: 'الطرق', lighting: 'الإنارة', other: 'أخرى',
};

const statusGuidance: Record<string, string> = {
  new: 'تم استلام شكواك وهي بانتظار المراجعة من قِبَل فريق الاستقبال.',
  under_review: 'يقوم فريق الاستقبال بمراجعة شكواك حالياً.',
  assigned: 'تم تحويل شكواك إلى مهمة تنفيذية وأُسندت إلى الفريق المختص.',
  in_progress: 'الفريق المختص يعمل على معالجة شكواك حالياً.',
  resolved: 'تمت معالجة شكواك وإغلاقها. شكراً لإبلاغنا.',
  rejected: 'تم إغلاق شكواك دون تنفيذ. يمكنك التواصل مع الإدارة لمزيد من التفاصيل.',
};

export default function ComplaintTrackPage() {
  const [trackingNumber, setTrackingNumber] = useState('');
  const [phone, setPhone] = useState('');
  const [complaint, setComplaint] = useState<any>(null);
  const [searching, setSearching] = useState(false);
  const [notFound, setNotFound] = useState(false);

  const handleTrack = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearching(true);
    setNotFound(false);
    try {
      const result = await apiService.trackComplaint(trackingNumber.trim(), phone.trim());
      setComplaint(result);
    } catch (error) {
      setComplaint(null);
      setNotFound(true);
      toast.error('لم يتم العثور على الشكوى. تحقق من رقم المتابعة ورقم الهاتف.');
    } finally {
      setSearching(false);
    }
  };

  const renderResult = () => {
    if (!complaint) return null;
    const sLabel = statusLabels[complaint.status] || complaint.status;
    const sColor = statusColors[complaint.status] || 'bg-gray-100 text-gray-800';
    const guidance = statusGuidance[complaint.status];

    return (
      <Card className="mt-6">
        <CardHeader>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="text-xs text-muted-foreground">رقم المتابعة</p>
              <p className="font-mono font-bold text-lg">{complaint.tracking_number}</p>
            </div>
            <Badge className={sColor}>{sLabel}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {guidance && (
            <div className="rounded-md border bg-muted/40 p-3 text-sm flex items-start gap-2">
              <Info size={16} className="mt-0.5 text-muted-foreground shrink-0" />
              <span>{guidance}</span>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">النوع</p>
              <p className="font-medium">{typeLabels[complaint.complaint_type] || complaint.complaint_type}</p>
            </div>
            {complaint.location_text && (
              <div>
                <p className="text-xs text-muted-foreground">الموقع</p>
                <p className="font-medium flex items-center gap-1">
                  <MapPin size={14} /> {complaint.location_text}
                </p>
              </div>
            )}
            {complaint.created_at && (
              <div>
                <p className="text-xs text-muted-foreground">تاريخ التقديم</p>
                <p className="font-medium">{format(new Date(complaint.created_at), 'yyyy/MM/dd')}</p>
              </div>
            )}
            {complaint.updated_at && (
              <div>
                <p className="text-xs text-muted-foreground">آخر تحديث</p>
                <p className="font-medium">{format(new Date(complaint.updated_at), 'yyyy/MM/dd')}</p>
              </div>
            )}
            {complaint.resolved_at && (
              <div className="sm:col-span-2">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <CheckCircle size={14} className="text-green-600" /> تاريخ الإغلاق
                </p>
                <p className="font-medium">{format(new Date(complaint.resolved_at), 'yyyy/MM/dd')}</p>
              </div>
            )}
          </div>
          {complaint.description && (
            <>
              <Separator />
              <div>
                <p className="text-xs text-muted-foreground mb-1">الوصف</p>
                <p className="text-sm whitespace-pre-wrap">{complaint.description}</p>
              </div>
            </>
          )}
          <Separator />
          <p className="text-xs text-muted-foreground">
            هذه الصفحة تعرض حالة الشكوى الحالية فقط. للاستفسار عن تفاصيل التنفيذ، تواصل مع إدارة المشروع.
          </p>
        </CardContent>
      </Card>
    );
  };

  return (
    <PublicShell>
      <div className="container mx-auto px-4 py-6 md:py-10 max-w-2xl" dir="rtl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <MagnifyingGlass size={22} />
              تتبع الشكوى
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              أدخل رقم المتابعة الذي حصلت عليه عند تقديم الشكوى ورقم الهاتف نفسه لمعرفة الحالة.{' '}
              <Link to="/complaints/new" className="text-primary hover:underline">
                لم تقدّم شكوى بعد؟ ابدأ من هنا
              </Link>
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleTrack} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="trackingNumber">رقم المتابعة</Label>
                <Input
                  id="trackingNumber"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  placeholder="مثال: CMP12345678"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">رقم الهاتف</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="نفس الرقم الذي استخدمته عند التقديم"
                  required
                />
              </div>
              <Button type="submit" className="w-full gap-2" disabled={searching}>
                {searching ? 'جارٍ البحث...' : 'تتبع'}
                {!searching && <ArrowLeft size={16} />}
              </Button>
            </form>

            {notFound && !complaint && (
              <div className="mt-6 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm">
                <p className="font-medium text-destructive">لم يتم العثور على الشكوى</p>
                <p className="text-muted-foreground mt-1">
                  تأكد من أن رقم المتابعة ورقم الهاتف يطابقان البيانات التي أدخلتها عند التقديم.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {renderResult()}
      </div>
    </PublicShell>
  );
}
