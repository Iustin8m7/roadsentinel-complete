import { useState, useEffect, memo } from 'react';
import type { GeoJsonObject } from 'geojson';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Video } from 'lucide-react';
import {
  IASI_MAP_CONFIG,
  type MapCamera,
  type MapPatrol,
  type MapAlert,
  type Severity,
} from '@/lib/iasi';

export interface IasiMapProps {
  cameras: MapCamera[];
  patrols?: MapPatrol[];
  alerts?: MapAlert[];
  focusCameraId?: string;
  onCameraClick?: (id: string) => void;
  onPatrolClick?: (id: string) => void;
  /** Hide the overlay label and zoom buttons (background use). */
  bare?: boolean;
  className?: string;
}

// Map controller: keeps the size in sync with the container and flies to the focused camera
function MapController({ focusCamera }: { focusCamera?: MapCamera }) {
  const map = useMap();

  useEffect(() => {
    // Invalidate size on mount & resize
    const container = map.getContainer();
    const observer = new ResizeObserver(() => {
      map.invalidateSize();
    });
    observer.observe(container);

    return () => observer.disconnect();
  }, [map]);

  // Smooth fly-to on focused camera change
  useEffect(() => {
    if (focusCamera) {
      map.flyTo([focusCamera.lat, focusCamera.lng], 15, {
        duration: 1.2,
      });
    }
  }, [focusCamera, map]);

  return null;
}

// Icon generator for cameras
const createCameraIcon = (camera: MapCamera, isWorstAlert: boolean, alertLabel?: string) => {
  const borderColor =
    camera.status === 'offline'
      ? '#536070'
      : camera.worst === 'critical'
      ? '#FF3B3B'
      : camera.worst === 'high'
      ? '#FF8A1F'
      : camera.worst === 'medium'
      ? '#FFC23D'
      : '#3DA5FF';

  const pulseRingsHtml = isWorstAlert
    ? `
      <div class="iasi-pulse-ring iasi-ring-1"></div>
      <div class="iasi-pulse-ring iasi-ring-2"></div>
      <div class="iasi-pulse-ring iasi-ring-3"></div>
      ${alertLabel ? `<div class="iasi-pulse-label font-mono">${alertLabel}</div>` : ''}
    `
    : '';

  const badgeHtml =
    camera.openAlerts > 0
      ? `<div class="iasi-camera-badge font-mono" style="background-color: ${borderColor};">${camera.openAlerts}</div>`
      : '';

  return L.divIcon({
    className: 'iasi-custom-marker',
    html: `
      <div class="iasi-marker-wrapper group">
        ${pulseRingsHtml}
        <div class="iasi-camera-circle" style="border-color: ${borderColor}; box-shadow: 0 0 12px ${borderColor}66;">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${borderColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="m22 8-6 4 6 4V8Z"/>
            <rect width="14" height="12" x="2" y="6" rx="2" ry="2"/>
          </svg>
        </div>
        ${badgeHtml}
        <div class="iasi-camera-tooltip font-mono">${camera.name}</div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
};

// Icon generator for patrols
const createPatrolIcon = (patrol: MapPatrol) => {
  const color =
    patrol.status === 'available'
      ? '#2ED47A'
      : patrol.status === 'busy'
      ? '#FF8A1F'
      : '#7D8A9B';

  const label = patrol.status === 'available' ? 'DISP' : patrol.status === 'busy' ? 'MISIUNE' : 'PAUZĂ';

  return L.divIcon({
    className: 'iasi-custom-patrol-marker',
    html: `
      <div class="iasi-patrol-badge font-mono" style="border-color: ${color}66; box-shadow: 0 0 12px ${color}33;">
        <span class="iasi-patrol-dot" style="background-color: ${color};"></span>
        <span class="iasi-patrol-callsign font-bold text-[#E6EDF3]">${patrol.callsign}</span>
        <span class="iasi-patrol-pill" style="color: ${color}; background-color: ${color}1A;">${label}</span>
      </div>
    `,
    iconSize: [115, 26],
    iconAnchor: [57, 13],
  });
};

export function IasiMap({
  cameras,
  patrols = [],
  alerts = [],
  focusCameraId,
  onCameraClick,
  onPatrolClick,
  bare = false,
  className = '',
}: IasiMapProps) {
  const [geoJsonData, setGeoJsonData] = useState<GeoJsonObject | null>(null);

  // Load static GeoJSON once
  useEffect(() => {
    fetch('/geo/iasi-roads.geojson')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setGeoJsonData(data);
      })
      .catch(() => {
        // Fallback silently if offline or not yet placed
      });
  }, []);

  // Determine which camera has the most severe open alert
  const worstSeverityOrder: Record<Severity, number> = {
    critical: 4,
    high: 3,
    medium: 2,
    info: 1,
  };

  let topAlert: MapAlert | undefined;
  if (alerts && alerts.length > 0) {
    topAlert = [...alerts].sort(
      (a, b) => (worstSeverityOrder[b.severity] || 0) - (worstSeverityOrder[a.severity] || 0)
    )[0];
  }

  const focusedCamera = cameras.find((c) => c.id === focusCameraId);

  return (
    <div className={`relative w-full h-full overflow-hidden bg-[#0A0E14] select-none ${className}`}>
      {/* Top Map Bar / Quick Tools */}
      <div className={`absolute top-3 left-3 z-[1000] flex items-center gap-2 ${bare ? 'hidden' : ''}`}>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#111821]/90 border border-[#1E2A36] backdrop-blur-md text-xs font-mono text-[#E6EDF3] shadow-lg">
          <span className="w-2 h-2 rounded-full bg-[#2ED47A] shadow-[0_0_8px_#2ED47A]" />
          <span className="font-heading font-bold text-sm uppercase tracking-wider">HARTA TACTICĂ IAȘI</span>
          <span className="text-[#7D8A9B] text-[10px]">WGS84</span>
        </div>

      </div>

      {/* Leaflet Map Container */}
      <MapContainer
        center={bare ? [47.1625, 27.5885] : IASI_MAP_CONFIG.center}
        zoom={bare ? 14 : IASI_MAP_CONFIG.defaultZoom}
        zoomControl={!bare}
        minZoom={IASI_MAP_CONFIG.minZoom}
        maxZoom={IASI_MAP_CONFIG.maxZoom}
        maxBounds={IASI_MAP_CONFIG.maxBounds}
        scrollWheelZoom={false}
        attributionControl={true}
        className="w-full h-full z-0 font-sans"
      >
        <MapController focusCamera={focusedCamera} />

        {/* OpenStreetMap tiles (free, no key), darkened in CSS via .rs-dark-tiles.
            OSM's tile policy needs a Referer, while the gateway sends no-referrer by default. */}
        <TileLayer
          url={IASI_MAP_CONFIG.tileUrl}
          attribution={IASI_MAP_CONFIG.attribution}
          className="rs-dark-tiles"
          referrerPolicy="strict-origin-when-cross-origin"
          maxZoom={19}
        />

        {/* Static GeoJSON Overlay for Main Arteries */}
        {geoJsonData && (
          <GeoJSON
            data={geoJsonData}
            style={() => ({
              color: '#2D445D',
              weight: 2.5,
              opacity: 0.85,
              dashArray: '4, 4',
            })}
          />
        )}

        {/* Patrol Markers */}
        {patrols.map((patrol) => (
          <Marker
            key={`patrol-${patrol.id}`}
            position={[patrol.lat, patrol.lng]}
            icon={createPatrolIcon(patrol)}
            eventHandlers={{ click: () => onPatrolClick?.(patrol.id) }}
          >
            <Popup className="iasi-custom-popup">
              <div className="p-3 bg-[#111821] text-[#E6EDF3] rounded-md border border-[#1E2A36] text-xs font-sans min-w-[180px]">
                <div className="flex items-center justify-between pb-1.5 border-b border-[#1E2A36] mb-2 font-mono">
                  <span className="font-bold text-[#3DA5FF]">{patrol.callsign}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    patrol.status === 'available'
                      ? 'text-[#2ED47A] bg-[#2ED47A]/15'
                      : patrol.status === 'busy'
                      ? 'text-[#FF8A1F] bg-[#FF8A1F]/15'
                      : 'text-[#7D8A9B] bg-[#7D8A9B]/15'
                  }`}>
                    {patrol.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-[11px] text-[#7D8A9B] mb-2">
                  Zonă: <strong className="text-[#E6EDF3]">{patrol.area || 'Centru'}</strong>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Camera Markers */}
        {cameras.map((camera) => {
          const isTopAlertCamera = topAlert && topAlert.cameraId === camera.id;
          const alertLabel = isTopAlertCamera && topAlert ? topAlert.label : undefined;

          return (
            <Marker
              key={`camera-${camera.id}`}
              position={[camera.lat, camera.lng]}
              icon={createCameraIcon(camera, Boolean(isTopAlertCamera), alertLabel)}
            >
              <Popup className="iasi-custom-popup">
                <div className="p-3 bg-[#111821] text-[#E6EDF3] rounded-md border border-[#1E2A36] text-xs font-sans min-w-[210px] shadow-2xl">
                  {/* Camera Header */}
                  <div className="flex items-center justify-between pb-1.5 border-b border-[#1E2A36] mb-2">
                    <div className="flex items-center gap-1.5">
                      <Video className="w-3.5 h-3.5 text-[#3DA5FF]" />
                      <span className="font-heading font-bold text-sm uppercase tracking-wide">
                        {camera.name}
                      </span>
                    </div>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        camera.status === 'online'
                          ? 'text-[#2ED47A] bg-[#2ED47A]/15'
                          : 'text-[#FF3B3B] bg-[#FF3B3B]/15'
                      }`}
                    >
                      {camera.status === 'online' ? 'Online' : 'Fără semnal'}
                    </span>
                  </div>

                  {/* Location & Details */}
                  <div className="text-[11px] text-[#7D8A9B] mb-2.5">
                    {camera.location}
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono mb-3 bg-[#17202B] p-1.5 rounded border border-[#1E2A36]">
                    <span className="text-[#7D8A9B]">Alerte active:</span>
                    <span
                      className={`font-bold ${
                        camera.openAlerts > 0 ? 'text-[#FF8A1F]' : 'text-[#7D8A9B]'
                      }`}
                    >
                      {camera.openAlerts} {camera.openAlerts === 1 ? 'alertă' : 'alerte'}
                    </span>
                  </div>

                  {onCameraClick && (
                    <button
                      type="button"
                      onClick={() => onCameraClick(camera.id)}
                      className="w-full py-1.5 px-2 bg-[#3DA5FF] hover:bg-[#3DA5FF]/90 text-white text-[11px] font-medium rounded text-center transition-colors"
                    >
                      Redă clipuri
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

export default memo(IasiMap);
