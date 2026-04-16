import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiService } from '@/services/api';
import { toast } from 'sonner';
import { UploadSimple, X } from '@phosphor-icons/react';

export default function ComplaintSubmitPage() {
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [complaintType, setComplaintType] = useState('');
  const [description, setDescription] = useState('');
  const [locationText, setLocationText] = useState('');
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [uploadedPaths, setUploadedPaths] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

    try {
      let imagePaths = '';
      if (imageFiles.length > 0) {
        setUploading(true);
        const paths: string[] = [];
        for (const file of imageFiles) {
          const res = await apiService.uploadFile(file, 'complaints');
          paths.push(res.path);
        }
        imagePaths = paths.join(',');
        setUploadedPaths(paths);
        setUploading(false);
      }

      const result = await apiService.createComplaint({
        full_name: fullName,
        phone,
        complaint_type: complaintType,
        description,
        location_text: locationText,
        ...(imagePaths ? { images: imagePaths } : {}),
      });

      setTrackingNumber(result.tracking_number);
      setSubmitted(true);
      toast.success('تم تقديم الشكوى بنجاح');
    } catch (error) {
      toast.error('فشل تقديم الشكوى. حاول مرة أخرى.');
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-center text-2xl">تم تقديم الشكوى بنجاح</CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <div className="p-6 bg-accent/10 rounded-lg">
              <p className="text-sm text-muted-foreground mb-2">رقم المتابعة</p>
              <p className="text-3xl font-bold text-accent">{trackingNumber}</p>
            </div>
            <p className="text-sm text-muted-foreground">
              احتفظ بهذا الرقم لتتبع شكواك
            </p>
            <Button onClick={() => window.location.href = '/complaints/track'} className="w-full">
              تتبع الشكوى الآن
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-4" dir="rtl">
      <div className="container mx-auto max-w-2xl py-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">تقديم شكوى جديدة</CardTitle>
            <p className="text-sm text-muted-foreground">قدم شكواك وسنتابعها بأسرع وقت</p>
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
                <Label htmlFor="complaintType">نوع الشكوى *</Label>
                <Select value={complaintType} onValueChange={setComplaintType}>
                  <SelectTrigger>
                    <SelectValue placeholder="اختر نوع الشكوى" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="infrastructure">البنية التحتية</SelectItem>
                    <SelectItem value="cleaning">النظافة</SelectItem>
                    <SelectItem value="electricity">الكهرباء</SelectItem>
                    <SelectItem value="water">المياه</SelectItem>
                    <SelectItem value="roads">الطرق</SelectItem>
                    <SelectItem value="lighting">الإنارة</SelectItem>
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
                <Label htmlFor="locationText">الموقع</Label>
                <Input
                  id="locationText"
                  value={locationText}
                  onChange={(e) => setLocationText(e.target.value)}
                  placeholder="مثال: جزيرة أ، البرج 1"
                />
              </div>

              <div className="space-y-2">
                <Label>صور مرفقة</Label>
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

              <Button type="submit" className="w-full" disabled={uploading}>
                {uploading ? 'جارٍ رفع الملفات...' : 'تقديم الشكوى'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
