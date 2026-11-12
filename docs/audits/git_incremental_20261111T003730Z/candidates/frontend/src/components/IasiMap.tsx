import { useState, useEffect } from 'react';
import { MapContainer, Marker, Popup, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { GeoJsonObject } from 'geojson';
import 'leaflet/dist/leaflet.css';
<<<<<<< INTEGRATION
import { IASI_MAP_CONFIG, type MapCamera, type MapPatrol, type MapAlert, type Severity } from '@/lib/iasi';
=======
import { Video } from 'lucide-react';
import {
  DEMO_LEGEND,
  IASI_MAP_CONFIG,
  isDemoCamera,
  type MapCamera,
  type MapAlert,
  type Severity,
} from '@/lib/iasi';
>>>>>>> GITHUB_TARGET

export interface IasiMapProps {
  cameras: MapCamera[];
  alerts?: MapAlert[];
  focusCameraId?: string;
  onCameraClick?: (id: string) => void;
<<<<<<< INTEGRATION
  onPatrolClick?: (id: string) => void;
  /** Hide zoom buttons (background use). */
=======
  /** Hide the overlay label and zoom buttons (background use). */
>>>>>>> GITHUB_TARGET
  bare?: boolean;
  className?: string;
}

const SEV_LABEL: Record<Severity, string> = { critical: 'critică', high: 'ridicată', medium: 'medie', info: 'informativă' };

function MapController({ focusCamera }: { focusCamera?: MapCamera }) {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  useEffect(() => {
    if (focusCamera) map.flyTo([focusCamera.lat, focusCamera.lng], 15, { duration: 1.2 });
  }, [focusCamera, map]);
  return null;
}

<<<<<<< INTEGRATION
/** Marker DOM built with textContent/classList only: names from the API can never inject markup. */
function cameraIcon(camera: MapCamera) {
  const root = document.createElement('div');
  const level = camera.status === 'offline' ? 'offline' : `sev-${camera.worst ?? 'info'}`;
  root.className = `rs-marker ${level}`;
  const shape = document.createElement('span');
  shape.className = 'rs-marker-shape';
  root.appendChild(shape);
  if (camera.openAlerts > 0) {
    const count = document.createElement('span');
    count.className = 'rs-marker-count';
    count.textContent = String(camera.openAlerts);
    root.appendChild(count);
  }
  return L.divIcon({ className: '', html: root, iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -16] });
}

function cameraTitle(c: MapCamera) {
  const state = c.status === 'offline' ? 'fără semnal' : 'activă';
  const alerts = c.openAlerts > 0 ? `, ${c.openAlerts} ${c.openAlerts === 1 ? 'alertă' : 'alerte'} de verificat${c.worst ? ` (cea mai gravă: ${SEV_LABEL[c.worst]})` : ''}` : '';
  return `${c.name}: ${state}${alerts}`;
}

export function IasiMap({ cameras, focusCameraId, onCameraClick, bare = false, className = '' }: IasiMapProps) {
  const [roads, setRoads] = useState<GeoJsonObject | null>(null);
=======
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

export function IasiMap({
  cameras,
  alerts = [],
  focusCameraId,
  onCameraClick,
  bare = false,
  className = '',
}: IasiMapProps) {
  const [geoJsonData, setGeoJsonData] = useState<GeoJsonObject | null>(null);
>>>>>>> GITHUB_TARGET

  useEffect(() => {
    fetch('/geo/iasi-roads.geojson')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data) setRoads(data); })
      .catch(() => { /* the map still works without the schematic roads */ });
  }, []);

  const focused = cameras.find((c) => c.id === focusCameraId);

  return (
    <div className={`relative w-full h-full overflow-hidden bg-void rs-map ${className}`}>
      {!bare && (
        <div className="absolute top-3 left-3 z-[1000] px-3 py-1.5 rounded-md bg-panel/90 border border-border text-xs text-text-secondary">
          Hartă schematică, fără fundal de hartă
        </div>
<<<<<<< INTEGRATION
      )}
=======

      </div>

      {/* Legend: most markers are stock footage placed on the map for illustration */}
      {!bare && cameras.some((c) => isDemoCamera(c.id)) && (
        <div className="absolute bottom-3 left-3 z-[1000] px-2.5 py-1 rounded-md bg-[#111821]/90 border border-[#FFC23D]/40 text-[11px] text-[#E6EDF3] shadow-lg" data-testid="map-demo-legend">
          <span className="font-bold text-[#FFC23D]">DEMO</span> · {DEMO_LEGEND}
        </div>
      )}

      {/* Leaflet Map Container */}
>>>>>>> GITHUB_TARGET
      <MapContainer
        center={bare ? [47.1625, 27.5885] : IASI_MAP_CONFIG.center}
        zoom={bare ? 14 : IASI_MAP_CONFIG.defaultZoom}
        zoomControl={!bare}
        minZoom={IASI_MAP_CONFIG.minZoom}
        maxZoom={IASI_MAP_CONFIG.maxZoom}
        maxBounds={IASI_MAP_CONFIG.maxBounds}
        scrollWheelZoom={false}
        attributionControl={false}
        className="w-full h-full z-0"
      >
<<<<<<< INTEGRATION
        <MapController focusCamera={focused} />
        {roads && <GeoJSON data={roads} style={() => ({ className: 'rs-road', weight: 2.5 })} />}
        {cameras.map((camera) => (
          <Marker key={camera.id} position={[camera.lat, camera.lng]} icon={cameraIcon(camera)} title={cameraTitle(camera)} alt={cameraTitle(camera)}>
            <Popup>
              <div className="p-3 text-sm min-w-[200px] flex flex-col gap-1.5">
                <div className="font-semibold">{camera.name}</div>
                {camera.location && <div className="text-text-secondary">{camera.location}</div>}
                <div>{camera.status === 'offline' ? 'Fără semnal' : 'Activă'} · {camera.openAlerts} {camera.openAlerts === 1 ? 'alertă' : 'alerte'} de verificat</div>
                {onCameraClick && (
                  <button type="button" onClick={() => onCameraClick(camera.id)}
                    className="mt-1 px-3 min-h-[var(--target-min)] rounded-md bg-accent text-on-accent text-sm font-medium cursor-pointer">
                    Redă clipuri
                  </button>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
=======
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
                    {isDemoCamera(camera.id) && (
                      <div className="mt-1 text-[#FFC23D]">Filmare demonstrativă de arhivă, nu o cameră din Iași.</div>
                    )}
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
>>>>>>> GITHUB_TARGET
      </MapContainer>
    </div>
  );
}

export default IasiMap;
