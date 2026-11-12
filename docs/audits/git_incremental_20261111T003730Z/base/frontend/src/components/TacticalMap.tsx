import { useMemo, Suspense, lazy } from 'react';
import { useDataStore } from '@/store/data';
import {
  IASI_CAMERAS,
  IASI_PATROLS,
  type MapCamera,
  type MapAlert,
  type Severity,
} from '@/lib/iasi';
import { Skeleton } from '@/components/ui';

// Lazy load IasiMap to keep initial bundle light
const IasiMapLazy = lazy(() => import('./IasiMap'));

export interface TacticalMapProps {
  className?: string;
  /** Hide the map label and zoom buttons (background use). */
  bare?: boolean;
  focusCameraId?: string;
  onCameraClick?: (id: string) => void;
  onPatrolClick?: (id: string) => void;
  criticalAlertLocation?: string;
}

export function TacticalMap({
  className = '',
  bare,
  focusCameraId,
  onCameraClick,
  onPatrolClick,
}: TacticalMapProps) {
  const storeCameras = useDataStore((s) => s.cameras);
  const alerts = useDataStore((s) => s.alerts);

  // Map alerts from store queue
  const mapAlerts: MapAlert[] = useMemo(() => {
    return alerts
      .filter((a) => a.status === 'new' || a.status === 'in_review')
      .map((a) => ({
        id: a.id,
        cameraId: a.cameraId,
        severity: a.severity as Severity,
        label: a.ruleSummary || `${a.type.toUpperCase()}`,
      }));
  }, [alerts]);

  // Merge store cameras with GPS coordinates and active alerts
  const mapCameras: MapCamera[] = useMemo(() => {
    // If storeCameras is empty (e.g. initial load before API returns), use IASI_CAMERAS defaults
    const sourceList =
      storeCameras && storeCameras.length > 0
        ? storeCameras
        : Object.entries(IASI_CAMERAS).map(([id, def]) => ({
            id,
            name: def.name,
            road: def.location,
            status: 'online' as const,
          }));

    return sourceList.map((cam, idx) => {
      // Find matching GPS coords by id or fallback by index
      const fallbackKeys = Object.keys(IASI_CAMERAS);
      const matchedDefault = IASI_CAMERAS[cam.id] || IASI_CAMERAS[fallbackKeys[idx % fallbackKeys.length]];
      const matchedGps = matchedDefault;
      const fallbackLocation = matchedDefault?.location || 'Iași';

      // Calculate open alerts on this camera
      const camAlerts = mapAlerts.filter((a) => a.cameraId === cam.id);
      const openAlertsCount = camAlerts.length;

      let worst: Severity | undefined;
      if (camAlerts.some((a) => a.severity === 'critical')) worst = 'critical';
      else if (camAlerts.some((a) => a.severity === 'high')) worst = 'high';
      else if (camAlerts.some((a) => a.severity === 'medium')) worst = 'medium';
      else if (camAlerts.some((a) => a.severity === 'info')) worst = 'info';

      return {
        id: cam.id,
        name: cam.name,
        location: cam.road || fallbackLocation,
        lat: matchedGps ? matchedGps.lat : 47.1585 + (idx * 0.005),
        lng: matchedGps ? matchedGps.lng : 27.6014 + (idx * 0.005),
        status: (cam.status === 'offline' ? 'offline' : 'online') as 'online' | 'offline',
        openAlerts: openAlertsCount,
        worst,
      };
    });
  }, [storeCameras, mapAlerts]);

  return (
    <div className={`relative w-full h-full overflow-hidden ${className}`}>
      <Suspense
        fallback={
          <div className="w-full h-full flex flex-col items-center justify-center bg-[#0A0E14] text-[#7D8A9B] gap-2 p-6">
            <Skeleton className="w-full h-full rounded-md bg-[#111821] border border-[#1E2A36]" />
          </div>
        }
      >
        <IasiMapLazy
          cameras={bare ? mapCameras.map((c) => ({ ...c, openAlerts: 0, worst: undefined })) : mapCameras}
          patrols={IASI_PATROLS}
          alerts={bare ? [] : mapAlerts}
          focusCameraId={focusCameraId}
          onCameraClick={onCameraClick}
          onPatrolClick={onPatrolClick}
          bare={bare}
          className="w-full h-full"
        />
      </Suspense>
    </div>
  );
}

export default TacticalMap;
export { IasiMapLazy as IasiMap };
export type { IasiMapProps } from './IasiMap';
