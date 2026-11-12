export type Severity = 'critical' | 'high' | 'medium' | 'info';

export interface MapCamera {
  id: string;
  name: string;
  location: string;
  lat: number;
  lng: number;
  status: 'online' | 'offline';
  openAlerts: number;
  worst?: Severity;
}

export interface MapPatrol {
  id: string;
  callsign: string;
  lat: number;
  lng: number;
  status: 'available' | 'busy' | 'break';
  area?: string;
}

export interface MapAlert {
  id: string;
  cameraId: string;
  severity: Severity;
  label: string;
}

export const IASI_CAMERAS: Record<string, { name: string; location: string; lat: number; lng: number; liveUrl?: string }> = {
  'iasi-piata-unirii': {
    name: 'Piața Unirii (live)',
    location: 'Piața Unirii · sursa: WebcamRomania.ro / Grand Hotel Traian',
    lat: 47.1655,
    lng: 27.5806,
    liveUrl: 'https://w1.webcamromania.ro/piatauniriiiasi/index.m3u8',
  },
  'demo-highway': {
    name: 'Centura Iași – DN28, pasarelă',
    location: 'Centura Iași, DN28 km 4',
    lat: 47.1305,
    lng: 27.6551,
  },
  'demo-urban': {
    name: 'Pasaj Octav Băncilă',
    location: 'Bd. Independenței',
    lat: 47.1662,
    lng: 27.5793,
  },
  'mx-avenue': {
    name: 'Bd. Ștefan cel Mare și Sfânt',
    location: 'trecere de pietoni',
    lat: 47.1647,
    lng: 27.5822,
  },
  'mx-bridge-night': {
    name: 'Pasaj Mihai Eminescu (noapte)',
    location: 'sens Copou',
    lat: 47.1712,
    lng: 27.5719,
  },
  'mx-interchange': {
    name: 'Nod rutier Podu Roș (vedere de sus)',
    location: 'Podu Roș × Bd. Nicolae Iorga',
    lat: 47.1540,
    lng: 27.5893,
  },
  'mx-junction': {
    name: 'Intersecție Piața Unirii',
    location: 'Piața Unirii',
    lat: 47.1658,
    lng: 27.5770,
  },
};

export const IASI_PATROLS: MapPatrol[] = [
  { id: 'IS-21', callsign: 'IS-21-POL', lat: 47.1800, lng: 27.5680, status: 'available', area: 'Copou' },
  { id: 'IS-14', callsign: 'IS-14-POL', lat: 47.1545, lng: 27.5900, status: 'busy',      area: 'Podu Roș' },
  { id: 'IS-07', callsign: 'IS-07-POL', lat: 47.1610, lng: 27.6080, status: 'available', area: 'Tătărași' },
  { id: 'IS-33', callsign: 'IS-33-POL', lat: 47.1370, lng: 27.5770, status: 'break',     area: 'Nicolina' },
];

export const IASI_MAP_CONFIG = {
  center: [47.1585, 27.6014] as [number, number],
  defaultZoom: 13,
  minZoom: 11,
  maxZoom: 18,
  maxBounds: [
    [47.10, 27.48], // Southwest
    [47.22, 27.72], // Northeast
  ] as [[number, number], [number, number]],
};
