import type { Patrol, Rule } from '@/types'

const UNIT = 'Brigada Rutieră București'
const at = new Date(Date.now() - 3 * 864e5).toISOString()

export const RULES: Rule[] = [
  { id: 'R-001', name: 'Sens interzis pe autostradă', alertType: 'wrong_way', zone: { name: 'Carosabil A1/A2/A3', kind: 'highway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-A3-004'], thresholds: {}, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-002', name: 'Pieton în zona autostrăzii', alertType: 'pedestrian_highway', zone: { name: 'Carosabil + acostament', kind: 'highway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-A3-004'], thresholds: { dwellSec: 2 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-003', name: 'Accident probabil (oprire bruscă multiplă)', alertType: 'probable_crash', zone: { name: 'Toate benzile', kind: 'roadway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-CB-CHJ', 'CAM-BIM-01', 'CAM-BUN-02'], thresholds: { decelMs2: 9 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-004', name: 'Obiect static pe carosabil', alertType: 'road_object', zone: { name: 'Benzi de circulație', kind: 'roadway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-A3-004', 'CAM-DN1-OTP'], thresholds: { dwellSec: 20 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-005', name: 'Viteză foarte mare — autostradă', alertType: 'high_speed', zone: { name: 'Autostradă', kind: 'highway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-A3-004'], thresholds: { speedKmh: 180 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-006', name: 'Viteză foarte mare — oraș', alertType: 'high_speed', zone: { name: 'Bulevard', kind: 'roadway' }, cameraIds: ['CAM-BIM-01', 'CAM-BUN-02', 'CAM-PIP-04'], thresholds: { speedKmh: 90 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-007', name: 'Staționare pe banda de urgență', alertType: 'emergency_lane_stop', zone: { name: 'Bandă de urgență', kind: 'emergency_lane' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-A3-004', 'CAM-CB-CHJ'], thresholds: { dwellSec: 60 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-008', name: 'Aproape-accident la trecere', alertType: 'near_miss', zone: { name: 'Trecere de pietoni', kind: 'crosswalk' }, cameraIds: ['CAM-BIM-01', 'CAM-BUN-02', 'CAM-PIP-04'], thresholds: { distanceM: 1.5 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-009', name: 'Frânare bruscă', alertType: 'hard_braking', zone: { name: 'Toate benzile', kind: 'roadway' }, cameraIds: ['CAM-CB-CHJ', 'CAM-DN1-OTP', 'CAM-DN7-CHT'], thresholds: { decelMs2: 6 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-010', name: 'Distanță prea mică între vehicule', alertType: 'tailgating', zone: { name: 'Bandă 1', kind: 'highway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012'], thresholds: { distanceM: 10, speedKmh: 100 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-011', name: 'Schimbări de bandă periculoase', alertType: 'dangerous_lane_change', zone: { name: 'Toate benzile', kind: 'roadway' }, cameraIds: ['CAM-CB-CHJ', 'CAM-DN1-OTP', 'CAM-PIP-04'], thresholds: { distanceM: 5 }, enabled: false, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-012', name: 'Sens unic — Bd. Unirii', alertType: 'wrong_way', zone: { name: 'Sens unic', kind: 'one_way' }, cameraIds: ['CAM-BUN-02'], thresholds: {}, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-013', name: 'Aglomerare', alertType: 'congestion', zone: { name: 'Toate benzile', kind: 'roadway' }, cameraIds: ['CAM-CB-CHJ', 'CAM-DN1-OTP', 'CAM-BIM-01', 'CAM-PIP-04'], thresholds: { speedKmh: 15, dwellSec: 300 }, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
  { id: 'R-014', name: 'Condiții de drum (ceață, polei)', alertType: 'road_conditions', zone: { name: 'Câmp vizual', kind: 'roadway' }, cameraIds: ['CAM-A1-023', 'CAM-A2-012', 'CAM-A3-004', 'CAM-DN7-CHT'], thresholds: {}, enabled: true, unit: UNIT, updatedAt: at, updatedBy: 'admin' },
]

export const PATROLS: Patrol[] = [
  { id: 'P-B21', callsign: 'B-21', unit: UNIT, vehicle: 'Dacia Logan MCV', status: 'available', area: 'Sector 6 / A1' },
  { id: 'P-B14', callsign: 'B-14', unit: UNIT, vehicle: 'Skoda Octavia', status: 'available', area: 'Sector 3 / A2' },
  { id: 'P-B07', callsign: 'B-07', unit: UNIT, vehicle: 'VW Passat', status: 'on_scene', area: 'Sector 1 / DN1' },
  { id: 'P-B33', callsign: 'B-33', unit: UNIT, vehicle: 'Dacia Duster', status: 'available', area: 'Centura Vest' },
  { id: 'P-M02', callsign: 'M-02', unit: UNIT, vehicle: 'Motocicletă BMW R1250RT', status: 'available', area: 'Centru' },
  { id: 'P-B40', callsign: 'B-40', unit: UNIT, vehicle: 'Skoda Kodiaq', status: 'off_duty', area: 'Sector 2 / Pipera' },
]
