import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import {
  Spinner, MapPin, WarningCircle, ListChecks, ChatCircleDots, TreeStructure,
} from '@phosphor-icons/react';
import { MapView } from '@/components/MapView';
import type { MapMarker } from '@/components/MapView';
import { GeoSubNav } from '@/components/GeoSubNav';

const TYPE_LABELS: Record<string, string> = {
  island: 'جزيرة', sector: 'قطاع', block: 'بلوك', building: 'مبنى',
  tower: 'برج', street: 'شارع', service_point: 'نقطة خدمة', other: 'أخرى',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'نشط', inactive: 'غير نشط',
  under_construction: 'قيد الإنشاء', demolished: 'مهدّم',
};

export default function GeoDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    apiService.getGeoDashboard()
      .then(setData)
      .catch(() => setError('فشل تحميل لوحة البيانات الجغرافية'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="text-center py-12">
          <WarningCircle size={48} className="mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">{error || 'لا توجد بيانات'}</p>
        </div>
      </Layout>
    );
  }

  const { summary, hotspots, all_locations, recent_complaints, recent_tasks } = data;

  // Build map markers from all locations with coordinates + complaints + tasks
  const locationMarkers: MapMarker[] = (all_locations || [])
    .filter((loc: any) => loc.latitude && loc.longitude)
    .map((loc: any) => ({
      id: loc.id,
      latitude: loc.latitude,
      longitude: loc.longitude,
      title: loc.name,
      description: `${TYPE_LABELS[loc.location_type] || loc.location_type} | شكاوى مفتوحة: ${loc.open_complaints} | مهام: ${loc.open_tasks}`,
      entity_type: 'location' as string,
      reference: loc.code,
      status: loc.is_hotspot ? 'hotspot' : loc.status,
    }));

  const complaintMarkers: MapMarker[] = (recent_complaints || []).map((c: any) => ({
    id: c.id,
    latitude: c.latitude,
    longitude: c.longitude,
    title: c.title,
    tracking_number: c.tracking_number,
    status: c.status,
    entity_type: 'complaint' as string,
    reference: c.tracking_number,
  }));

  const taskMarkers: MapMarker[] = (recent_tasks || []).map((t: any) => ({
    id: t.id,
    latitude: t.latitude,
    longitude: t.longitude,
    title: t.title,
    status: t.status,
    entity_type: 'task' as string,
    reference: t.reference,
  }));

  const allMarkers = [...locationMarkers, ...complaintMarkers, ...taskMarkers];

  return (
    <Layout>
      <div className="space-y-6">
        <GeoSubNav active="geo" />
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TreeStructure size={28} className="text-primary" />
            التحليلات الجغرافية
          </h1>
          <div className="flex gap-2">
            <Link to="/locations">
              <Button variant="outline" size="sm">قائمة المواقع</Button>
            </Link>
            <Link to="/locations/reports">
              <Button variant="outline" size="sm">تقارير المواقع</Button>
            </Link>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-primary">{summary.total_locations}</div>
              <div className="text-xs text-muted-foreground mt-1">إجمالي المواقع</div>
            </CardContent>
          </Card>
          {Object.entries(summary.by_type || {}).slice(0, 4).map(([type, count]) => (
            <Card key={type}>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold">{count as number}</div>
                <div className="text-xs text-muted-foreground mt-1">{TYPE_LABELS[type] || type}</div>
              </CardContent>
            </Card>
          ))}
          <Card>
            <CardContent className="p-4 text-center">
              <div className={`text-2xl font-bold ${hotspots.length > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {hotspots.length}
              </div>
              <div className="text-xs text-muted-foreground mt-1">نقاط ساخنة</div>
            </CardContent>
          </Card>
        </div>

        {/* Main Map */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <MapPin size={18} />
              الخريطة التشغيلية
            </CardTitle>
          </CardHeader>
          <CardContent>
            <MapView
              markers={allMarkers}
              zoom={13}
              height="500px"
            />
            <div className="flex gap-4 mt-3 text-xs text-muted-foreground justify-center flex-wrap">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" />
                موقع
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
                شكوى
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-yellow-500 inline-block" style={{ transform: 'rotate(45deg)' }} />
                مهمة
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Tabs: Hotspots + Status breakdown */}
        <Tabs defaultValue="hotspots">
          <TabsList>
            <TabsTrigger value="hotspots" className="flex items-center gap-1">
              <WarningCircle size={14} />
              نقاط ساخنة
            </TabsTrigger>
            <TabsTrigger value="status" className="flex items-center gap-1">
              <ListChecks size={14} />
              حسب الحالة
            </TabsTrigger>
            <TabsTrigger value="all" className="flex items-center gap-1">
              <MapPin size={14} />
              جميع المواقع
            </TabsTrigger>
          </TabsList>

          {/* Hotspots Tab */}
          <TabsContent value="hotspots">
            <Card>
              <CardContent className="p-0">
                {hotspots.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <WarningCircle size={32} className="mx-auto mb-2 text-green-500" />
                    <p>لا توجد نقاط ساخنة حالياً</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-right">الموقع</TableHead>
                        <TableHead className="text-right">النوع</TableHead>
                        <TableHead className="text-right">شكاوى مفتوحة</TableHead>
                        <TableHead className="text-right">مهام مفتوحة</TableHead>
                        <TableHead className="text-right">مهام متأخرة</TableHead>
                        <TableHead className="text-right">عقود نشطة</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {hotspots.map((hs: any) => (
                        <TableRow key={hs.id}>
                          <TableCell>
                            <Link to={`/locations/${hs.id}`} className="text-primary hover:underline font-medium">
                              {hs.name}
                            </Link>
                            <div className="text-xs text-muted-foreground font-mono">{hs.code}</div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {TYPE_LABELS[hs.location_type] || hs.location_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-red-600 font-bold">{hs.open_complaints}</TableCell>
                          <TableCell>{hs.open_tasks}</TableCell>
                          <TableCell className={hs.delayed_tasks > 0 ? 'text-orange-600 font-bold' : ''}>{hs.delayed_tasks}</TableCell>
                          <TableCell>{hs.active_contracts}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Status breakdown tab */}
          <TabsContent value="status">
            <Card>
              <CardContent className="py-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(summary.by_status || {}).map(([status, count]) => (
                    <div key={status} className="text-center p-4 rounded-lg border">
                      <div className="text-2xl font-bold">{count as number}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {STATUS_LABELS[status] || status}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-6">
                  <h4 className="font-semibold mb-3">توزيع الأنواع</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(summary.by_type || {}).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
                        <span className="text-sm">{TYPE_LABELS[type] || type}</span>
                        <Badge>{count as number}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* All locations tab */}
          <TabsContent value="all">
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">الموقع</TableHead>
                      <TableHead className="text-right">الرمز</TableHead>
                      <TableHead className="text-right">النوع</TableHead>
                      <TableHead className="text-right">الحالة</TableHead>
                      <TableHead className="text-right">شكاوى مفتوحة</TableHead>
                      <TableHead className="text-right">مهام مفتوحة</TableHead>
                      <TableHead className="text-right">متأخرة</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(all_locations || []).map((loc: any) => (
                      <TableRow key={loc.id}>
                        <TableCell>
                          <Link to={`/locations/${loc.id}`} className="text-primary hover:underline font-medium text-sm">
                            {loc.name}
                          </Link>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{loc.code}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {TYPE_LABELS[loc.location_type] || loc.location_type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={
                            loc.status === 'active' ? 'bg-green-100 text-green-800' :
                            loc.status === 'under_construction' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-600'
                          }>
                            {STATUS_LABELS[loc.status] || loc.status}
                          </Badge>
                        </TableCell>
                        <TableCell className={loc.open_complaints >= 5 ? 'text-red-600 font-bold' : ''}>
                          {loc.open_complaints}
                          {loc.is_hotspot && <WarningCircle size={14} className="inline ml-1 text-red-500" />}
                        </TableCell>
                        <TableCell>{loc.open_tasks}</TableCell>
                        <TableCell className={loc.delayed_tasks > 0 ? 'text-orange-600 font-bold' : ''}>
                          {loc.delayed_tasks}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
