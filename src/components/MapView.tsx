import { MapContainer, TileLayer, Marker, Popup, Polygon, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons in bundled environments
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = defaultIcon;

// ---------------------------------------------------------------------------
// Marker styles by entity type and status
// ---------------------------------------------------------------------------

// Complaint status colors
const complaintStatusColors: Record<string, string> = {
  new: '#EF4444',
  under_review: '#F59E0B',
  assigned: '#3B82F6',
  in_progress: '#8B5CF6',
  resolved: '#10B981',
  rejected: '#6B7280',
};

// Task status colors
const taskStatusColors: Record<string, string> = {
  pending: '#F59E0B',
  assigned: '#3B82F6',
  in_progress: '#8B5CF6',
  completed: '#10B981',
  cancelled: '#6B7280',
};

const projectStatusColors: Record<string, string> = {
  planned: '#F59E0B',
  active: '#10B981',
  on_hold: '#8B5CF6',
  completed: '#3B82F6',
  cancelled: '#6B7280',
};

const locationStatusColors: Record<string, string> = {
  active: '#0EA5E9',
  inactive: '#9CA3AF',
  under_construction: '#F59E0B',
  demolished: '#6B7280',
};

// Entity-type shape markers
function createComplaintIcon(color: string) {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 24px; height: 24px;
      background: ${color};
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  });
}

function createTaskIcon(color: string) {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 22px; height: 22px;
      background: ${color};
      border: 3px solid white;
      border-radius: 4px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      transform: rotate(45deg);
    "></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -14],
  });
}

function createProjectIcon(color: string) {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 0;
      height: 0;
      border-left: 12px solid transparent;
      border-right: 12px solid transparent;
      border-bottom: 22px solid ${color};
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.35));
    "></div>`,
    iconSize: [24, 22],
    iconAnchor: [12, 18],
    popupAnchor: [0, -16],
  });
}

function createLocationIcon(color: string) {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 20px; height: 20px;
      background: ${color};
      border: 2px solid white;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 18],
    popupAnchor: [0, -16],
  });
}

function getMarkerIcon(marker: MapMarker) {
  if (marker.entity_type === 'task') {
    const color = taskStatusColors[marker.status || ''] || '#3B82F6';
    return createTaskIcon(color);
  }
  if (marker.entity_type === 'project') {
    const color = projectStatusColors[marker.status || ''] || '#10B981';
    return createProjectIcon(color);
  }
  if (marker.entity_type === 'location') {
    const color = locationStatusColors[marker.status || ''] || '#0EA5E9';
    return createLocationIcon(color);
  }
  // Default: complaint (circle)
  const color = complaintStatusColors[marker.status || ''] || '#3B82F6';
  return createComplaintIcon(color);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MapMarker {
  id: number;
  latitude: number;
  longitude: number;
  title: string;
  description?: string;
  status?: string;
  tracking_number?: string;
  entity_type?: string; // 'complaint' | 'task' | 'project' | 'location'
  reference?: string;
  priority?: string;
  location_accuracy?: 'exact' | 'estimated';
  confidence?: 'high' | 'medium' | 'low';
  match_reason?: string;
}

export interface AreaPolygon {
  id: number;
  name: string;
  name_ar: string;
  code: string;
  description?: string;
  boundary?: [number, number][];
  color?: string;
}

interface MapViewProps {
  markers: MapMarker[];
  polygons?: AreaPolygon[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  onMarkerClick?: (marker: MapMarker) => void;
  showPolygonLabels?: boolean;
}

// ---------------------------------------------------------------------------
// Status labels
// ---------------------------------------------------------------------------

const statusLabels: Record<string, string> = {
  // Complaints
  new: 'جديدة',
  under_review: 'قيد المراجعة',
  assigned: 'تم التعيين',
  in_progress: 'قيد التنفيذ',
  resolved: 'تم الحل',
  rejected: 'مرفوضة',
  // Tasks
  pending: 'معلقة',
  completed: 'مكتملة',
  cancelled: 'ملغاة',
  // Projects
  planned: 'مخطط',
  active: 'نشط',
  on_hold: 'متوقف مؤقتاً',
  // Locations
  inactive: 'غير نشط',
  under_construction: 'قيد الإنشاء',
  demolished: 'مزال',
};

const entityTypeLabels: Record<string, string> = {
  complaint: 'شكوى',
  task: 'مهمة',
  project: 'مشروع',
  location: 'موقع مرجعي',
};

const locationAccuracyLabels: Record<string, string> = {
  exact: 'موقع دقيق',
  estimated: 'موقع تقديري',
};

const confidenceLabels: Record<string, string> = {
  high: 'مرتفعة',
  medium: 'متوسطة',
  low: 'منخفضة',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MapView({
  markers,
  polygons = [],
  center,
  zoom = 14,
  height = '500px',
  onMarkerClick,
  showPolygonLabels = true,
}: MapViewProps) {
  // Default center: Dummar, Damascus
  const mapCenter = center || [33.5365, 36.2204];

  return (
    <div style={{ height, width: '100%' }} className="rounded-lg overflow-hidden border">
      <MapContainer
        center={mapCenter as [number, number]}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Area polygons */}
        {polygons.map((poly) =>
          poly.boundary && poly.boundary.length > 0 ? (
            <Polygon
              key={`area-${poly.id}`}
              positions={poly.boundary as [number, number][]}
              pathOptions={{
                color: poly.color || '#3B82F6',
                weight: 2,
                opacity: 0.7,
                fillOpacity: 0.12,
              }}
            >
              {showPolygonLabels && (
                <Tooltip
                  permanent
                  direction="center"
                  className="area-label-tooltip"
                >
                  <span style={{ fontSize: 11, fontWeight: 500 }}>
                    {poly.name_ar}
                  </span>
                </Tooltip>
              )}
            </Polygon>
          ) : null
        )}

        {/* Markers */}
        {markers.map((marker) => (
          <Marker
            key={`${marker.entity_type || 'c'}-${marker.id}`}
            position={[marker.latitude, marker.longitude]}
            icon={getMarkerIcon(marker)}
            eventHandlers={{
              click: () => onMarkerClick?.(marker),
            }}
          >
            <Popup>
              <div className="text-right" dir="rtl" style={{ minWidth: 180 }}>
                <p className="font-bold text-sm mb-1">
                  {marker.reference || marker.tracking_number || `#${marker.id}`}
                  {marker.entity_type && (
                    <span className="text-xs text-gray-500 mr-2">
                      ({entityTypeLabels[marker.entity_type] || marker.entity_type})
                    </span>
                  )}
                </p>
                <p className="text-xs mb-1">{marker.title}</p>
                {marker.location_accuracy && (
                  <p className="text-xs mb-1 text-muted-foreground">
                    {locationAccuracyLabels[marker.location_accuracy] || marker.location_accuracy}
                    {marker.confidence ? ` • ثقة: ${confidenceLabels[marker.confidence] || marker.confidence}` : ''}
                  </p>
                )}
                {marker.status && (
                  <span
                    className="inline-block px-2 py-0.5 rounded text-xs text-white"
                    style={{
                      background:
                        marker.entity_type === 'task'
                          ? taskStatusColors[marker.status] || '#6B7280'
                          : marker.entity_type === 'project'
                            ? projectStatusColors[marker.status] || '#6B7280'
                            : marker.entity_type === 'location'
                              ? locationStatusColors[marker.status] || '#6B7280'
                              : complaintStatusColors[marker.status] || '#6B7280',
                    }}
                  >
                    {statusLabels[marker.status] || marker.status}
                  </span>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

export default MapView;
