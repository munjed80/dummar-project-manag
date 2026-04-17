import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Spinner, Warning, Copy } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const dupStatusLabels: Record<string, string> = {
  pending: 'معلق',
  confirmed_same: 'مؤكد - نفس العقد',
  confirmed_different: 'مؤكد - مختلف',
  review_later: 'مراجعة لاحقاً',
};

const dupStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed_same: 'bg-red-100 text-red-800',
  confirmed_different: 'bg-green-100 text-green-800',
  review_later: 'bg-gray-100 text-gray-800',
};

interface DuplicateRecord {
  id: number;
  document_id: number;
  contract_id_a: number;
  contract_id_b: number;
  similarity_score: number;
  match_reasons: string;
  status: string;
  reviewed_by_id: number | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

function parseMatchReasons(raw: string): string[] {
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function DuplicateReviewPage() {
  const [duplicates, setDuplicates] = useState<DuplicateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [reviewNotes, setReviewNotes] = useState<Record<number, string>>({});
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchData = () => {
    setLoading(true);
    setError('');
    const params: { status_filter?: string } = {};
    if (statusFilter && statusFilter !== 'all') {
      params.status_filter = statusFilter;
    }
    apiService
      .getIntelligenceDuplicates(params)
      .then((data) => {
        setDuplicates(Array.isArray(data) ? data : []);
      })
      .catch(() => setError('فشل تحميل بيانات التكرارات'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleReview = async (id: number, status: string) => {
    setActionLoading(id);
    try {
      await apiService.reviewDuplicate(id, {
        status,
        review_notes: reviewNotes[id] || undefined,
      });
      toast.success('تم تحديث حالة التكرار بنجاح');
      setReviewingId(null);
      setReviewNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      fetchData();
    } catch {
      toast.error('فشل تحديث حالة التكرار');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold mb-1 flex items-center gap-2">
              <Copy size={28} />
              مراجعة التكرارات
            </h1>
            <p className="text-muted-foreground">مراجعة العقود المتشابهة والمكررة المحتملة</p>
          </div>

          {/* Filter */}
          <div className="w-full sm:w-[200px]">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="تصفية حسب الحالة" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">المعلقة فقط</SelectItem>
                <SelectItem value="all">الكل</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="text-center py-8 text-destructive flex flex-col items-center gap-2">
            <Warning size={32} />
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchData}>
              إعادة المحاولة
            </Button>
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner className="animate-spin" size={32} />
          </div>
        ) : !error && duplicates.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12 text-muted-foreground">
              <Copy size={48} className="mx-auto mb-4 opacity-50" />
              <p>لا توجد تكرارات {statusFilter === 'pending' ? 'معلقة' : ''} للمراجعة</p>
            </CardContent>
          </Card>
        ) : (
          /* Duplicate Cards */
          <div className="space-y-4">
            {duplicates.map((dup) => {
              const reasons = parseMatchReasons(dup.match_reasons);
              const similarityPercent = (Number(dup.similarity_score) * 100).toFixed(1);
              const isReviewing = reviewingId === dup.id;
              const isLoading = actionLoading === dup.id;

              return (
                <Card key={dup.id}>
                  <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      <CardTitle className="text-lg">تكرار #{dup.id}</CardTitle>
                      <Badge className={dupStatusColors[dup.status] || 'bg-gray-100 text-gray-800'}>
                        {dupStatusLabels[dup.status] || dup.status}
                      </Badge>
                    </div>
                    <div className="text-left flex-shrink-0">
                      <span className="text-2xl font-bold text-primary">{similarityPercent}%</span>
                      <p className="text-xs text-muted-foreground">نسبة التشابه</p>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {/* Contract links */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="p-3 rounded-lg border">
                        <p className="text-sm text-muted-foreground mb-1">العقد الأول</p>
                        <Link
                          to={`/contracts/${dup.contract_id_a}`}
                          className="text-primary hover:underline font-medium"
                        >
                          عقد #{dup.contract_id_a}
                        </Link>
                      </div>
                      <div className="p-3 rounded-lg border">
                        <p className="text-sm text-muted-foreground mb-1">العقد الثاني</p>
                        <Link
                          to={`/contracts/${dup.contract_id_b}`}
                          className="text-primary hover:underline font-medium"
                        >
                          عقد #{dup.contract_id_b}
                        </Link>
                      </div>
                    </div>

                    {/* Match reasons */}
                    {reasons.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">أسباب التشابه:</p>
                        <div className="flex flex-wrap gap-2">
                          {reasons.map((reason, idx) => (
                            <Badge key={idx} variant="outline">
                              {reason}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Metadata */}
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>
                        تاريخ الإنشاء:{' '}
                        {dup.created_at ? format(new Date(dup.created_at), 'yyyy/MM/dd') : '-'}
                      </span>
                      {dup.reviewed_at && (
                        <span>
                          تاريخ المراجعة:{' '}
                          {format(new Date(dup.reviewed_at), 'yyyy/MM/dd HH:mm')}
                        </span>
                      )}
                      {dup.review_notes && (
                        <span>ملاحظات: {dup.review_notes}</span>
                      )}
                    </div>

                    {/* Review actions */}
                    {dup.status === 'pending' && (
                      <div className="border-t pt-4 space-y-3">
                        {isReviewing ? (
                          <>
                            <Input
                              placeholder="ملاحظات المراجعة (اختياري)"
                              value={reviewNotes[dup.id] || ''}
                              onChange={(e) =>
                                setReviewNotes((prev) => ({ ...prev, [dup.id]: e.target.value }))
                              }
                              dir="auto"
                            />
                            <div className="flex flex-wrap gap-2">
                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={isLoading}
                                onClick={() => handleReview(dup.id, 'confirmed_same')}
                              >
                                {isLoading && <Spinner className="animate-spin ml-1" size={16} />}
                                نفس العقد
                              </Button>
                              <Button
                                size="sm"
                                className="bg-green-600 hover:bg-green-700"
                                disabled={isLoading}
                                onClick={() => handleReview(dup.id, 'confirmed_different')}
                              >
                                {isLoading && <Spinner className="animate-spin ml-1" size={16} />}
                                عقد مختلف
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={isLoading}
                                onClick={() => handleReview(dup.id, 'review_later')}
                              >
                                {isLoading && <Spinner className="animate-spin ml-1" size={16} />}
                                مراجعة لاحقاً
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={isLoading}
                                onClick={() => setReviewingId(null)}
                              >
                                إلغاء
                              </Button>
                            </div>
                          </>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setReviewingId(dup.id)}
                          >
                            مراجعة
                          </Button>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Back link */}
        <Link
          to="/contract-intelligence"
          className="text-primary hover:underline inline-block"
        >
          ← العودة لمركز ذكاء العقود
        </Link>
      </div>
    </Layout>
  );
}
