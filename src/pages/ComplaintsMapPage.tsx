import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent } from '@/components/ui/card';
import { MapView } from '@/components/MapView';
import type { MapMarker, AreaPolygon } from '@/components/MapView';
import { apiService } from '@/services/api';
import { GeoSubNav } from '@/components/GeoSubNav';
import { MapPin, Funnel } from '@phosphor-icons/react';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

const LAYER_LABELS: Record<string, string> = {
  complaint: 'الشكاوى',
  task: 'المهام',
  project: 'المشاريع',
  location: 'المواقع المرجعية',
};

const STATUS_OPTIONS = [
  { value: '', label: 'جميع الحالات' },
  { value: 'new', label: 'شكوى: جديدة' },
  { value: 'under_review', label: 'شكوى: قيد المراجعة' },
  { value: 'assigned', label: 'شكوى/مهمة: معيّنة' },
  { value: 'in_progress', label: 'قيد التنفيذ' },
  { value: 'resolved', label: 'شكوى: تم الحل' },
  { value: 'pending', label: 'مهمة: معلقة' },
  { value: 'completed', label: 'مهمة: مكتملة' },
  { value: 'planned', label: 'مشروع: مخطط' },
  { value: 'active', label: 'مشروع/موقع: نشط' },
  { value: 'on_hold', label: 'مشروع: متوقف مؤقتاً' },
  { value: 'cancelled', label: 'مشروع: ملغى' },
  { value: 'inactive', label: 'موقع: غير نشط' },
  { value: 'under_construction', label: 'موقع: قيد الإنشاء' },
  { value: 'demolished', label: 'موقع: مهدّم' },
];
const TYPE_OPTIONS = [
  { value: '', label: 'جميع الأنواع' },
  { value: 'complaint', label: 'الشكاوى' },
  { value: 'task', label: 'المهام' },
  { value: 'project', label: 'المشاريع' },
  { value: 'location', label: 'المواقع المرجعية' },
];

function ComplaintsMapPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [itemsWithoutCoordinates, setItemsWithoutCoordinates] = useState<any[]>([]);
  const [polygons, setPolygons] = useState<AreaPolygon[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [layers, setLayers] = useState<Record<string, boolean>>({
    complaint: true,
    task: true,
    project: true,
    location: true,
  });
  const [showZones, setShowZones] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const fetchBoundaries = async () => {
      try {
        const data = await apiService.getAreaBoundaries();
        setPolygons(data);
      } catch {
        setPolygons([]);
      }
    };
    fetchBoundaries();
  }, []);

  useEffect(() => {
    const fetchMarkers = async () => {
      try {
        setLoading(true);
        const params: Record<string, any> = {};
        if (statusFilter) params.status_filter = statusFilter;
        if (entityTypeFilter) params.entity_type = entityTypeFilter;
        const data = await apiService.getOperationsMapMarkers(params);
        const mapped: MapMarker[] = (data.markers || []).map((m: any) => ({
          id: m.id,
          latitude: m.latitude,
          longitude: m.longitude,
          title: m.title || '',
          status: m.status,
          entity_type: m.entity_type,
          reference: m.reference,
          priority: m.priority,
          location_accuracy: m.location_accuracy,
          confidence: m.confidence,
          match_reason: m.match_reason,
        }));
        setMarkers(mapped);
        setItemsWithoutCoordinates(data.items_without_coordinates || []);
      } catch {
        setMarkers([]);
        setItemsWithoutCoordinates([]);
      } finally {
        setLoading(false);
      }
    };
    fetchMarkers();
  }, [statusFilter, entityTypeFilter, refreshKey]);

  const canCorrectLocation = !!role && ['project_director', 'contracts_manager', 'engineer_supervisor', 'complaints_officer', 'area_supervisor'].includes(role);

  const handleManualCorrection = async (item: any) => {
    if (!canCorrectLocation) return;
    const latRaw = window.prompt('أدخل خط العرض (latitude):');
    const lngRaw = window.prompt('أدخل خط الطول (longitude):');
    if (latRaw == null || lngRaw == null) return;
    const latitude = Number(latRaw);
    const longitude = Number(lngRaw);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      toast.error('الإحداثيات غير صالحة');
      return;
    }
    const locationIdRaw = window.prompt('اختياري: أدخل location_id المرجعي إن وجد:');
    const location_id = locationIdRaw && locationIdRaw.trim() ? Number(locationIdRaw) : undefined;
    const payload: any = { latitude, longitude };
    if (location_id && !Number.isNaN(location_id)) payload.location_id = location_id;

    try {
      if (item.entity_type === 'complaint') await apiService.updateComplaint(item.id, payload);
      else if (item.entity_type === 'task') await apiService.updateTask(item.id, payload);
      else if (item.entity_type === 'project') {
        if (!payload.location_id) {
          toast.error('المشروع يتطلب location_id مرجعي للتصحيح اليدوي');
          return;
        }
        await apiService.updateProject(item.id, { location_id: payload.location_id });
      }
      else {
        toast.error('تعديل الموقع للمواقع المرجعية يتم من صفحة المواقع المرجعية');
        return;
      }
      toast.success('تم حفظ الموقع بنجاح');
      setRefreshKey((k) => k + 1);
    } catch {
      toast.error('فشل حفظ الموقع');
    }
  };

  const handleMarkerClick = (marker: MapMarker) => {
    if (marker.entity_type === 'task') {
      navigate(`/tasks/${marker.id}`);
    } else if (marker.entity_type === 'project') {
      navigate(`/projects/${marker.id}`);
    } else if (marker.entity_type === 'location') {
      navigate(`/locations/${marker.id}`);
    } else {
      navigate(`/complaints/${marker.id}`);
    }
  };

  const visibleMarkers = markers.filter((marker) => layers[marker.entity_type || 'complaint']);
  const visibleUnlocated = itemsWithoutCoordinates.filter((item) => layers[item.entity_type]);
  const needsLocationItems = visibleUnlocated.filter((item) => item.needs_location || item.confidence === 'low');
  const unknownItems = visibleUnlocated.filter((item) => !item.needs_location && item.confidence !== 'low');

  const complaintCount = markers.filter((m) => m.entity_type === 'complaint').length;
  const taskCount = markers.filter((m) => m.entity_type === 'task').length;
  const projectCount = markers.filter((m) => m.entity_type === 'project').length;
  const locationCount = markers.filter((m) => m.entity_type === 'location').length;

  return (
    <Layout>
      <div className="space-y-4">
        <GeoSubNav active="map" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <MapPin size={28} className="text-primary" weight="fill" />
            <h1 className="text-xl md:text-2xl font-bold">خريطة العمليات — إدارة التجمع - مشروع دمر</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>{complaintCount} شكوى</span>
            <span className="text-border">|</span>
            <span>{taskCount} مهمة</span>
            <span className="text-border">|</span>
            <span>{projectCount} مشروع</span>
            <span className="text-border">|</span>
            <span>{locationCount} موقع مرجعي</span>
          </div>
        </div>

        <Card>
          <CardContent className="py-3 space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Funnel size={18} className="text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">الطبقات:</span>
              {Object.entries(LAYER_LABELS).map(([key, label]) => (
                <label key={key} className="flex items-center gap-1 text-xs bg-muted px-2.5 py-1 rounded-full">
                  <input
                    type="checkbox"
                    checked={layers[key]}
                    onChange={(e) => setLayers((prev) => ({ ...prev, [key]: e.target.checked }))}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-muted-foreground">الحالة:</span>
              {STATUS_OPTIONS.map((f) => (
                <button
                  key={f.value || 'all'}
                  onClick={() => setStatusFilter(f.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    statusFilter === f.value
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-muted-foreground">النوع:</span>
              {TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value || 'all-types'}
                  onClick={() => setEntityTypeFilter(opt.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    entityTypeFilter === opt.value
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={showZones}
                  onChange={(e) => setShowZones(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-muted-foreground">عرض المناطق</span>
              </label>
            </div>
          </CardContent>
        </Card>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <MapView
            markers={visibleMarkers}
            polygons={showZones ? polygons : []}
            height="calc(100vh - 360px)"
            onMarkerClick={handleMarkerClick}
          />
        )}

        {!loading && visibleMarkers.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center">
              <MapPin size={40} className="mx-auto mb-3 text-muted-foreground" />
              <p className="text-muted-foreground">لا توجد عناصر بإحداثيات جغرافية</p>
              <p className="text-sm text-muted-foreground mt-1">تحقق من فلاتر الطبقات أو أضف إحداثيات للعناصر المرتبطة بالموقع.</p>
            </CardContent>
          </Card>
        )}

        {!loading && (
          <Card>
            <CardContent className="py-4">
              <h2 className="text-base font-semibold mb-3">عناصر تحتاج تحديد موقع</h2>
              {needsLocationItems.length === 0 ? (
                <p className="text-sm text-muted-foreground">لا توجد عناصر منخفضة الثقة تحتاج تحديد موقع يدوي.</p>
              ) : (
                <div className="space-y-2 mb-5">
                  {needsLocationItems.map((item) => (
                    <div key={`${item.entity_type}-${item.id}`} className="border rounded-md px-3 py-2">
                      <button
                        className="w-full text-right hover:text-primary"
                        onClick={() => {
                          if (item.entity_type === 'complaint') navigate(`/complaints/${item.id}`);
                          else if (item.entity_type === 'task') navigate(`/tasks/${item.id}`);
                          else if (item.entity_type === 'project') navigate(`/projects/${item.id}`);
                          else if (item.entity_type === 'location') navigate(`/locations/${item.id}`);
                        }}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-sm">{item.title || `#${item.id}`}</span>
                          <span className="text-xs text-muted-foreground">{LAYER_LABELS[item.entity_type] || item.entity_type}</span>
                        </div>
                      </button>
                      <div className="text-xs text-muted-foreground mt-1">
                        يحتاج تحديد موقع • الثقة: {item.confidence || 'low'}
                      </div>
                      {canCorrectLocation && item.entity_type !== 'location' && (
                        <button
                          className="mt-2 text-xs text-primary hover:underline"
                          onClick={() => handleManualCorrection(item)}
                        >
                          تحديد الموقع على الخريطة
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <h2 className="text-base font-semibold mb-3">عناصر بدون موقع محدد</h2>
              {unknownItems.length === 0 ? (
                <p className="text-sm text-muted-foreground">لا توجد عناصر بدون إحداثيات ضمن الطبقات المحددة.</p>
              ) : (
                <div className="space-y-2">
                  {unknownItems.map((item) => (
                    <button
                      key={`${item.entity_type}-${item.id}`}
                      className="w-full text-right border rounded-md px-3 py-2 hover:bg-muted/50 transition-colors"
                      onClick={() => {
                        if (item.entity_type === 'complaint') navigate(`/complaints/${item.id}`);
                        else if (item.entity_type === 'task') navigate(`/tasks/${item.id}`);
                        else if (item.entity_type === 'project') navigate(`/projects/${item.id}`);
                        else if (item.entity_type === 'location') navigate(`/locations/${item.id}`);
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-sm">{item.title || `#${item.id}`}</span>
                        <span className="text-xs text-muted-foreground">{LAYER_LABELS[item.entity_type] || item.entity_type}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {item.reference ? `مرجع: ${item.reference}` : 'بدون مرجع'} {item.location_text ? `• الموقع: ${item.location_text}` : ''} {item.confidence ? `• الثقة: ${item.confidence}` : ''}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}

export default ComplaintsMapPage;
