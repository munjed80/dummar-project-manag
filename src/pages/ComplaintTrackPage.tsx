import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiService } from '@/services/api';
import { toast } from 'sonner';

export default function ComplaintTrackPage() {
  const [trackingNumber, setTrackingNumber] = useState('');
  const [phone, setPhone] = useState('');
  const [complaint, setComplaint] = useState<any>(null);

  const handleTrack = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const result = await apiService.trackComplaint(trackingNumber, phone);
      setComplaint(result);
    } catch (error) {
      toast.error('لم يتم العثور على الشكوى. تحقق من رقم المتابعة ورقم الهاتف.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>تتبع الشكوى</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleTrack} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="trackingNumber">رقم المتابعة</Label>
              <Input
                id="trackingNumber"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">رقم الهاتف</Label>
              <Input
                id="phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">تتبع</Button>
          </form>

          {complaint && (
            <div className="mt-6 p-4 bg-muted rounded-lg space-y-2">
              <p><strong>الحالة:</strong> {complaint.status}</p>
              <p><strong>النوع:</strong> {complaint.complaint_type}</p>
              <p><strong>الوصف:</strong> {complaint.description}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
