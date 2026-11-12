import { USE_MOCKS } from '@/lib/api';
import { useMemo, Suspense, lazy } from 'react';
import { useDataStore } from '@/store/data';
import {
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

  // Only cameras with known coordinates are placed (no invented positions). When the API gives none,
  // lib/iasi.ts provides an approximate fallback for the known demo cameras.
  const mapCameras: MapCamera[] = useMemo(
    () =>
      storeCameras
        .filter((cam) => Number.isFinite(cam.lat) && Number.isFinite(cam.lng))
        .map((cam) => {
          const camAlerts = mapAlerts.filter((a) => a.cameraId === cam.id);
          const worst = (['critical', 'high', 'medium', 'info'] as Severity[]).find((sev) => camAlerts.some((a) => a.severity === sev));
          return {
            id: cam.id,
            name: cam.name,
            location: cam.road,
            lat: cam.lat,
            lng: cam.lng,
            status: (cam.status === 'offline' ? 'offline' : 'online') as 'online' | 'offline',
            openAlerts: camAlerts.length,
            worst,
          };
        }),
    [storeCameras, mapAlerts],
  );

  return (
    <div className={`relative w-full h-full overflow-hidden ${className}`}>
      <Suspense
        fallback={
          <div className="w-full h-full flex flex-col items-center justify-center bg-void text-text-secondary gap-2 p-6">
            <Skeleton className="w-full h-full rounded-md bg-panel border border-border" />
          </div>
        }
      >
        <IasiMapLazy
          cameras={bare ? mapCameras.map((c) => ({ ...c, openAlerts: 0, worst: undefined })) : mapCameras}
          patrols={USE_MOCKS ? IASI_PATROLS : []}
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
