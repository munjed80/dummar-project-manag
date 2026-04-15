import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Spinner, FilePdf, ClockCounterClockwise } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const statusLabels: Record<string, string> = {
  draft: 'مسودة', under_review: 'قيد المراجعة', approved: 'مُعتمد',
  active: 'نشط', suspended: 'معلق', completed: 'مكتمل',
  expired: 'منتهي', cancelled: 'ملغى',
};

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800', under_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800', active: 'bg-green-100 text-green-800',
  suspended: 'bg-orange-100 text-orange-800', completed: 'bg-emerald-100 text-emerald-800',
  expired: 'bg-red-100 text-red-800', cancelled: 'bg-red-100 text-red-800',
};

const typeLabels: Record<string, string> = {
  construction: 'إنشاء', maintenance: 'صيانة', supply: 'توريد',
  consulting: 'استشارات', other: 'أخرى',
};

function formatValue(value: number | string | null | undefined): string {
  if (value == null) return '-';
  return Number(value).toLocaleString('en-US');
}

export default function ContractDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [contract, setContract] = useState<any>(null);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    const numId = Number(id);
    Promise.all([
      apiService.getContract(numId),
      apiService.getContractApprovals(numId).catch(() => []),
    ])
      .then(([contractData, approvalsData]) => {
        setContract(contractData);
        setApprovals(Array.isArray(approvalsData) ? approvalsData : []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleGeneratePdf = async () => {
    if (!id) return;
    setGeneratingPdf(true);
    try {
      await apiService.generateContractPdf(Number(id));
      toast.success('تم إنشاء ملف PDF بنجاح');
    } catch {
      toast.error('فشل إنشاء ملف PDF');
    } finally {
      setGeneratingPdf(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  if (!contract) {
    return (
      <Layout>
        <div className="text-center py-12 text-muted-foreground">لم يتم العثور على العقد</div>
      </Layout>
    );
  }

  const detail = (label: string, value: React.ReactNode) => (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '-'}</span>
    </div>
  );

  return (
    <Layout>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                تفاصيل العقد
                <Badge className={statusColors[contract.status] || 'bg-gray-100 text-gray-800'}>
                  {statusLabels[contract.status] || contract.status}
                </Badge>
              </div>
              <Button onClick={handleGeneratePdf} disabled={generatingPdf} variant="outline">
                {generatingPdf ? <Spinner className="animate-spin ml-2" size={16} /> : <FilePdf className="ml-2" size={18} />}
                إنشاء PDF
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {detail('رقم العقد', <span className="font-mono">{contract.contract_number}</span>)}
              {detail('العنوان', contract.title)}
              {detail('المقاول', contract.contractor_name)}
              {detail('النوع', typeLabels[contract.type] || contract.type)}
              {detail('القيمة', formatValue(contract.value))}
              {detail('تاريخ البدء', contract.start_date ? format(new Date(contract.start_date), 'yyyy/MM/dd') : '-')}
              {detail('تاريخ الانتهاء', contract.end_date ? format(new Date(contract.end_date), 'yyyy/MM/dd') : '-')}
              {detail('تاريخ الإنشاء', contract.created_at ? format(new Date(contract.created_at), 'yyyy/MM/dd HH:mm') : '-')}
              {detail('تاريخ التحديث', contract.updated_at ? format(new Date(contract.updated_at), 'yyyy/MM/dd HH:mm') : '-')}
            </div>
            {contract.description && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">الوصف</span>
                  <p className="mt-1">{contract.description}</p>
                </div>
              </>
            )}
            {contract.terms && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">الشروط</span>
                  <p className="mt-1">{contract.terms}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClockCounterClockwise size={20} />
              سجل الموافقات
            </CardTitle>
          </CardHeader>
          <CardContent>
            {approvals.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">لا توجد موافقات</p>
            ) : (
              <div className="space-y-4">
                {approvals.map((app: any, idx: number) => (
                  <div key={app.id || idx} className="flex gap-4 border-r-2 border-primary pr-4 pb-4">
                    <div className="flex-1">
                      <p className="font-medium">{app.action || '-'}</p>
                      {app.comments && <p className="text-sm text-muted-foreground mt-1">{app.comments}</p>}
                      {app.user_name && <p className="text-sm mt-1">بواسطة: {app.user_name}</p>}
                      <p className="text-xs text-muted-foreground mt-1">
                        {app.created_at ? format(new Date(app.created_at), 'yyyy/MM/dd HH:mm') : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
