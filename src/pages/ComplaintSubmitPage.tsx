import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiService, ApiError } from '@/services/api';
import { toast } from 'sonner';
import { UploadSimple, X, CheckCircle, Copy, ArrowLeft, Info, FileText, User, Phone, MapPin, PaperPlaneTilt } from '@phosphor-icons/react';
import { PublicShell } from '@/components/PublicHeader';


const FALLBACK_AREAS = [
  'الجزيرة 1',
  'الجزيرة 2',
  'المنطقة التجارية المركزية',
  'القطاع الشمالي',
  'القطاع الجنوبي',
  'منطقة الخدمات',
  'الحزام الأخضر',
  'أخرى',
];

export default function ComplaintSubmitPage() {
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [complaintType, setComplaintType] = useState('');
  const [description, setDescription] = useState('');
  const [areas, setAreas] = useState<any[]>([]);
  const [selectedArea, setSelectedArea] = useState('');
  const [detailedAddress, setDetailedAddress] = useState('');
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiService.getAreas()
      .then((data) => setAreas(Array.isArray(data) ? data : []))
      .catch(() => setAreas([]));
  }, []);

  const copyTracking = async () => {
    try {
      await navigator.clipboard.writeText(trackingNumber);
      toast.success('تم نسخ رقم المتابعة');
    } catch {
      toast.error('تعذّر نسخ رقم المتابعة');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setImageFiles((prev) => [...prev, ...files]);
    if (e.target) e.target.value = '';
  };

  const removeFile = (index: number) => {
    setImageFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!complaintType) {
      toast.error('يرجى اختيار نوع الطلب');
      return;
    }

    setSubmitting(true);
    try {
      const selectedAreaObj = areas.find((a: any) => String(a.id) === selectedArea);
      const selectedAreaName = selectedAreaObj
        ? (selectedAreaObj.name_ar || selectedAreaObj.name)
        : (selectedArea.startsWith('fallback:') ? selectedArea.replace('fallback:', '') : '');

      const composedAddress = [selectedAreaName, detailedAddress.trim()].filter(Boolean).join(' - ');

      const result = await apiService.submitComplaintWithAttachments({
        full_name: fullName,
        phone,
        complaint_type: complaintType,
        description,
        area_id: selectedAreaObj ? Number(selectedAreaObj.id) : undefined,
        location_text: composedAddress || undefined,
      }, imageFiles);

      if (result?.queued) {
        toast.success('تم حفظ الطلب محليًا وسيتم إرساله عند عودة الاتصال');
        setSubmitted(true);
        setTrackingNumber('LOCAL-PENDING');
        return;
      }

      setTrackingNumber(result.tracking_number);
      setSubmitted(true);
      toast.success('تم تقديم الطلب / الشكوى بنجاح');
    } catch (error) {
      if (error instanceof ApiError && error.detail) {
        toast.error(`فشل تقديم الطلب: ${error.detail}`);
      } else {
        toast.error('فشل تقديم الطلب. حاول مرة أخرى.');
      }
    } finally {
      setUploading(false);
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <PublicShell>
        <div className="container mx-auto px-4 py-8 md:py-14 max-w-2xl" dir="rtl">
          <Card className="shadow-lg border-0 ring-1 ring-border/60">
            <CardHeader className="items-center text-center pb-4 pt-8">
              <div className="mx-auto w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mb-4 shadow-sm">
                <CheckCircle size={44} className="text-green-600" weight="fill" />
              </div>
              <CardTitle className="text-2xl font-bold">تم استلام طلبك بنجاح</CardTitle>
              <p className="text-sm text-muted-foreground mt-2 max-w-sm mx-auto leading-relaxed">
                احتفظ برقم المتابعة التالي — ستحتاجه لتتبع حالة طلبك / شكواك لاحقاً.
              </p>
            </CardHeader>
            <CardContent className="space-y-5 pb-8">
              <div className="p-6 bg-primary/5 rounded-2xl text-center border border-primary/15">
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">رقم المتابعة</p>
                <p className="text-3xl font-bold text-primary font-mono tracking-widest">{trackingNumber}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-3 gap-1.5 text-muted-foreground hover:text-foreground"
                  onClick={copyTracking}
                >
                  <Copy size={14} />
                  نسخ الرقم
                </Button>
              </div>

              <div className="rounded-xl border bg-muted/30 p-5 text-sm space-y-3">
                <p className="font-semibold flex items-center gap-2 text-foreground">
                  <Info size={16} className="text-primary" />
                  ماذا يحدث بعد الآن؟
                </p>
                <ol className="space-y-2 text-muted-foreground">
                  {[
                    'سيقوم فريق الاستقبال بمراجعة طلبك خلال أيام العمل القادمة.',
                    'عند تحويله إلى مهمة تنفيذية، سيتم تعيين الفريق المختص لمعالجته.',
                    'يمكنك تتبع كل مرحلة برقم المتابعة ورقم هاتفك في صفحة "تتبع طلب / شكوى".',
                  ].map((step, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="flex-shrink-0 mt-0.5 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-bold">
                        {i + 1}
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <Link to="/complaints/track" className="block">
                  <Button className="w-full h-12 gap-2 rounded-xl text-sm font-semibold shadow-sm">
                    تتبع الطلب الآن
                    <ArrowLeft size={16} />
                  </Button>
                </Link>
                <Link to="/" className="block">
                  <Button variant="outline" className="w-full h-12 rounded-xl text-sm">العودة للرئيسية</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </PublicShell>
    );
  }

  return (
    <PublicShell>
      <div className="container mx-auto px-4 py-6 md:py-10 max-w-2xl" dir="rtl">
        <Card className="shadow-lg border-0 ring-1 ring-border/60">
          <CardHeader className="pb-2 pt-7 px-6">
            <CardTitle className="text-2xl font-bold">تقديم طلب / شكوى جديدة</CardTitle>
            <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
              املأ الحقول التالية بدقة لمساعدتنا في توجيه طلبك للجهة المعنية بأسرع وقت.{' '}
              <Link to="/complaints/track" className="text-primary hover:underline font-medium">
                لديك طلب سابق؟ تتبعه من هنا
              </Link>
            </p>
          </CardHeader>
          <CardContent className="px-6 pb-7">
            <form onSubmit={handleSubmit} className="space-y-5">

              {/* Section: Personal info */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-1 border-b border-border/50">
                  <User size={15} className="text-muted-foreground" />
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">بيانات مقدم الطلب</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="fullName" className="text-sm font-medium">الاسم الكامل <span className="text-destructive">*</span></Label>
                    <Input
                      id="fullName"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      placeholder="أدخل الاسم الكامل"
                      className="h-10 rounded-lg"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="phone" className="text-sm font-medium">رقم الهاتف <span className="text-destructive">*</span></Label>
                    <Input
                      id="phone"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      required
                      placeholder="09XX XXXXXXX"
                      className="h-10 rounded-lg"
                    />
                  </div>
                </div>
              </div>

              {/* Section: Complaint details */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-1 border-b border-border/50">
                  <FileText size={15} className="text-muted-foreground" />
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">تفاصيل الطلب / الشكوى</span>
                </div>

                <div className="space-y-1.5" style={{'--accent': 'var(--primary)', '--accent-foreground': 'var(--primary-foreground)'} as React.CSSProperties}>
                  <Label htmlFor="complaintType" className="text-sm font-medium">نوع الطلب <span className="text-destructive">*</span></Label>
                  <Select value={complaintType} onValueChange={setComplaintType}>
                    <SelectTrigger className="h-10 rounded-lg">
                      <SelectValue placeholder="اختر نوع الطلب أو الشكوى" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="heating_network">صيانة شبكة التدفئة</SelectItem>
                      <SelectItem value="corruption">شكوى فساد</SelectItem>
                      <SelectItem value="infrastructure">البنية التحتية</SelectItem>
                      <SelectItem value="other">أخرى</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="description" className="text-sm font-medium">الوصف التفصيلي <span className="text-destructive">*</span></Label>
                  <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                    rows={5}
                    placeholder="صِف المشكلة أو الطلب بوضوح — النوع، المكان، المدة، الأعطال الملحوظة…"
                    className="resize-none rounded-lg text-sm leading-relaxed"
                  />
                </div>
              </div>

              {/* Section: Location */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-1 border-b border-border/50">
                  <MapPin size={15} className="text-muted-foreground" />
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">الموقع والعنوان</span>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="area" className="text-sm font-medium">المنطقة / الحي</Label>
                  <Select value={selectedArea} onValueChange={setSelectedArea}>
                    <SelectTrigger id="area" className="h-10 rounded-lg">
                      <SelectValue placeholder="اختر المنطقة / الحي" />
                    </SelectTrigger>
                    <SelectContent>
                      {areas.length > 0
                        ? areas.map((a: any) => (
                          <SelectItem key={a.id} value={String(a.id)}>{a.name_ar || a.name}</SelectItem>
                        ))
                        : FALLBACK_AREAS.map((name) => (
                          <SelectItem key={name} value={`fallback:${name}`}>{name}</SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="detailedAddress" className="text-sm font-medium">العنوان التفصيلي</Label>
                  <Input
                    id="detailedAddress"
                    value={detailedAddress}
                    onChange={(e) => setDetailedAddress(e.target.value)}
                    placeholder="مثال: الجزيرة 10، البرج 3، الطابق 3، الشقة 23"
                    className="h-10 rounded-lg"
                  />
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    العنوان التفصيلي (الجزيرة/البرج/الشارع/الطابق) يساعد الفريق على الوصول بسرعة.
                  </p>
                </div>
              </div>

              {/* Section: Attachments */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 pb-1 border-b border-border/50">
                  <UploadSimple size={15} className="text-muted-foreground" />
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">صور ومستندات (اختياري)</span>
                </div>

                <div
                  className="border-2 border-dashed border-border/60 rounded-xl p-6 text-center cursor-pointer hover:border-primary/40 hover:bg-primary/[0.02] transition-all duration-200"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadSimple className="mx-auto mb-2 text-muted-foreground" size={28} />
                  <p className="text-sm font-medium">اضغط لاختيار صور أو مستندات</p>
                  <p className="text-xs text-muted-foreground mt-1">JPG، PNG، PDF — حتى 10 ميغابايت لكل ملف</p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.gif,.pdf"
                  multiple
                  className="hidden"
                  onChange={handleFileSelect}
                />
                {imageFiles.length > 0 && (
                  <div className="space-y-1.5 mt-1">
                    {imageFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-muted/50 rounded-lg px-3 py-2 text-sm border border-border/40">
                        <span className="truncate text-xs text-foreground/80 max-w-[80%]">{file.name}</span>
                        <button type="button" onClick={() => removeFile(idx)} className="text-muted-foreground hover:text-destructive transition-colors shrink-0 ms-2">
                          <X size={15} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* CTA Button */}
              <div className="pt-2">
                <Button
                  type="submit"
                  className="w-full h-13 py-3.5 rounded-xl text-base font-semibold gap-2.5 shadow-sm hover:shadow-md transition-all duration-200 tracking-wide"
                  disabled={submitting || uploading}
                  size="lg"
                >
                  {uploading ? (
                    'جارٍ رفع الملفات...'
                  ) : submitting ? (
                    'جارٍ إرسال الطلب...'
                  ) : (
                    <>
                      <PaperPlaneTilt size={18} weight="fill" />
                      تقديم الطلب / الشكوى
                    </>
                  )}
                </Button>
                <p className="text-center text-xs text-muted-foreground mt-2.5">
                  بعد الإرسال ستحصل على رقم متابعة لتتبع حالة طلبك
                </p>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </PublicShell>
  );
}
