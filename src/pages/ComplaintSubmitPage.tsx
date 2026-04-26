import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiService, ApiError } from '@/services/api';
import { toast } from 'sonner';
import { UploadSimple, X, CheckCircle, Copy, ArrowLeft, Info } from '@phosphor-icons/react';
import { PublicShell } from '@/components/PublicHeader';

export default function ComplaintSubmitPage() {
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [complaintType, setComplaintType] = useState('');
  const [description, setDescription] = useState('');
  const [locationText, setLocationText] = useState('');
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const imagePaths: string[] = [];
      if (imageFiles.length > 0) {
        setUploading(true);
        for (const file of imageFiles) {
          const res = await apiService.uploadFilePublic(file);
          imagePaths.push(res.path);
        }
        setUploading(false);
      }

      const result = await apiService.createComplaint({
        full_name: fullName,
        phone,
        complaint_type: complaintType,
        description,
        location_text: locationText,
        ...(imagePaths.length > 0 ? { images: imagePaths } : {}),
      });

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
          <Card>
            <CardHeader className="items-center text-center">
              <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-2">
                <CheckCircle size={36} className="text-green-600" weight="fill" />
              </div>
              <CardTitle className="text-2xl">تم استلام طلبك بنجاح</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                احتفظ برقم المتابعة التالي — ستحتاجه لتتبع حالة طلبك / شكواك لاحقاً.
              </p>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="p-5 bg-accent/10 rounded-lg text-center">
                <p className="text-xs text-muted-foreground mb-1">رقم المتابعة</p>
                <p className="text-3xl font-bold text-accent font-mono tracking-wider">{trackingNumber}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-2 gap-1"
                  onClick={copyTracking}
                >
                  <Copy size={14} />
                  نسخ الرقم
                </Button>
              </div>

              <div className="rounded-lg border bg-muted/40 p-4 text-sm space-y-2">
                <p className="font-bold flex items-center gap-2">
                  <Info size={16} />
                  ماذا يحدث بعد الآن؟
                </p>
                <ol className="list-decimal pr-5 space-y-1 text-muted-foreground">
                  <li>سيقوم فريق الاستقبال بمراجعة طلبك خلال أيام العمل القادمة.</li>
                  <li>عند تحويله إلى مهمة تنفيذية، سيتم تعيين الفريق المختص لمعالجته.</li>
                  <li>يمكنك تتبع كل مرحلة برقم المتابعة ورقم هاتفك في صفحة "تتبع طلب / شكوى".</li>
                </ol>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Link to="/complaints/track" className="block">
                  <Button className="w-full gap-2">
                    تتبع الطلب الآن
                    <ArrowLeft size={16} />
                  </Button>
                </Link>
                <Link to="/" className="block">
                  <Button variant="outline" className="w-full">العودة للرئيسية</Button>
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
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">تقديم طلب / شكوى جديدة</CardTitle>
            <p className="text-sm text-muted-foreground">
              املأ الحقول التالية بدقة لمساعدتنا في توجيه طلبك للجهة المعنية بأسرع وقت.
              <Link to="/complaints/track" className="text-primary hover:underline mr-1">
                لديك طلب أو شكوى سابقة؟ تتبعها من هنا
              </Link>
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">الاسم الكامل *</Label>
                <Input
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">رقم الهاتف *</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="complaintType">نوع الطلب *</Label>
                <Select value={complaintType} onValueChange={setComplaintType}>
                  <SelectTrigger>
                    <SelectValue placeholder="اختر نوع الطلب" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="infrastructure">البنية التحتية</SelectItem>
                    <SelectItem value="cleaning">النظافة</SelectItem>
                    <SelectItem value="electricity">الكهرباء</SelectItem>
                    <SelectItem value="water">المياه</SelectItem>
                    <SelectItem value="roads">الطرق</SelectItem>
                    <SelectItem value="lighting">الإنارة</SelectItem>
                    <SelectItem value="heating_network">طلب صيانة شبكة التدفئة</SelectItem>
                    <SelectItem value="other">أخرى</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">الوصف *</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  rows={5}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="locationText">العنوان التفصيلي</Label>
                <Input
                  id="locationText"
                  value={locationText}
                  onChange={(e) => setLocationText(e.target.value)}
                  placeholder="مثال: جزيرة أ، البرج 1، الطابق 3، الشقة 12"
                />
                <p className="text-xs text-muted-foreground">
                  حاول كتابة عنوان تفصيلي واضح (الجزيرة/البرج/الشارع/الطابق) ليصل الفريق بسرعة.
                </p>
              </div>

              <div className="space-y-2">
                <Label>صور مرفقة (صورة قبل التنفيذ إن وُجدت)</Label>
                <div
                  className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadSimple className="mx-auto mb-2" size={24} />
                  <p className="text-sm text-muted-foreground">اضغط لاختيار صور أو مستندات</p>
                  <p className="text-xs text-muted-foreground mt-1">JPG, PNG, PDF - حتى 10 ميغابايت</p>
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
                  <div className="space-y-1 mt-2">
                    {imageFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-muted rounded px-3 py-1 text-sm">
                        <span>{file.name}</span>
                        <button type="button" onClick={() => removeFile(idx)} className="text-destructive hover:text-destructive/80">
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={submitting || uploading}>
                {uploading ? 'جارٍ رفع الملفات...' : submitting ? 'جارٍ الإرسال...' : 'تقديم الطلب / الشكوى'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </PublicShell>
  );
}
