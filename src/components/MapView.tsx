import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
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

// Status-based marker colors
const statusColors: Record<string, string> = {
  new: '#EF4444',
  under_review: '#F59E0B',
  assigned: '#3B82F6',
  in_progress: '#8B5CF6',
  resolved: '#10B981',
  rejected: '#6B7280',
};

function createColorIcon(color: string) {
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

export interface MapMarker {
  id: number;
  latitude: number;
  longitude: number;
  title: string;
  description?: string;
  status?: string;
  tracking_number?: string;
}

interface MapViewProps {
  markers: MapMarker[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  onMarkerClick?: (marker: MapMarker) => void;
}

const statusLabels: Record<string, string> = {
  new: 'جديدة',
  under_review: 'قيد المراجعة',
  assigned: 'تم التعيين',
  in_progress: 'قيد التنفيذ',
  resolved: 'تم الحل',
  rejected: 'مرفوضة',
};

export function MapView({ markers, center, zoom = 14, height = '500px', onMarkerClick }: MapViewProps) {
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
        {markers.map((marker) => (
          <Marker
            key={marker.id}
            position={[marker.latitude, marker.longitude]}
            icon={createColorIcon(statusColors[marker.status || ''] || '#3B82F6')}
            eventHandlers={{
              click: () => onMarkerClick?.(marker),
            }}
          >
            <Popup>
              <div className="text-right" dir="rtl" style={{ minWidth: 180 }}>
                <p className="font-bold text-sm mb-1">
                  {marker.tracking_number || `#${marker.id}`}
                </p>
                <p className="text-xs mb-1">{marker.title}</p>
                {marker.status && (
                  <span
                    className="inline-block px-2 py-0.5 rounded text-xs text-white"
                    style={{ background: statusColors[marker.status] || '#6B7280' }}
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
