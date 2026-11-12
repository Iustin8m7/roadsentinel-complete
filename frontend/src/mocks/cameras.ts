import type { Camera } from '@/types'

const UNIT = 'Brigada Rutieră București'

export const CAMERAS: Camera[] = [
  { id: 'CAM-A1-023', name: 'A1 km 23 — Bolintin', road: 'A1', direction: 'spre Pitești', lat: 44.4421, lng: 25.8012, status: 'online', fps: 25, calibrated: true, unit: UNIT },
  { id: 'CAM-A2-012', name: 'A2 km 12 — Glina', road: 'A2', direction: 'spre Constanța', lat: 44.3925, lng: 26.2601, status: 'online', fps: 25, calibrated: true, unit: UNIT },
  { id: 'CAM-A3-004', name: 'A3 km 4 — Ștefăneștii de Jos', road: 'A3', direction: 'spre Ploiești', lat: 44.5541, lng: 26.1803, status: 'online', fps: 30, calibrated: true, unit: UNIT },
  { id: 'CAM-DN1-OTP', name: 'DN1 — Aeroport Otopeni', road: 'DN1', direction: 'spre Ploiești', lat: 44.5672, lng: 26.0853, status: 'online', fps: 25, calibrated: true, unit: UNIT },
  { id: 'CAM-DN7-CHT', name: 'DN7 — Chitila', road: 'DN7', direction: 'spre București', lat: 44.5065, lng: 25.9771, status: 'degraded', fps: 12, calibrated: false, unit: UNIT },
  { id: 'CAM-CB-CHJ', name: 'Centura — Chiajna', road: 'Centura București', direction: 'sens nord', lat: 44.4573, lng: 25.9705, status: 'online', fps: 25, calibrated: true, unit: UNIT },
  { id: 'CAM-BIM-01', name: 'Bd. Iuliu Maniu — Lujerului', road: 'Bd. Iuliu Maniu', direction: 'spre centru', lat: 44.4335, lng: 26.0346, status: 'online', fps: 30, calibrated: true, unit: UNIT },
  { id: 'CAM-BUN-02', name: 'Bd. Unirii — Piața Alba Iulia', road: 'Bd. Unirii', direction: 'spre Piața Unirii', lat: 44.4271, lng: 26.1196, status: 'online', fps: 30, calibrated: true, unit: UNIT },
  { id: 'CAM-PV-03', name: 'Piața Victoriei', road: 'Piața Victoriei', direction: 'intersecție', lat: 44.4522, lng: 26.0857, status: 'offline', fps: 0, calibrated: true, unit: UNIT },
  { id: 'CAM-PIP-04', name: 'Șos. Pipera — Petricani', road: 'Șos. Pipera', direction: 'spre Voluntari', lat: 44.4844, lng: 26.1239, status: 'online', fps: 25, calibrated: true, unit: UNIT },
]

export const cameraById = (id: string) => CAMERAS.find((c) => c.id === id)
