import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Spinner, FilePdf, ClockCounterClockwise, Paperclip, Warning, Trash } from '@phosphor-icons/react';
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
  return Number(value).toLocaleString('en-US') + ' ل.س';
}

export default function ContractDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [contract, setContract] = useState<any>(null);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    setError('');
    const numId = Number(id);
    Promise.all([
      apiService.getContract(numId),
      apiService.getContractApprovals(numId).catch(() => []),
    ])
      .then(([contractData, approvalsData]) => {
        setContract(contractData);
        setApprovals(Array.isArray(approvalsData) ? approvalsData : []);
      })
      .catch(() => setError('فشل تحميل بيانات العقد'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleGeneratePdf = async () => {
    if (!id) return;
    setGeneratingPdf(true);
    try {
      const result = await apiService.generateContractPdf(Number(id));
      toast.success('تم إنشاء ملف PDF بنجاح');
      if (result.pdf_path) {
        window.open(`http://localhost:8000${result.pdf_path}`, '_blank');
      }
      fetchData();
    } catch {
      toast.error('فشل إنشاء ملف PDF');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const handleAttachmentsUpdate = async (attachments: string[]) => {
    if (!id) return;
    try {
      await apiService.updateContract(Number(id), { attachments });
      toast.success('تم تحديث المرفقات');
      fetchData();
    } catch {
      toast.error('فشل تحديث المرفقات');
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setDeleting(true);
    try {
      await apiService.deleteContract(Number(id));
      toast.success('تم حذف العقد');
      window.location.href = '/contracts';
    } catch {
      toast.error('فشل حذف العقد - يمكن حذف المسودات فقط');
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12"><Spinner className="animate-spin" size={32} /></div>
      </Layout>
    );
  }

  if (error || !contract) {
    return (
      <Layout>
        <div className="text-center py-12">
          <Warning size={48} className="mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">{error || 'لم يتم العثور على العقد'}</p>
          <Link to="/contracts" className="text-primary hover:underline mt-2 inline-block">العودة للقائمة</Link>
        </div>
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
        {/* Contract Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                تفاصيل العقد
                <Badge className={statusColors[contract.status] || 'bg-gray-100 text-gray-800'}>
                  {statusLabels[contract.status] || contract.status}
                </Badge>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleGeneratePdf} disabled={generatingPdf} variant="outline">
                  {generatingPdf ? <Spinner className="animate-spin ml-2" size={16} /> : <FilePdf className="ml-2" size={18} />}
                  إنشاء PDF
                </Button>
                {contract.pdf_file && (
                  <Button variant="outline" asChild>
                    <a href={`http://localhost:8000${contract.pdf_file}`} target="_blank" rel="noopener noreferrer">
                      <FilePdf className="ml-2" size={18} />
                      تحميل PDF
                    </a>
                  </Button>
                )}
                {contract.status === 'draft' && (
                  <Button variant="destructive" onClick={() => setConfirmDelete(true)}>
                    <Trash className="ml-2" size={16} />
                    حذف
                  </Button>
                )}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {detail('رقم العقد', <span className="font-mono text-lg">{contract.contract_number}</span>)}
              {detail('العنوان', contract.title)}
              {detail('المقاول', contract.contractor_name)}
              {detail('تواصل المقاول', contract.contractor_contact)}
              {detail('النوع', (
                <Badge variant="outline">{typeLabels[contract.contract_type] || contract.contract_type}</Badge>
              ))}
              {detail('القيمة', formatValue(contract.contract_value))}
              {detail('تاريخ البدء', contract.start_date ? format(new Date(contract.start_date), 'yyyy/MM/dd') : '-')}
              {detail('تاريخ الانتهاء', contract.end_date ? format(new Date(contract.end_date), 'yyyy/MM/dd') : '-')}
              {detail('مدة التنفيذ', contract.execution_duration_days ? `${contract.execution_duration_days} يوم` : '-')}
              {detail('المناطق المرتبطة', contract.related_areas)}
              {detail('تاريخ الإنشاء', contract.created_at ? format(new Date(contract.created_at), 'yyyy/MM/dd HH:mm') : '-')}
              {detail('تاريخ التحديث', contract.updated_at ? format(new Date(contract.updated_at), 'yyyy/MM/dd HH:mm') : '-')}
              {contract.approved_at && detail('تاريخ الاعتماد', format(new Date(contract.approved_at), 'yyyy/MM/dd HH:mm'))}
            </div>
            {contract.scope_description && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">نطاق العمل</span>
                  <p className="mt-1 whitespace-pre-wrap">{contract.scope_description}</p>
                </div>
              </>
            )}
            {contract.notes && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">ملاحظات</span>
                  <p className="mt-1 whitespace-pre-wrap">{contract.notes}</p>
                </div>
              </>
            )}

            {/* QR Code */}
            {contract.qr_code && (
              <>
                <Separator className="my-4" />
                <div>
                  <span className="text-sm text-muted-foreground">رمز QR للتحقق</span>
                  <div className="mt-2">
                    <img src={contract.qr_code} alt="QR Code" className="w-32 h-32" />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Attachments */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Paperclip size={20} />
              المرفقات
            </CardTitle>
          </CardHeader>
          <CardContent>
            <FileUpload
              category="contracts"
              accept="all"
              existingFiles={contract.attachments || []}
              onUploadComplete={handleAttachmentsUpdate}
              label="ملفات العقد"
            />
          </CardContent>
        </Card>

        {/* Approval Trail */}
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

      {/* Delete Confirmation */}
      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent dir="rtl">
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد الحذف</AlertDialogTitle>
            <AlertDialogDescription>
              هل أنت متأكد من حذف العقد "{contract.title}"؟ يمكن حذف المسودات فقط. لا يمكن التراجع عن هذا الإجراء.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground" disabled={deleting}>
              {deleting && <Spinner className="animate-spin ml-2" size={16} />}
              حذف العقد
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
