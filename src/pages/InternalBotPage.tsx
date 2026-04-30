import { useEffect, useState } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

export default function InternalBotPage() {
  const [question, setQuestion] = useState('');
  const [days, setDays] = useState('30');
  const [municipalityId, setMunicipalityId] = useState('all');
  const [districtId, setDistrictId] = useState('all');
  const [projectId, setProjectId] = useState('all');
  const [projects, setProjects] = useState<any[]>([]);
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiService.getProjects({ limit: 200 }).then((r) => setProjects(r.items || [])).catch(() => setProjects([]));
  }, []);

  const ask = async (preset?: string) => {
    const q = (preset || question).trim();
    if (!q) return;
    setLoading(true); setError('');
    try {
      const res = await apiService.queryInternalBot({
        question: q,
        days: Number(days) || undefined,
        municipality_id: municipalityId === 'all' ? undefined : Number(municipalityId),
        district_id: districtId === 'all' ? undefined : Number(districtId),
        project_id: projectId === 'all' ? undefined : Number(projectId),
      });
      setResult(res);
      if (preset) setQuestion(preset);
    } catch (e: any) { setError(e?.message || 'تعذر تنفيذ الاستعلام'); }
    finally { setLoading(false); }
  };

  return (
    <Layout>
      <div dir="rtl" className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>المساعد الذكي الداخلي</CardTitle>
            <p className="text-sm text-muted-foreground">أداة داخلية لدعم اتخاذ القرار الإداري وليست روبوتاً عاماً للمواطنين.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {['ملخص الشكاوى', 'ملخص المهام', 'العقود التي تقترب من الانتهاء'].map((preset) => (
                <Button key={preset} type="button" variant="outline" onClick={() => ask(preset)}>{preset}</Button>
              ))}
            </div>
            <Input placeholder="اكتب سؤالك التحليلي..." value={question} onChange={(e) => setQuestion(e.target.value)} />
            <div className="grid gap-2 md:grid-cols-4">
              <Input value={days} onChange={(e) => setDays(e.target.value)} placeholder="الأيام" />
              <Select value={municipalityId} onValueChange={setMunicipalityId}><SelectTrigger><SelectValue placeholder="البلدية" /></SelectTrigger><SelectContent><SelectItem value="all">كل البلديات</SelectItem></SelectContent></Select>
              <Select value={districtId} onValueChange={setDistrictId}><SelectTrigger><SelectValue placeholder="الحي" /></SelectTrigger><SelectContent><SelectItem value="all">كل الأحياء</SelectItem></SelectContent></Select>
              <Select value={projectId} onValueChange={setProjectId}><SelectTrigger><SelectValue placeholder="المشروع" /></SelectTrigger><SelectContent><SelectItem value="all">كل المشاريع</SelectItem>{projects.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.title}</SelectItem>)}</SelectContent></Select>
            </div>
            <Button onClick={() => ask()} disabled={loading || !question.trim()}>{loading ? 'جارٍ التحليل...' : 'تنفيذ الاستعلام'}</Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardHeader><CardTitle>نتائج المساعد</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div><span className="font-semibold">النية:</span> <Badge variant="secondary">{result.intent || '-'}</Badge></div>
              <div><span className="font-semibold">الملخص:</span> {result.summary || 'لا يوجد ملخص.'}</div>
              <div>
                <span className="font-semibold">الإحصاءات:</span>
                <pre className="text-xs bg-muted/30 rounded p-2 mt-1 overflow-auto">{JSON.stringify(result.counts || result.statistics || {}, null, 2)}</pre>
              </div>
              <div>
                <span className="font-semibold">الصفوف:</span>
                {Array.isArray(result.rows) && result.rows.length > 0 ? (
                  <pre className="text-xs bg-muted/30 rounded p-2 mt-1 overflow-auto">{JSON.stringify(result.rows, null, 2)}</pre>
                ) : <p className="text-sm text-muted-foreground mt-1">لا توجد صفوف نتائج.</p>}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
