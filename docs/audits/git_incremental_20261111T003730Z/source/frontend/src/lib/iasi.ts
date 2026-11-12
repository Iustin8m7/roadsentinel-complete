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

// Every mapped camera except the public Piața Unirii stream plays licensed stock footage filmed
// elsewhere; it sits on the Iași map for illustration only, and the UI has to say so.
export const REAL_STREAM_ID = 'iasi-piata-unirii';
export const DEMO_LEGEND = 'Locații demonstrative; filmări de arhivă';
export const isDemoCamera = (id: string) => id !== REAL_STREAM_ID && Object.hasOwn(IASI_CAMERAS, id);
/** Display name of a mapped camera, marked DEMO for stock footage; undefined for other cameras. */
export const iasiCameraName = (id: string): string | undefined =>
  Object.hasOwn(IASI_CAMERAS, id) ? `${isDemoCamera(id) ? 'DEMO · ' : ''}${IASI_CAMERAS[id].name}` : undefined;

export const IASI_MAP_CONFIG = {
  center: [47.1585, 27.6014] as [number, number],
  defaultZoom: 13,
  minZoom: 11,
  maxZoom: 18,
  maxBounds: [
    [47.10, 27.48], // Southwest
    [47.22, 27.72], // Northeast
  ] as [[number, number], [number, number]],
  tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
};
