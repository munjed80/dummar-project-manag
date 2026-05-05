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
import { MagnifyingGlass, ArrowLeft, Info, CheckCircle, MapPin, Calendar, Clock, FileText } from '@phosphor-icons/react';
import { format } from 'date-fns';

const statusLabels: Record<string, string> = {
  new: 'قيد المعالجة', under_review: 'قيد المعالجة', assigned: 'قيد المعالجة',
  in_progress: 'قيد التنفيذ', resolved: 'تم الحل', rejected: 'مرفوضة',
};

const statusColors: Record<string, string> = {
  new: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  under_review: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  assigned: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  in_progress: 'bg-purple-100 text-purple-800 border-purple-200',
  resolved: 'bg-green-100 text-green-800 border-green-200',
  rejected: 'bg-red-100 text-red-800 border-red-200',
};

const typeLabels: Record<string, string> = {
  infrastructure: 'البنية التحتية', cleaning: 'النظافة', electricity: 'الكهرباء',
  water: 'المياه', roads: 'الطرق', lighting: 'الإنارة',
  heating_network: 'صيانة شبكة التدفئة', corruption: 'شكوى فساد', other: 'أخرى',
};

const statusGuidance: Record<string, string> = {
  new: 'تم استلام طلبك وهو قيد المعالجة من قِبَل فريق إدارة الشكاوى.',
  under_review: 'تم استلام طلبك وهو قيد المعالجة من قِبَل فريق إدارة الشكاوى.',
  assigned: 'تم استلام طلبك وهو قيد المعالجة من قِبَل فريق إدارة الشكاوى.',
  in_progress: 'الفريق المختص يعمل على معالجة طلبك حالياً.',
  resolved: 'تمت معالجة طلبك وإغلاقه. شكراً لإبلاغنا.',
  rejected: 'تم إغلاق طلبك دون تنفيذ. يمكنك التواصل مع الإدارة لمزيد من التفاصيل.',
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
      toast.error('لم يتم العثور على الطلب. تحقق من رقم المتابعة ورقم الهاتف.');
    } finally {
      setSearching(false);
    }
  };

  const renderResult = () => {
    if (!complaint) return null;
    const sLabel = statusLabels[complaint.status] || complaint.status;
    const sColor = statusColors[complaint.status] || 'bg-gray-100 text-gray-800 border-gray-200';
    const guidance = statusGuidance[complaint.status];

    return (
      <Card className="mt-6 shadow-md border-0 ring-1 ring-border/60">
        <CardHeader className="pb-3 pt-5 px-5">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-0.5">رقم المتابعة</p>
              <p className="font-mono font-bold text-xl tracking-wider text-foreground">{complaint.tracking_number}</p>
            </div>
            <Badge className={`${sColor} border text-sm px-3 py-1 font-semibold`}>{sLabel}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 px-5 pb-6">
          {guidance && (
            <div className="rounded-xl border bg-primary/5 border-primary/15 p-4 text-sm flex items-start gap-3">
              <Info size={16} className="mt-0.5 text-primary shrink-0" />
              <span className="leading-relaxed text-foreground/80">{guidance}</span>
            </div>
          )}

          {/* Data grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-0 divide-y sm:divide-y-0 sm:divide-x sm:divide-x-reverse rounded-xl border border-border/50 overflow-hidden">
            <div className="px-4 py-3 bg-muted/20">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-1">
                <FileText size={12} />
                نوع الطلب
              </p>
              <p className="font-semibold text-sm">{typeLabels[complaint.complaint_type] || complaint.complaint_type}</p>
            </div>
            {complaint.location_text && (
              <div className="px-4 py-3 bg-muted/20">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-1">
                  <MapPin size={12} />
                  العنوان
                </p>
                <p className="font-semibold text-sm">{complaint.location_text}</p>
              </div>
            )}
            {complaint.created_at && (
              <div className="px-4 py-3">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-1">
                  <Calendar size={12} />
                  تاريخ التقديم
                </p>
                <p className="font-semibold text-sm">{format(new Date(complaint.created_at), 'yyyy/MM/dd')}</p>
              </div>
            )}
            {complaint.updated_at && (
              <div className="px-4 py-3">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-1">
                  <Clock size={12} />
                  آخر تحديث
                </p>
                <p className="font-semibold text-sm">{format(new Date(complaint.updated_at), 'yyyy/MM/dd')}</p>
              </div>
            )}
          </div>

          {complaint.resolved_at && (
            <div className="flex items-center gap-3 rounded-xl bg-green-50 border border-green-100 px-4 py-3">
              <CheckCircle size={18} className="text-green-600 shrink-0" weight="fill" />
              <div>
                <p className="text-xs font-medium text-green-700">تاريخ الإغلاق</p>
                <p className="font-bold text-sm text-green-800">{format(new Date(complaint.resolved_at), 'yyyy/MM/dd')}</p>
              </div>
            </div>
          )}

          {complaint.description && (
            <>
              <Separator className="my-1" />
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-muted-foreground">وصف الطلب</p>
                <p className="text-sm whitespace-pre-wrap leading-relaxed text-foreground/80">{complaint.description}</p>
              </div>
            </>
          )}

          {complaint.repair_result && (
            <>
              <Separator className="my-1" />
              <div className="space-y-4">
                <p className="text-sm font-bold flex items-center gap-2 text-green-700">
                  <CheckCircle size={16} className="text-green-600" weight="fill" />
                  نتيجة الإصلاح
                </p>
                {complaint.repair_result.notes && (
                  <div className="rounded-xl bg-muted/30 border border-border/40 p-4">
                    <p className="text-xs font-medium text-muted-foreground mb-1.5">ملاحظات الفريق المنفّذ</p>
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{complaint.repair_result.notes}</p>
                  </div>
                )}
                {Array.isArray(complaint.repair_result.after_photos) && complaint.repair_result.after_photos.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">صور بعد الإصلاح</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {complaint.repair_result.after_photos.map((path: string, i: number) => (
                        <a
                          key={i}
                          href={`/uploads/${path}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`عرض صورة بعد الإصلاح رقم ${i + 1}`}
                          className="block rounded-xl overflow-hidden border border-border/40 hover:opacity-90 transition-opacity"
                        >
                          <img
                            src={`/uploads/${path}`}
                            alt={`صورة بعد الإصلاح ${i + 1}`}
                            className="w-full h-24 object-cover"
                            loading="lazy"
                          />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          <Separator className="my-1" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            هذه الصفحة تعرض حالة الطلب الحالية فقط. للاستفسار عن تفاصيل التنفيذ، تواصل مع إدارة المشروع.
          </p>
        </CardContent>
      </Card>
    );
  };

  return (
    <PublicShell>
      <div className="container mx-auto px-4 py-6 md:py-10 max-w-2xl" dir="rtl">
        <Card className="shadow-lg border-0 ring-1 ring-border/60">
          <CardHeader className="pb-2 pt-7 px-6">
            <CardTitle className="flex items-center gap-2.5 text-2xl font-bold">
              <MagnifyingGlass size={22} className="text-primary" />
              تتبع الطلب / الشكوى
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
              أدخل رقم المتابعة الذي حصلت عليه عند تقديم الطلب ورقم الهاتف نفسه لمعرفة الحالة.{' '}
              <Link to="/complaints/new" className="text-primary hover:underline font-medium">
                لم تقدّم طلباً بعد؟ ابدأ من هنا
              </Link>
            </p>
          </CardHeader>
          <CardContent className="px-6 pb-7">
            <form onSubmit={handleTrack} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="trackingNumber" className="text-sm font-medium">رقم المتابعة</Label>
                <Input
                  id="trackingNumber"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  placeholder="مثال: CMP12345678"
                  required
                  className="h-10 rounded-lg font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="phone" className="text-sm font-medium">رقم الهاتف</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="نفس الرقم الذي استخدمته عند التقديم"
                  required
                  className="h-10 rounded-lg"
                />
              </div>
              <div className="pt-1">
                <Button
                  type="submit"
                  className="w-full h-12 rounded-xl text-base font-semibold gap-2.5 shadow-sm hover:shadow-md transition-all duration-200"
                  disabled={searching}
                  size="lg"
                >
                  {searching ? (
                    'جارٍ البحث...'
                  ) : (
                    <>
                      <MagnifyingGlass size={18} weight="bold" />
                      تتبع الطلب
                      <ArrowLeft size={16} />
                    </>
                  )}
                </Button>
              </div>
            </form>

            {notFound && !complaint && (
              <div className="mt-5 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
                <p className="font-semibold text-destructive">لم يتم العثور على الطلب</p>
                <p className="text-muted-foreground mt-1 leading-relaxed">
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
