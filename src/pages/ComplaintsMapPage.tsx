import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MapView } from '@/components/MapView';
import type { MapMarker } from '@/components/MapView';
import { apiService } from '@/services/api';
import { MapPin, Funnel } from '@phosphor-icons/react';

const statusFilters = [
  { value: '', label: 'جميع الحالات' },
  { value: 'new', label: 'جديدة' },
  { value: 'under_review', label: 'قيد المراجعة' },
  { value: 'assigned', label: 'تم التعيين' },
  { value: 'in_progress', label: 'قيد التنفيذ' },
  { value: 'resolved', label: 'تم الحل' },
  { value: 'rejected', label: 'مرفوضة' },
];

const statusColors: Record<string, string> = {
  new: '#EF4444',
  under_review: '#F59E0B',
  assigned: '#3B82F6',
  in_progress: '#8B5CF6',
  resolved: '#10B981',
  rejected: '#6B7280',
};

function ComplaintsMapPage() {
  const navigate = useNavigate();
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    const fetchMarkers = async () => {
      try {
        setLoading(true);
        const params: Record<string, any> = {};
        if (statusFilter) params.status_filter = statusFilter;
        const data = await apiService.getComplaintsMapMarkers(params);
        const mapped: MapMarker[] = data
          .filter((c: any) => c.latitude && c.longitude)
          .map((c: any) => ({
            id: c.id,
            latitude: c.latitude,
            longitude: c.longitude,
            title: c.description?.substring(0, 80) || 'شكوى',
            description: c.description,
            status: c.status,
            tracking_number: c.tracking_number,
          }));
        setMarkers(mapped);
      } catch {
        setMarkers([]);
      } finally {
        setLoading(false);
      }
    };
    fetchMarkers();
  }, [statusFilter]);

  const handleMarkerClick = (marker: MapMarker) => {
    navigate(`/complaints/${marker.id}`);
  };

  return (
    <Layout>
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <MapPin size={28} className="text-primary" weight="fill" />
            <h1 className="text-2xl font-bold">خريطة الشكاوى — مشروع دمّر</h1>
          </div>
          <span className="text-sm text-muted-foreground">
            {markers.length} شكوى على الخريطة
          </span>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Funnel size={18} className="text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground ml-1">تصفية:</span>
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
                  {f.value && (
                    <span
                      className="inline-block w-2 h-2 rounded-full ml-1"
                      style={{ background: statusColors[f.value] || '#6B7280' }}
                    />
                  )}
                  {f.label}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 text-xs">
          {statusFilters.filter((f) => f.value).map((f) => (
            <div key={f.value} className="flex items-center gap-1">
              <span
                className="w-3 h-3 rounded-full border border-white shadow-sm"
                style={{ background: statusColors[f.value] }}
              />
              <span className="text-muted-foreground">{f.label}</span>
            </div>
          ))}
        </div>

        {/* Map */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <MapView
            markers={markers}
            height="600px"
            onMarkerClick={handleMarkerClick}
          />
        )}

        {!loading && markers.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center">
              <MapPin size={40} className="mx-auto mb-3 text-muted-foreground" />
              <p className="text-muted-foreground">لا توجد شكاوى بإحداثيات جغرافية</p>
              <p className="text-sm text-muted-foreground mt-1">يجب إضافة الإحداثيات عند تقديم الشكوى لعرضها على الخريطة</p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}

export default ComplaintsMapPage;
