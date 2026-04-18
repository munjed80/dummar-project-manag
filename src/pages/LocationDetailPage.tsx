import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import {
  Spinner, MapPin, ChatCircleDots, ListChecks, FileText,
  CaretLeft, ArrowRight, WarningCircle, Clock, TreeStructure, PencilSimple, Plus,
} from '@phosphor-icons/react';
import { MapView } from '@/components/MapView';
import type { MapMarker } from '@/components/MapView';
import { LocationFormDialog } from '@/components/LocationFormDialog';

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

const STATUS_LABELS: Record<string, string> = {
  active: 'نشط',
  inactive: 'غير نشط',
  under_construction: 'قيد الإنشاء',
  demolished: 'مهدّم',
};

const COMPLAINT_STATUS: Record<string, string> = {
  new: 'جديدة',
  under_review: 'قيد المراجعة',
  assigned: 'تم التعيين',
  in_progress: 'قيد التنفيذ',
  resolved: 'تم الحل',
  rejected: 'مرفوضة',
};

const TASK_STATUS: Record<string, string> = {
  pending: 'معلّقة',
  assigned: 'تم التعيين',
  in_progress: 'قيد التنفيذ',
  completed: 'مكتملة',
  cancelled: 'ملغاة',
};

const CONTRACT_STATUS: Record<string, string> = {
  draft: 'مسودة',
  under_review: 'قيد المراجعة',
  approved: 'مُعتمد',
  active: 'نشط',
  suspended: 'مُعلّق',
  completed: 'مكتمل',
  expired: 'منتهي',
  cancelled: 'ملغى',
};

export default function LocationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<any>(null);
  const [complaints, setComplaints] = useState<any>(null);
  const [tasks, setTasks] = useState<any>(null);
  const [contracts, setContracts] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [mapData, setMapData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateChildDialog, setShowCreateChildDialog] = useState(false);

  useEffect(() => {
    if (!id) return;
    loadDetail(parseInt(id));
  }, [id]);

  const loadDetail = async (locationId: number) => {
    setLoading(true);
    try {
      const [detailData, complaintsData, tasksData, contractsData, activityData, mapDataResult] = await Promise.all([
        apiService.getLocationDetail(locationId),
        apiService.getLocationComplaints(locationId),
        apiService.getLocationTasks(locationId),
        apiService.getLocationContracts(locationId),
        apiService.getLocationActivity(locationId),
        apiService.getLocationMapData(locationId).catch(() => null),
      ]);
      setDetail(detailData);
      setComplaints(complaintsData);
      setTasks(tasksData);
      setContracts(contractsData);
      setActivity(activityData);
      setMapData(mapDataResult);
    } catch (err) {
      console.error('Failed to load location:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !detail) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="animate-spin" size={32} />
        </div>
      </Layout>
    );
  }

  const loc = detail.location;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground flex-wrap">
          <Link to="/locations" className="hover:text-primary">المواقع</Link>
          {detail.breadcrumb?.map((b: any) => (
            <span key={b.id} className="flex items-center gap-1">
              <CaretLeft size={12} />
              <Link to={`/locations/${b.id}`} className="hover:text-primary">{b.name}</Link>
            </span>
          ))}
          <CaretLeft size={12} />
          <span className="font-medium text-foreground">{loc.name}</span>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <MapPin size={28} className="text-primary" />
              {loc.name}
            </h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
              <Badge variant="outline">{LOCATION_TYPE_LABELS[loc.location_type] || loc.location_type}</Badge>
              <span className="font-mono">{loc.code}</span>
              <Badge className={loc.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}>
                {STATUS_LABELS[loc.status] || loc.status}
              </Badge>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowCreateChildDialog(true)}>
              <Plus size={14} className="ml-1" />
              إضافة فرعي
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowEditDialog(true)}>
              <PencilSimple size={14} className="ml-1" />
              تعديل
            </Button>
            <Link to="/locations">
              <Button variant="outline" size="sm">العودة للمواقع</Button>
            </Link>
          </div>
        </div>

        {/* Operational Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-lg font-bold">{detail.complaint_count}</div>
              <div className="text-xs text-muted-foreground">إجمالي الشكاوى</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-lg font-bold text-orange-600">{detail.open_complaint_count}</div>
              <div className="text-xs text-muted-foreground">شكاوى مفتوحة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-lg font-bold">{detail.task_count}</div>
              <div className="text-xs text-muted-foreground">إجمالي المهام</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-lg font-bold text-blue-600">{detail.open_task_count}</div>
              <div className="text-xs text-muted-foreground">مهام مفتوحة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className={`text-lg font-bold ${detail.delayed_task_count > 0 ? 'text-red-600' : ''}`}>
                {detail.delayed_task_count}
              </div>
              <div className="text-xs text-muted-foreground">مهام متأخرة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-lg font-bold">{detail.contract_count}</div>
              <div className="text-xs text-muted-foreground">عقود مرتبطة</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-lg font-bold text-green-600">{detail.active_contract_count}</div>
              <div className="text-xs text-muted-foreground">عقود نشطة</div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: Location info + hierarchy */}
          <div className="space-y-4">
            {/* Info Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">معلومات الموقع</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {loc.description && (
                  <div>
                    <div className="text-xs text-muted-foreground">الوصف</div>
                    <div className="text-sm">{loc.description}</div>
                  </div>
                )}
                {(loc.latitude && loc.longitude) && (
                  <div>
                    <div className="text-xs text-muted-foreground">الإحداثيات</div>
                    <div className="text-sm font-mono">{loc.latitude}, {loc.longitude}</div>
                  </div>
                )}
                {detail.parent && (
                  <div>
                    <div className="text-xs text-muted-foreground">الموقع الأب</div>
                    <Link to={`/locations/${detail.parent.id}`} className="text-sm text-primary hover:underline">
                      {detail.parent.name} ({LOCATION_TYPE_LABELS[detail.parent.location_type] || detail.parent.location_type})
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Children */}
            {detail.children?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TreeStructure size={18} />
                    المواقع الفرعية ({detail.children.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {detail.children.map((child: any) => (
                    <Link
                      key={child.id}
                      to={`/locations/${child.id}`}
                      className="flex items-center gap-2 p-2 hover:bg-muted/50 rounded-md transition-colors"
                    >
                      <MapPin size={14} className="text-primary" />
                      <span className="text-sm font-medium flex-1">{child.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {LOCATION_TYPE_LABELS[child.location_type] || child.location_type}
                      </Badge>
                    </Link>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Activity Timeline */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock size={18} />
                  النشاط الأخير
                </CardTitle>
              </CardHeader>
              <CardContent>
                {activity.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">لا يوجد نشاط</p>
                ) : (
                  <div className="space-y-3">
                    {activity.slice(0, 10).map((item: any, idx: number) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <span className="shrink-0 mt-1">
                          {item.type === 'complaint' ? (
                            <ChatCircleDots size={14} className="text-orange-500" />
                          ) : (
                            <ListChecks size={14} className="text-blue-500" />
                          )}
                        </span>
                        <div className="flex-1 min-w-0">
                          <Link
                            to={item.type === 'complaint' ? `/complaints/${item.id}` : `/tasks/${item.id}`}
                            className="hover:text-primary truncate block"
                          >
                            {item.title}
                          </Link>
                          <div className="text-xs text-muted-foreground flex gap-2">
                            <span>{item.reference}</span>
                            <Badge variant="outline" className="text-xs">
                              {item.type === 'complaint'
                                ? (COMPLAINT_STATUS[item.status] || item.status)
                                : (TASK_STATUS[item.status] || item.status)}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right column: Complaints, Tasks, Contracts */}
          <div className="lg:col-span-2">
            <Tabs defaultValue="complaints">
              <TabsList>
                <TabsTrigger value="complaints" className="flex items-center gap-1">
                  <ChatCircleDots size={14} />
                  الشكاوى ({complaints?.total_count || 0})
                </TabsTrigger>
                <TabsTrigger value="tasks" className="flex items-center gap-1">
                  <ListChecks size={14} />
                  المهام ({tasks?.total_count || 0})
                </TabsTrigger>
                <TabsTrigger value="contracts" className="flex items-center gap-1">
                  <FileText size={14} />
                  العقود ({contracts?.total_count || 0})
                </TabsTrigger>
              </TabsList>

              {/* Complaints Tab */}
              <TabsContent value="complaints">
                <Card>
                  <CardContent className="p-0">
                    {!complaints?.items?.length ? (
                      <p className="text-muted-foreground text-center py-8">لا توجد شكاوى مرتبطة</p>
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">رقم التتبع</TableHead>
                            <TableHead className="text-right">مقدم الشكوى</TableHead>
                            <TableHead className="text-right">النوع</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">التاريخ</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {complaints.items.map((c: any) => (
                            <TableRow key={c.id}>
                              <TableCell>
                                <Link to={`/complaints/${c.id}`} className="font-mono text-primary hover:underline text-sm">
                                  {c.tracking_number}
                                </Link>
                              </TableCell>
                              <TableCell className="text-sm">{c.full_name}</TableCell>
                              <TableCell className="text-sm">{c.complaint_type}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="text-xs">
                                  {COMPLAINT_STATUS[c.status] || c.status}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">
                                {c.created_at ? new Date(c.created_at).toLocaleDateString('ar') : '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Tasks Tab */}
              <TabsContent value="tasks">
                <Card>
                  <CardContent className="p-0">
                    {!tasks?.items?.length ? (
                      <p className="text-muted-foreground text-center py-8">لا توجد مهام مرتبطة</p>
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">العنوان</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">الأولوية</TableHead>
                            <TableHead className="text-right">الاستحقاق</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {tasks.items.map((t: any) => (
                            <TableRow key={t.id}>
                              <TableCell>
                                <Link to={`/tasks/${t.id}`} className="text-primary hover:underline text-sm">
                                  {t.title}
                                </Link>
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline" className="text-xs">
                                  {TASK_STATUS[t.status] || t.status}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-sm">{t.priority}</TableCell>
                              <TableCell className="text-xs text-muted-foreground">
                                {t.due_date || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Contracts Tab */}
              <TabsContent value="contracts">
                <Card>
                  <CardContent className="p-0">
                    {!contracts?.items?.length ? (
                      <p className="text-muted-foreground text-center py-8">لا توجد عقود مرتبطة</p>
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-right">رقم العقد</TableHead>
                            <TableHead className="text-right">العنوان</TableHead>
                            <TableHead className="text-right">المقاول</TableHead>
                            <TableHead className="text-right">الحالة</TableHead>
                            <TableHead className="text-right">الانتهاء</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {contracts.items.map((c: any) => (
                            <TableRow key={c.id}>
                              <TableCell>
                                <Link to={`/contracts/${c.id}`} className="font-mono text-primary hover:underline text-sm">
                                  {c.contract_number}
                                </Link>
                              </TableCell>
                              <TableCell className="text-sm">{c.title}</TableCell>
                              <TableCell className="text-sm">{c.contractor_name}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="text-xs">
                                  {CONTRACT_STATUS[c.status] || c.status}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">
                                {c.end_date || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Interactive Map */}
        {(loc.latitude || loc.longitude || (mapData?.complaints?.length > 0) || (mapData?.tasks?.length > 0) || (mapData?.children?.length > 0)) && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MapPin size={18} />
                خريطة الموقع
              </CardTitle>
            </CardHeader>
            <CardContent>
              <MapView
                markers={[
                  // Location point itself
                  ...(loc.latitude && loc.longitude ? [{
                    id: loc.id,
                    latitude: loc.latitude,
                    longitude: loc.longitude,
                    title: loc.name,
                    description: LOCATION_TYPE_LABELS[loc.location_type] || loc.location_type,
                    status: loc.status,
                    entity_type: 'location' as string,
                    reference: loc.code,
                  }] : []),
                  // Child locations
                  ...(mapData?.children || []).map((child: any) => ({
                    id: child.id,
                    latitude: child.latitude,
                    longitude: child.longitude,
                    title: child.name,
                    description: child.code,
                    entity_type: 'location' as string,
                    reference: child.code,
                  })),
                  // Complaints
                  ...(mapData?.complaints || []).map((c: any) => ({
                    id: c.id,
                    latitude: c.latitude,
                    longitude: c.longitude,
                    title: c.title,
                    tracking_number: c.tracking_number,
                    status: c.status,
                    entity_type: 'complaint' as string,
                    reference: c.tracking_number,
                  })),
                  // Tasks
                  ...(mapData?.tasks || []).map((t: any) => ({
                    id: t.id,
                    latitude: t.latitude,
                    longitude: t.longitude,
                    title: t.title,
                    status: t.status,
                    entity_type: 'task' as string,
                    reference: t.reference,
                  })),
                ]}
                center={loc.latitude && loc.longitude ? [loc.latitude, loc.longitude] : undefined}
                zoom={15}
                height="400px"
              />
              <div className="flex gap-4 mt-3 text-xs text-muted-foreground justify-center">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" />
                  الموقع / فرعي
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
        )}

        {/* Edit Dialog */}
        <LocationFormDialog
          open={showEditDialog}
          onOpenChange={setShowEditDialog}
          editData={loc}
          onSuccess={() => loadDetail(parseInt(id!))}
        />

        {/* Create Child Dialog */}
        <LocationFormDialog
          open={showCreateChildDialog}
          onOpenChange={setShowCreateChildDialog}
          parentId={loc.id}
          onSuccess={() => loadDetail(parseInt(id!))}
        />
      </div>
    </Layout>
  );
}
