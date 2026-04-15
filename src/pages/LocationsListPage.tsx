import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Spinner, Buildings, MapPin } from '@phosphor-icons/react';

export default function LocationsListPage() {
  const [areas, setAreas] = useState<any[]>([]);
  const [buildings, setBuildings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiService.getAreas(),
      apiService.getBuildings(),
    ])
      .then(([areasData, buildingsData]) => {
        setAreas(areasData);
        setBuildings(Array.isArray(buildingsData) ? buildingsData : []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const areaMap = Object.fromEntries(areas.map((a: any) => [a.id, a.name]));

  const buildingsByArea = areas.map((area: any) => ({
    area,
    buildings: buildings.filter((b: any) => b.area_id === area.id),
  }));

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">المواقع والمناطق</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {areas.map((area: any) => {
            const count = buildings.filter((b: any) => b.area_id === area.id).length;
            return (
              <Card key={area.id}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <MapPin size={20} />
                    {area.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Buildings size={16} />
                    <span>{count} مبنى</span>
                  </div>
                  {area.description && (
                    <p className="text-sm text-muted-foreground mt-2">{area.description}</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
          {areas.length === 0 && (
            <p className="text-muted-foreground col-span-full text-center py-8">لا توجد مناطق</p>
          )}
        </div>

        {buildingsByArea.map(({ area, buildings: areaBuildings }) => (
          areaBuildings.length > 0 && (
            <Card key={area.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Buildings size={20} />
                  مباني منطقة {area.name}
                  <Badge variant="secondary">{areaBuildings.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">اسم المبنى</TableHead>
                      <TableHead className="text-right">الرقم</TableHead>
                      <TableHead className="text-right">النوع</TableHead>
                      <TableHead className="text-right">الطوابق</TableHead>
                      <TableHead className="text-right">الوحدات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {areaBuildings.map((b: any) => (
                      <TableRow key={b.id}>
                        <TableCell>{b.name || '-'}</TableCell>
                        <TableCell className="font-mono">{b.building_number || '-'}</TableCell>
                        <TableCell>{b.type || '-'}</TableCell>
                        <TableCell>{b.floors ?? '-'}</TableCell>
                        <TableCell>{b.units ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )
        ))}

        {buildings.length === 0 && areas.length > 0 && (
          <Card>
            <CardContent className="py-8">
              <p className="text-muted-foreground text-center">لا توجد مباني مسجلة</p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
