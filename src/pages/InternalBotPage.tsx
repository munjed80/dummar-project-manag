import { useState } from 'react';
import { apiService } from '@/services/api';

export default function InternalBotPage() {
  const [question, setQuestion] = useState('');
  const [intent, setIntent] = useState('');
  const [days, setDays] = useState<number | ''>('');
  const [locationId, setLocationId] = useState<number | ''>('');
  const [projectId, setProjectId] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState('');
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);

  const askBot = async () => {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const res = await apiService.queryInternalBot({
        question,
        intent: intent || undefined,
        days: days === '' ? undefined : Number(days),
        location_id: locationId === '' ? undefined : Number(locationId),
        project_id: projectId === '' ? undefined : Number(projectId),
      });
      setSummary(String(res.summary || ''));
      setRows(Array.isArray(res.rows) ? res.rows : []);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6" dir="rtl">
      <h1 className="text-2xl font-bold mb-4">المساعد الذكي</h1>
      <div className="border rounded-lg p-4 space-y-3">
        <textarea className="w-full border rounded p-2" rows={3} placeholder="اكتب سؤالك..." value={question} onChange={(e) => setQuestion(e.target.value)} />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <select className="border rounded p-2" value={intent} onChange={(e) => setIntent(e.target.value)}>
            <option value="">النية (اختياري)</option>
            <option value="summary">ملخص</option>
            <option value="list">قائمة</option>
            <option value="alerts">تنبيهات</option>
          </select>
          <input className="border rounded p-2" type="number" placeholder="عدد الأيام" value={days} onChange={(e) => setDays(e.target.value === '' ? '' : Number(e.target.value))} />
          <input className="border rounded p-2" type="number" placeholder="رقم الموقع" value={locationId} onChange={(e) => setLocationId(e.target.value === '' ? '' : Number(e.target.value))} />
          <input className="border rounded p-2" type="number" placeholder="رقم المشروع" value={projectId} onChange={(e) => setProjectId(e.target.value === '' ? '' : Number(e.target.value))} />
        </div>
        <button className="bg-primary text-white rounded px-4 py-2" onClick={askBot} disabled={loading}>{loading ? 'جاري التحليل...' : 'إرسال السؤال'}</button>
      </div>

      <div className="mt-4 border rounded-lg p-4">
        <h2 className="font-semibold mb-2">النتائج</h2>
        {!summary && rows.length === 0 && <p className="text-sm text-gray-500">لا توجد نتائج بعد. اطرح سؤالاً لعرض الملخص والبيانات.</p>}
        {summary && <div className="mb-3 p-3 rounded bg-gray-50"><p className="text-sm whitespace-pre-wrap">{summary}</p></div>}
        {rows.length > 0 && (
          <div className="overflow-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr>
                  {Object.keys(rows[0]).map((k) => <th key={k} className="border p-2 bg-gray-50 text-right">{k}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr key={idx}>
                    {Object.keys(rows[0]).map((k) => <td key={k} className="border p-2">{String(row[k] ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
