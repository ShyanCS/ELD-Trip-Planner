import { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import './MapView.css';

// Fix Leaflet default icon path issue with bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

/**
 * MapView — Leaflet map with route polyline and color-coded waypoint markers.
 *
 * Props:
 *   geometry  — GeoJSON LineString geometry (coordinates: [[lon, lat], ...])
 *   waypoints — array of { type, name, lat, lon, miles_from_start }
 */

// ─── Marker Colors ──────────────────────────────────────────────────────────

const MARKER_COLORS = {
  start:   '#22C55E', // green
  pickup:  '#3B82F6', // blue
  dropoff: '#EF4444', // red
  fuel:    '#F59E0B', // amber
  rest:    '#8B5CF6', // purple
};

const MARKER_LABELS = {
  start:   'Start',
  pickup:  'Pickup',
  dropoff: 'Dropoff',
  fuel:    'Fuel Stop',
  rest:    'Rest Stop',
};

const MARKER_ICONS = {
  start:   '🟢',
  pickup:  '📦',
  dropoff: '🏁',
  fuel:    '⛽',
  rest:    '🛌',
};


// ─── Custom SVG Marker Icon ─────────────────────────────────────────────────

function createMarkerIcon(type) {
  const color = MARKER_COLORS[type] || '#6B7280';

  const svg = `
    <svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 0 C6.268 0 0 6.268 0 14 C0 24.5 14 40 14 40 C14 40 28 24.5 28 14 C28 6.268 21.732 0 14 0 Z"
            fill="${color}" stroke="#0e0906" stroke-width="1.5"/>
      <circle cx="14" cy="14" r="7" fill="#0e0906" opacity="0.3"/>
      <circle cx="14" cy="14" r="5" fill="white" opacity="0.9"/>
    </svg>`;

  return L.divIcon({
    html: svg,
    className: 'map-marker-icon',
    iconSize: [28, 40],
    iconAnchor: [14, 40],
    popupAnchor: [0, -40],
  });
}


// ─── Auto-fit bounds helper ─────────────────────────────────────────────────

function FitBounds({ positions }) {
  const map = useMap();

  useEffect(() => {
    if (positions && positions.length > 1) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
    }
  }, [map, positions]);

  return null;
}


// ─── Component ──────────────────────────────────────────────────────────────

export default function MapView({ geometry, waypoints }) {
  // Convert GeoJSON [lon, lat] to Leaflet [lat, lon]
  const routePositions = (geometry?.coordinates || []).map(
    ([lon, lat]) => [lat, lon]
  );

  if (routePositions.length === 0) return null;

  return (
    <div className="map-view" id="map-view">
      <MapContainer
        center={routePositions[0]}
        zoom={5}
        className="map-view__container"
        scrollWheelZoom={true}
        zoomControl={true}
      >
        {/* Dark tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Route polyline */}
        <Polyline
          positions={routePositions}
          pathOptions={{
            color: '#ffb690',
            weight: 3,
            opacity: 0.8,
            dashArray: null,
          }}
        />

        {/* Waypoint markers */}
        {(waypoints || []).map((wp, idx) => (
          <Marker
            key={`${wp.type}-${idx}`}
            position={[wp.lat, wp.lon]}
            icon={createMarkerIcon(wp.type)}
          >
            <Popup className="map-popup">
              <div className="map-popup__content">
                <div className="map-popup__icon">{MARKER_ICONS[wp.type] || '📍'}</div>
                <div className="map-popup__info">
                  <div className="map-popup__type">{MARKER_LABELS[wp.type] || wp.type}</div>
                  <div className="map-popup__name">{wp.name}</div>
                  {wp.miles_from_start != null && (
                    <div className="map-popup__miles">
                      Mile {wp.miles_from_start.toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Auto-fit to route bounds */}
        <FitBounds positions={routePositions} />
      </MapContainer>

      {/* Legend */}
      <div className="map-legend">
        {Object.entries(MARKER_LABELS).map(([type, label]) => (
          <div key={type} className="map-legend__item">
            <span
              className="map-legend__dot"
              style={{ backgroundColor: MARKER_COLORS[type] }}
            />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
