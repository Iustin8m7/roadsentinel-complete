import { useState, useEffect } from 'react';
import { MapContainer, Marker, Popup, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { GeoJsonObject } from 'geojson';
import 'leaflet/dist/leaflet.css';
import { IASI_MAP_CONFIG, type MapCamera, type MapPatrol, type MapAlert, type Severity } from '@/lib/iasi';

export interface IasiMapProps {
  cameras: MapCamera[];
  patrols?: MapPatrol[];
  alerts?: MapAlert[];
  focusCameraId?: string;
  onCameraClick?: (id: string) => void;
  onPatrolClick?: (id: string) => void;
  /** Hide zoom buttons (background use). */
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
      )}
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
      </MapContainer>
    </div>
  );
}

export default IasiMap;
