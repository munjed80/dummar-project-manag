import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Spinner, Warning } from '@phosphor-icons/react';
import { format } from 'date-fns';

const PAGE_SIZE = 15;

const statusLabels: Record<string, string> = {
  queued: 'في الانتظار',
  processing: 'قيد المعالجة',
  ocr_complete: 'OCR مكتمل',
  extracted: 'مستخرج',
  review: 'قيد المراجعة',
  approved: 'مُعتمد',
  rejected: 'مرفوض',
  failed: 'فشل',
};

const statusColors: Record<string, string> = {
  queued: 'bg-gray-100 text-gray-800',
  processing: 'bg-blue-100 text-blue-800',
  ocr_complete: 'bg-cyan-100 text-cyan-800',
  extracted: 'bg-indigo-100 text-indigo-800',
  review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  failed: 'bg-red-100 text-red-800',
};

interface QueueDocument {
  id: string;
  original_filename: string;
  processing_status: string;
  ocr_confidence: number | null;
  extraction_confidence: number | null;
  suggested_type: string | null;
  created_at: string;
  file_type: string;
  import_source: string;
}

function formatConfidence(value: number | null): string {
  if (value == null) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export default function ProcessingQueuePage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<QueueDocument[]>([]);
  const [queueLength, setQueueLength] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: { status_filter?: string; skip: number; limit: number } = {
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    };
    if (statusFilter !== 'all') params.status_filter = statusFilter;

    apiService
      .getProcessingQueue(params)
      .then((data) => {
        setDocuments(data.documents);
        setQueueLength(data.queue_length);
      })
      .catch(() => setError('فشل تحميل قائمة المعالجة'))
      .finally(() => setLoading(false));
  }, [statusFilter, page]);

  // Reset page when filter changes
  useEffect(() => {
    setPage(0);
  }, [statusFilter]);

  const totalPages = Math.max(1, Math.ceil(queueLength / PAGE_SIZE));

  return (
    <Layout>
      <div className="space-y-6" dir="rtl">
        <Card>
          <CardHeader>
            <CardTitle>قائمة معالجة العقود</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Filter */}
            <div className="flex flex-col sm:flex-row flex-wrap gap-3">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue placeholder="حالة المعالجة" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">جميع الحالات</SelectItem>
                  {Object.entries(statusLabels).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground self-center">
                {queueLength} مستند
              </span>
            </div>

            {/* Error */}
            {error && (
              <div className="text-center py-8 text-destructive flex flex-col items-center gap-2">
                <Warning size={32} />
                <p>{error}</p>
              </div>
            )}

            {/* Loading */}
            {loading ? (
              <div className="flex justify-center py-12">
                <Spinner className="animate-spin" size={32} />
              </div>
            ) : !error && (
              <>
                {documents.length === 0 ? (
                  <p className="text-center py-8 text-muted-foreground">لا توجد مستندات</p>
                ) : (
                  <>
                    {/* Desktop Table */}
                    <div className="responsive-table-desktop">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">اسم الملف</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">نوع الملف</TableHead>
                            <TableHead className="text-right">النوع المقترح</TableHead>
                            <TableHead className="text-right">ثقة OCR</TableHead>
                            <TableHead className="text-right">ثقة الاستخراج</TableHead>
                            <TableHead className="text-right">المصدر</TableHead>
                            <TableHead className="text-right">التاريخ</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {documents.map((doc) => (
                            <TableRow
                              key={doc.id}
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => navigate(`/contract-intelligence/documents/${doc.id}`)}
                            >
                              <TableCell className="font-medium">{doc.original_filename}</TableCell>
                              <TableCell>
                                <Badge className={statusColors[doc.processing_status] ?? ''}>
                                  {statusLabels[doc.processing_status] ?? doc.processing_status}
                                </Badge>
                              </TableCell>
                              <TableCell>{doc.file_type}</TableCell>
                              <TableCell>{doc.suggested_type ?? '—'}</TableCell>
                              <TableCell>{formatConfidence(doc.ocr_confidence)}</TableCell>
                              <TableCell>{formatConfidence(doc.extraction_confidence)}</TableCell>
                              <TableCell>{doc.import_source}</TableCell>
                              <TableCell>{format(new Date(doc.created_at), 'yyyy/MM/dd')}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>

                    {/* Mobile Cards */}
                    <div className="responsive-cards-mobile space-y-3">
                      {documents.map((doc) => (
                        <Card
                          key={doc.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/contract-intelligence/documents/${doc.id}`)}
                        >
                          <CardContent className="p-4 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-sm truncate max-w-[60%]">
                                {doc.original_filename}
                              </span>
                              <Badge className={statusColors[doc.processing_status] ?? ''}>
                                {statusLabels[doc.processing_status] ?? doc.processing_status}
                              </Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-1 text-sm text-muted-foreground">
                              <span>نوع الملف: {doc.file_type}</span>
                              <span>المصدر: {doc.import_source}</span>
                              <span>ثقة OCR: {formatConfidence(doc.ocr_confidence)}</span>
                              <span>ثقة الاستخراج: {formatConfidence(doc.extraction_confidence)}</span>
                              {doc.suggested_type && (
                                <span>النوع المقترح: {doc.suggested_type}</span>
                              )}
                              <span>{format(new Date(doc.created_at), 'yyyy/MM/dd')}</span>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page === 0}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      السابق
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      صفحة {page + 1} من {totalPages} ({queueLength} مستند)
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages - 1}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      التالي
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
