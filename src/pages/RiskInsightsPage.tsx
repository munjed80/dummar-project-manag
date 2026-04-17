import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Spinner, Warning, ShieldWarning, CheckCircle } from '@phosphor-icons/react';
import { format } from 'date-fns';
import { toast } from 'sonner';

interface RiskFlag {
  id: number;
  document_id: number | null;
  contract_id: number | null;
  risk_type: string;
  severity: string;
  description: string;
  details: string | null;
  is_resolved: boolean;
  resolved_by_id: number | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
}

const severityLabels: Record<string, string> = {
  low: 'منخفض',
  medium: 'متوسط',
  high: 'مرتفع',
  critical: 'حرج',
};

const severityColors: Record<string, string> = {
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

const severityOrder: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export default function RiskInsightsPage() {
  const [risks, setRisks] = useState<RiskFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [unresolvedOnly, setUnresolvedOnly] = useState(true);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState<Record<number, string>>({});

  const fetchRisks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiService.getIntelligenceRisks({
        unresolved_only: unresolvedOnly,
      });
      const sorted = [...data].sort(
        (a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
      );
      setRisks(sorted);
    } catch {
      setError('فشل في تحميل بيانات المخاطر');
    } finally {
      setLoading(false);
    }
  }, [unresolvedOnly]);

  useEffect(() => {
    fetchRisks();
  }, [fetchRisks]);

  const handleResolve = async (id: number) => {
    const notes = resolutionNotes[id]?.trim() || '';
    try {
      setResolvingId(id);
      await apiService.resolveRiskFlag(id, notes || undefined);
      toast.success('تم حل المخاطرة بنجاح');
      setResolutionNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      fetchRisks();
    } catch {
      toast.error('فشل في حل المخاطرة');
    } finally {
      setResolvingId(null);
    }
  };

  const severityIcon = (severity: string) => {
    if (severity === 'critical' || severity === 'high') {
      return <ShieldWarning size={20} className="text-red-600" />;
    }
    return <Warning size={20} className="text-yellow-600" />;
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page header */}
        <div>
          <h1 className="text-2xl md:text-3xl font-bold mb-2">رؤى المخاطر</h1>
          <p className="text-muted-foreground">
            عرض جميع علامات المخاطر عبر جميع العقود مع إمكانية التصفية والحل
          </p>
        </div>

        {/* Filter controls */}
        <Card>
          <CardContent className="pt-6">
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={unresolvedOnly}
                onChange={(e) => setUnresolvedOnly(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm font-medium">عرض المخاطر غير المحلولة فقط</span>
            </label>
          </CardContent>
        </Card>

        {/* Error state */}
        {error && (
          <div className="text-center py-8 text-destructive flex flex-col items-center gap-2">
            <Warning size={32} />
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchRisks}>
              إعادة المحاولة
            </Button>
          </div>
        )}

        {/* Loading state */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner className="animate-spin" size={32} />
          </div>
        ) : !error && risks.length === 0 ? (
          /* Empty state */
          <Card>
            <CardContent className="py-12 text-center">
              <CheckCircle size={48} className="mx-auto mb-4 text-green-500" />
              <p className="text-lg font-medium text-muted-foreground">
                {unresolvedOnly
                  ? 'لا توجد مخاطر غير محلولة — ممتاز!'
                  : 'لا توجد مخاطر مسجلة'}
              </p>
            </CardContent>
          </Card>
        ) : (
          /* Risk list */
          !error && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                عدد النتائج: {risks.length}
              </p>

              {risks.map((risk) => (
                <Card key={risk.id} className="overflow-hidden">
                  <CardHeader className="pb-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {severityIcon(risk.severity)}
                        <CardTitle className="text-base">
                          {risk.risk_type}
                        </CardTitle>
                      </div>
                      <Badge className={severityColors[risk.severity] ?? 'bg-gray-100 text-gray-800'}>
                        {severityLabels[risk.severity] ?? risk.severity}
                      </Badge>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-3">
                    <p className="text-sm">{risk.description}</p>

                    {risk.details && (
                      <p className="text-sm text-muted-foreground bg-muted/50 rounded p-3">
                        {risk.details}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                      <span>
                        تاريخ الإنشاء: {format(new Date(risk.created_at), 'yyyy/MM/dd')}
                      </span>

                      {risk.document_id && (
                        <Link
                          to={`/contract-intelligence/documents/${risk.document_id}`}
                          className="text-primary hover:underline"
                        >
                          عرض المستند
                        </Link>
                      )}

                      {risk.contract_id && (
                        <Link
                          to={`/contracts/${risk.contract_id}`}
                          className="text-primary hover:underline"
                        >
                          عرض العقد
                        </Link>
                      )}
                    </div>

                    {risk.is_resolved ? (
                      <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded p-3">
                        <CheckCircle size={18} />
                        <span>
                          تم الحل
                          {risk.resolved_at &&
                            ` — ${format(new Date(risk.resolved_at), 'yyyy/MM/dd')}`}
                        </span>
                        {risk.resolution_notes && (
                          <span className="text-muted-foreground mr-2">
                            ({risk.resolution_notes})
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 border-t pt-3">
                        <Input
                          placeholder="ملاحظات الحل (اختياري)"
                          value={resolutionNotes[risk.id] ?? ''}
                          onChange={(e) =>
                            setResolutionNotes((prev) => ({
                              ...prev,
                              [risk.id]: e.target.value,
                            }))
                          }
                          className="flex-1"
                        />
                        <Button
                          size="sm"
                          onClick={() => handleResolve(risk.id)}
                          disabled={resolvingId === risk.id}
                        >
                          {resolvingId === risk.id ? (
                            <Spinner className="animate-spin ml-2" size={16} />
                          ) : (
                            <CheckCircle size={16} className="ml-2" />
                          )}
                          حل المخاطرة
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )
        )}
      </div>
    </Layout>
  );
}
