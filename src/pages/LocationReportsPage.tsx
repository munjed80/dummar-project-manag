import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Spinner, MapPin, WarningCircle, ChartBar, ArrowLeft,
  FileText, ChatCircleDots, ListChecks,
} from '@phosphor-icons/react';

const LOCATION_TYPE_LABELS: Record<string, string> = {
  island: 'جزيرة',
  sector: 'قطاع',
  block: 'بلوك',
  building: 'مبنى',
  tower: 'برج',
  street: 'شارع',
  service_point: 'نقطة خدمة',
  other: 'أخرى',
};

export default function LocationReportsPage() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiService.getLocationReportSummary()
      .then(setReport)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !report) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  const maxComplaints = Math.max(
    ...report.most_complaints.map((s: any) => s.complaint_count),
    1,
  );

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ChartBar size={28} />
            تقارير المواقع
          </h1>
          <Link to="/locations">
            <Button variant="outline" size="sm" className="flex items-center gap-1">
              <ArrowLeft size={14} />
              العودة للمواقع
            </Button>
          </Link>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold">{report.total_locations}</div>
              <div className="text-sm text-muted-foreground">إجمالي المواقع</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold text-red-600">{report.hotspots.length}</div>
              <div className="text-sm text-muted-foreground">نقاط ساخنة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold text-orange-600">{report.most_delayed.length}</div>
              <div className="text-sm text-muted-foreground">مواقع فيها تأخير</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold text-green-600">{report.contract_coverage.length}</div>
              <div className="text-sm text-muted-foreground">مواقع بتغطية عقدية</div>
            </CardContent>
          </Card>
        </div>

        {/* By Type Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">توزيع المواقع حسب النوع</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(report.by_type).map(([type, count]) => (
                <div key={type} className="flex items-center gap-2 p-2 bg-muted/30 rounded-md">
                  <MapPin size={16} className="text-primary" />
                  <span className="text-sm flex-1">{LOCATION_TYPE_LABELS[type] || type}</span>
                  <Badge variant="secondary">{count as number}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Hotspots */}
        {report.hotspots.length > 0 && (
          <Card className="border-red-200">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2 text-red-700">
                <WarningCircle size={20} />
                النقاط الساخنة — أكثر المواقع شكاوى مفتوحة
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-right">الموقع</TableHead>
                    <TableHead className="text-right">النوع</TableHead>
                    <TableHead className="text-right">شكاوى مفتوحة</TableHead>
                    <TableHead className="text-right">إجمالي الشكاوى</TableHead>
                    <TableHead className="text-right">مهام متأخرة</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.hotspots.map((s: any) => (
                    <TableRow key={s.location_id}>
                      <TableCell>
                        <Link to={`/locations/${s.location_id}`} className="text-primary hover:underline font-medium">
                          {s.location_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {LOCATION_TYPE_LABELS[s.location_type] || s.location_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-red-600 font-bold">{s.open_complaint_count}</TableCell>
                      <TableCell>{s.complaint_count}</TableCell>
                      <TableCell>
                        {s.delayed_task_count > 0 ? (
                          <span className="text-orange-600 font-bold">{s.delayed_task_count}</span>
                        ) : '0'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Most Complaints */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <ChatCircleDots size={20} />
              أكثر المواقع كثافة بالشكاوى
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.most_complaints.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">لا توجد بيانات</p>
            ) : (
              <div className="space-y-3">
                {report.most_complaints.filter((s: any) => s.complaint_count > 0).map((s: any) => (
                  <div key={s.location_id} className="flex items-center gap-3">
                    <Link
                      to={`/locations/${s.location_id}`}
                      className="w-40 text-sm truncate hover:text-primary"
                    >
                      {s.location_name}
                    </Link>
                    <div className="flex-1">
                      <Progress value={(s.complaint_count / maxComplaints) * 100} className="h-3" />
                    </div>
                    <span className="text-sm font-mono w-12 text-left">{s.complaint_count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Most Delayed */}
        {report.most_delayed.length > 0 && (
          <Card className="border-orange-200">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2 text-orange-700">
                <ListChecks size={20} />
                المواقع الأكثر تأخيراً في المهام
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-right">الموقع</TableHead>
                    <TableHead className="text-right">مهام متأخرة</TableHead>
                    <TableHead className="text-right">مهام مفتوحة</TableHead>
                    <TableHead className="text-right">إجمالي المهام</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.most_delayed.map((s: any) => (
                    <TableRow key={s.location_id}>
                      <TableCell>
                        <Link to={`/locations/${s.location_id}`} className="text-primary hover:underline font-medium">
                          {s.location_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-red-600 font-bold">{s.delayed_task_count}</TableCell>
                      <TableCell>{s.open_task_count}</TableCell>
                      <TableCell>{s.task_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Contract Coverage */}
        {report.contract_coverage.length > 0 && (
          <Card className="border-green-200">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2 text-green-700">
                <FileText size={20} />
                التغطية العقدية للمواقع
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-right">الموقع</TableHead>
                    <TableHead className="text-right">عقود نشطة</TableHead>
                    <TableHead className="text-right">إجمالي العقود</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.contract_coverage.map((s: any) => (
                    <TableRow key={s.location_id}>
                      <TableCell>
                        <Link to={`/locations/${s.location_id}`} className="text-primary hover:underline font-medium">
                          {s.location_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-green-600 font-bold">{s.active_contract_count}</TableCell>
                      <TableCell>{s.contract_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
