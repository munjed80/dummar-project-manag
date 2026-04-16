import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent } from '@/components/ui/card';
import { MapView } from '@/components/MapView';
import type { MapMarker, AreaPolygon } from '@/components/MapView';
import { apiService } from '@/services/api';
import { MapPin, Funnel } from '@phosphor-icons/react';

const entityFilters = [
  { value: '', label: 'الكل' },
  { value: 'complaint', label: 'الشكاوى' },
  { value: 'task', label: 'المهام' },
];

const statusFilters = [
  { value: '', label: 'جميع الحالات' },
  { value: 'new', label: 'جديدة' },
  { value: 'under_review', label: 'قيد المراجعة' },
  { value: 'assigned', label: 'تم التعيين' },
  { value: 'in_progress', label: 'قيد التنفيذ' },
  { value: 'resolved', label: 'تم الحل' },
  { value: 'pending', label: 'معلقة' },
  { value: 'completed', label: 'مكتملة' },
];

function ComplaintsMapPage() {
  const navigate = useNavigate();
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [polygons, setPolygons] = useState<AreaPolygon[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [showZones, setShowZones] = useState(true);

  // Load area boundaries once
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

  // Load markers when filters change
  useEffect(() => {
    const fetchMarkers = async () => {
      try {
        setLoading(true);
        const params: Record<string, any> = {};
        if (entityFilter) params.entity_type = entityFilter;
        if (statusFilter) params.status_filter = statusFilter;
        const data = await apiService.getOperationsMapMarkers(params);
        const mapped: MapMarker[] = data
          .filter((m: any) => m.latitude && m.longitude)
          .map((m: any) => ({
            id: m.id,
            latitude: m.latitude,
            longitude: m.longitude,
            title: m.title || '',
            status: m.status,
            entity_type: m.entity_type,
            reference: m.reference,
            priority: m.priority,
          }));
        setMarkers(mapped);
      } catch {
        setMarkers([]);
      } finally {
        setLoading(false);
      }
    };
    fetchMarkers();
  }, [statusFilter, entityFilter]);

  const handleMarkerClick = (marker: MapMarker) => {
    if (marker.entity_type === 'task') {
      navigate(`/tasks/${marker.id}`);
    } else {
      navigate(`/complaints/${marker.id}`);
    }
  };

  const complaintCount = markers.filter((m) => m.entity_type === 'complaint').length;
  const taskCount = markers.filter((m) => m.entity_type === 'task').length;

  return (
    <Layout>
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <MapPin size={28} className="text-primary" weight="fill" />
            <h1 className="text-xl md:text-2xl font-bold">خريطة العمليات — مشروع دمّر</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>{complaintCount} شكوى</span>
            <span className="text-border">|</span>
            <span>{taskCount} مهمة</span>
          </div>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="py-3">
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Entity type filter */}
              <div className="flex items-center gap-2 flex-wrap">
                <Funnel size={18} className="text-muted-foreground" />
                <span className="text-sm font-medium text-muted-foreground">النوع:</span>
                {entityFilters.map((f) => (
                  <button
                    key={f.value}
                    onClick={() => setEntityFilter(f.value)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      entityFilter === f.value
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Status filter */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-muted-foreground">الحالة:</span>
                {statusFilters.map((f) => (
                  <button
                    key={f.value}
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

              {/* Zone overlay toggle */}
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
            </div>
          </CardContent>
        </Card>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-medium text-muted-foreground">شكاوى:</span>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full" style={{ background: '#EF4444' }} />
              <span className="text-muted-foreground">جديدة</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full" style={{ background: '#F59E0B' }} />
              <span className="text-muted-foreground">مراجعة</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full" style={{ background: '#8B5CF6' }} />
              <span className="text-muted-foreground">تنفيذ</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full" style={{ background: '#10B981' }} />
              <span className="text-muted-foreground">تم الحل</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-muted-foreground">مهام:</span>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded" style={{ background: '#F59E0B', transform: 'rotate(45deg)' }} />
              <span className="text-muted-foreground">معلقة</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded" style={{ background: '#3B82F6', transform: 'rotate(45deg)' }} />
              <span className="text-muted-foreground">معيّنة</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded" style={{ background: '#10B981', transform: 'rotate(45deg)' }} />
              <span className="text-muted-foreground">مكتملة</span>
            </div>
          </div>
        </div>

        {/* Map */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <MapView
            markers={markers}
            polygons={showZones ? polygons : []}
            height="calc(100vh - 350px)"
            onMarkerClick={handleMarkerClick}
          />
        )}

        {!loading && markers.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center">
              <MapPin size={40} className="mx-auto mb-3 text-muted-foreground" />
              <p className="text-muted-foreground">لا توجد عناصر بإحداثيات جغرافية</p>
              <p className="text-sm text-muted-foreground mt-1">يجب إضافة الإحداثيات عند تقديم الشكوى أو إنشاء المهمة لعرضها على الخريطة</p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}

export default ComplaintsMapPage;
