import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Spinner, Warning, CheckCircle, XCircle, ArrowsClockwise } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const statusLabels: Record<string, string> = {
  queued: 'في الانتظار', processing: 'قيد المعالجة', ocr_complete: 'OCR مكتمل',
  extracted: 'مستخرج', review: 'قيد المراجعة', approved: 'مُعتمد',
  rejected: 'مرفوض', failed: 'فشل',
};
const statusColors: Record<string, string> = {
  queued: 'bg-gray-100 text-gray-800', processing: 'bg-blue-100 text-blue-800',
  ocr_complete: 'bg-cyan-100 text-cyan-800', extracted: 'bg-indigo-100 text-indigo-800',
  review: 'bg-yellow-100 text-yellow-800', approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800', failed: 'bg-red-100 text-red-800',
};
const severityLabels: Record<string, string> = {
  low: 'منخفض', medium: 'متوسط', high: 'مرتفع', critical: 'حرج',
};
const severityColors: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800', medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800', critical: 'bg-red-100 text-red-800',
};

export default function DocumentReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<any>(null);
  const [risks, setRisks] = useState<any[]>([]);
  const [duplicates, setDuplicates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  // Editable state derived from document
  const [extractedFields, setExtractedFields] = useState<Record<string, string>>({});
  const [editedSummary, setEditedSummary] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    setError('');
    const numId = Number(id);
    Promise.all([
      apiService.getContractDocument(numId),
      apiService.getIntelligenceRisks({ document_id: numId }).catch(() => []),
      apiService.getIntelligenceDuplicates({ document_id: numId }).catch(() => []),
    ])
      .then(([docData, risksData, dupsData]) => {
        setDocument(docData);
        setRisks(Array.isArray(risksData) ? risksData : []);
        setDuplicates(Array.isArray(dupsData) ? dupsData : []);

        // Parse extracted fields
        let fields: Record<string, string> = {};
        if (docData.extracted_fields) {
          try {
            fields = typeof docData.extracted_fields === 'string'
              ? JSON.parse(docData.extracted_fields)
              : docData.extracted_fields;
          } catch {
            fields = {};
          }
        }
        setExtractedFields(fields);
        setEditedSummary(docData.auto_summary || docData.summary || '');
      })
      .catch(() => setError('فشل تحميل بيانات المستند'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleSaveEdits = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await apiService.updateContractDocument(Number(id), {
        extracted_fields: JSON.stringify(extractedFields),
        edited_summary: editedSummary,
      });
      toast.success('تم حفظ التعديلات بنجاح');
      fetchData();
    } catch {
      toast.error('فشل حفظ التعديلات');
    } finally {
      setSaving(false);
    }
  };

  const handleAction = async (action: string) => {
    if (!id) return;
    setActionLoading(action);
    setConfirmAction(null);
    const numId = Number(id);
    try {
      switch (action) {
        case 'approve':
          await apiService.approveContractDocument(numId);
          toast.success('تم اعتماد المستند بنجاح');
          break;
        case 'reject':
          await apiService.rejectContractDocument(numId);
          toast.success('تم رفض المستند');
          break;
        case 'reprocess':
          await apiService.reprocessDocument(numId);
          toast.success('تمت إعادة معالجة المستند');
          break;
        case 'convert': {
          const result = await apiService.convertDocumentToContract(numId);
          toast.success(`تم تحويل نتيجة التحليل وإعداد عقد رقم ${result.contract_number}`);
          navigate(`/contracts/${result.contract_id}`);
          return;
        }
      }
      fetchData();
    } catch {
      toast.error('فشل تنفيذ الإجراء');
    } finally {
      setActionLoading('');
    }
  };

  const handleResolveRisk = async (riskId: number) => {
    try {
      await apiService.resolveRiskFlag(riskId);
      toast.success('تم حل التنبيه');
      fetchData();
    } catch {
      toast.error('فشل حل التنبيه');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12"><Spinner className="animate-spin" size={32} /></div>
      </Layout>
    );
  }

  if (error || !document) {
    return (
      <Layout>
        <div className="text-center py-12">
          <Warning size={48} className="mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">{error || 'لم يتم العثور على المستند'}</p>
          <Link to="/contract-intelligence" className="text-primary hover:underline mt-2 inline-block">
            العودة للقائمة
          </Link>
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

  const confirmMessages: Record<string, string> = {
    approve: 'هل أنت متأكد من اعتماد هذا المستند؟',
    reject: 'هل أنت متأكد من رفض هذا المستند؟',
    reprocess: 'هل تريد إعادة معالجة هذا المستند؟',
    convert: 'هل أنت متأكد من تحويل نتيجة التحليل إلى عقد استثماري؟',
  };
  const hasAnalysisResult = !!(document?.extracted_fields || document?.ocr_text || document?.auto_summary);

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header & Actions */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold">مراجعة المستند</h1>
            <Badge className={statusColors[document.status] || 'bg-gray-100 text-gray-800'}>
              {statusLabels[document.status] || document.status}
            </Badge>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/investment-contracts')}
            >
              عرض العقود الاستثمارية
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmAction('reprocess')}
              disabled={!!actionLoading}
            >
              {actionLoading === 'reprocess' ? <Spinner className="animate-spin ml-1" size={16} /> : <ArrowsClockwise size={16} className="ml-1" />}
              إعادة المعالجة
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setConfirmAction('reject')}
              disabled={!!actionLoading}
            >
              {actionLoading === 'reject' ? <Spinner className="animate-spin ml-1" size={16} /> : <XCircle size={16} className="ml-1" />}
              رفض
            </Button>
            <Button
              size="sm"
              onClick={() => setConfirmAction('approve')}
              disabled={!!actionLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              {actionLoading === 'approve' ? <Spinner className="animate-spin ml-1" size={16} /> : <CheckCircle size={16} className="ml-1" />}
              اعتماد
            </Button>
            {hasAnalysisResult && (
              <Button
                size="sm"
                onClick={() => setConfirmAction('convert')}
                disabled={!!actionLoading}
              >
                {actionLoading === 'convert' && <Spinner className="animate-spin ml-1" size={16} />}
                تحويل النتيجة إلى عقد استثماري
              </Button>
            )}
          </div>
        </div>

        {/* 1. Document Info */}
        <Card>
          <CardHeader>
            <CardTitle>معلومات المستند</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {detail('اسم الملف', document.original_filename || document.filename)}
              {detail('نوع الملف', document.file_type || document.mime_type || '-')}
              {detail('الحالة', (
                <Badge className={statusColors[document.status] || 'bg-gray-100 text-gray-800'}>
                  {statusLabels[document.status] || document.status}
                </Badge>
              ))}
              {detail('تاريخ الرفع', document.created_at
                ? format(new Date(document.created_at), 'yyyy/MM/dd HH:mm')
                : '-',
              )}
            </div>
          </CardContent>
        </Card>

        {/* 2. OCR Text */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>نص OCR</span>
              {document.ocr_confidence != null && (
                <Badge variant="outline">
                  دقة: {(Number(document.ocr_confidence) * 100).toFixed(1)}%
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              readOnly
              dir="auto"
              className="min-h-[200px] font-mono text-sm"
              value={document.ocr_text || 'لا يوجد نص OCR'}
            />
          </CardContent>
        </Card>

        {/* 3. Extracted Fields (editable) */}
        <Card>
          <CardHeader>
            <CardTitle>الحقول المستخرجة</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.keys(extractedFields).length === 0 ? (
              <p className="text-muted-foreground text-center py-4">لا توجد حقول مستخرجة</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(extractedFields).map(([key, value]) => (
                  <div key={key} className="space-y-1">
                    <label className="text-sm font-medium text-muted-foreground">{key}</label>
                    <Input
                      value={value}
                      onChange={(e) =>
                        setExtractedFields((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                    />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 4. Classification */}
        {(document.classification || document.classification_suggestion) && (
          <Card>
            <CardHeader>
              <CardTitle>التصنيف</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 flex-wrap">
                <Badge variant="outline" className="text-base px-3 py-1">
                  {document.classification || document.classification_suggestion}
                </Badge>
                {document.classification_confidence != null && (
                  <span className="text-sm text-muted-foreground">
                    ثقة: {(Number(document.classification_confidence) * 100).toFixed(1)}%
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 5. Auto Summary (editable) */}
        <Card>
          <CardHeader>
            <CardTitle>الملخص التلقائي</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              dir="auto"
              className="min-h-[120px]"
              value={editedSummary}
              onChange={(e) => setEditedSummary(e.target.value)}
              placeholder="لا يوجد ملخص بعد"
            />
            <Button onClick={handleSaveEdits} disabled={saving} size="sm">
              {saving && <Spinner className="animate-spin ml-1" size={16} />}
              حفظ التعديلات
            </Button>
          </CardContent>
        </Card>

        {/* 6. Risk Flags */}
        <Card>
          <CardHeader>
            <CardTitle>تنبيهات المخاطر</CardTitle>
          </CardHeader>
          <CardContent>
            {risks.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">لا توجد تنبيهات</p>
            ) : (
              <div className="space-y-3">
                {risks.map((risk: any) => (
                  <div
                    key={risk.id}
                    className="flex items-start justify-between gap-3 p-3 rounded-lg border"
                  >
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className={severityColors[risk.severity] || 'bg-gray-100 text-gray-800'}>
                          {severityLabels[risk.severity] || risk.severity}
                        </Badge>
                        <span className="font-medium">{risk.risk_type || risk.type}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{risk.description}</p>
                    </div>
                    {!risk.resolved_at && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleResolveRisk(risk.id)}
                      >
                        حل
                      </Button>
                    )}
                    {risk.resolved_at && (
                      <Badge className="bg-green-100 text-green-800">تم الحل</Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 7. Duplicate Matches */}
        <Card>
          <CardHeader>
            <CardTitle>المستندات المكررة</CardTitle>
          </CardHeader>
          <CardContent>
            {duplicates.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">لا توجد مستندات مكررة</p>
            ) : (
              <div className="space-y-3">
                {duplicates.map((dup: any) => (
                  <div
                    key={dup.id}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg border"
                  >
                    <div className="flex-1 space-y-1">
                      <p className="font-medium">
                        {dup.matched_filename || dup.matched_document_filename || `مستند #${dup.matched_document_id || dup.document_b_id}`}
                      </p>
                      {dup.similarity_score != null && (
                        <p className="text-sm text-muted-foreground">
                          نسبة التشابه: {(Number(dup.similarity_score) * 100).toFixed(1)}%
                        </p>
                      )}
                    </div>
                    {dup.matched_document_id && (
                      <Link
                        to={`/contract-intelligence/documents/${dup.matched_document_id || dup.document_b_id}`}
                        className="text-primary hover:underline text-sm"
                      >
                        عرض
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Separator />

        {/* Back link */}
        <Link to="/contract-intelligence" className="text-primary hover:underline inline-block">
          ← العودة لذكاء العقود
        </Link>
      </div>

      {/* Confirmation Dialog */}
      <AlertDialog open={!!confirmAction} onOpenChange={(open) => { if (!open) setConfirmAction(null); }}>
        <AlertDialogContent dir="rtl">
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد الإجراء</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction ? confirmMessages[confirmAction] : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction onClick={() => confirmAction && handleAction(confirmAction)}>
              تأكيد
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
}
