# Prompt: harta Iașiului pe coordonate GPS (camere și patrule puse din frontend)

> Copiază tot de mai jos într-un generator de cod. Rezultatul înlocuiește `src/components/TacticalMap.tsx` (desen SVG stilizat, fără coordonate reale).

---

Creează în proiectul React 19 + TypeScript + Tailwind 4 (Vite) componenta **`IasiMap`**: o hartă reală a municipiului **Iași**, cu coordonate GPS (WGS84, lat/lng), peste care frontend-ul pune **camerele de trafic, patrulele și alertele**.

## Bibliotecă și fundal
- **MapLibre GL JS** (`maplibre-gl`, versiune fixă, ex. 4.7.1) cu `react-map-gl/maplibre`, sau **Leaflet 1.9.4 + react-leaflet 4**. Alege una și explică alegerea.
- **Tile-uri gratuite, fără cheie API:** OpenStreetMap / CARTO **Dark Matter** (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`), cu atribuirea obligatorie „© OpenStreetMap contributors © CARTO” vizibilă în colț.
- Temă dark „tactical”, potrivită cu aplicația: fundal `#0A0E14`, panou `#111821`, bordură `#1E2A36`, text `#E6EDF3` / `#7D8A9B`, accent `#3DA5FF`, OK `#2ED47A`. Gravitate: critică `#FF3B3B`, ridicată `#FF8A1F`, medie `#FFC23D`, info `#3DA5FF`. Fonturi: JetBrains Mono pentru etichete și Barlow Condensed pentru titluri.

## Încadrare
- Centru `[47.1585, 27.6014]` (lat, lng), zoom inițial 13, limite de navigare (maxBounds) `sud-vest [47.10, 27.48]` – `nord-est [47.22, 27.72]`, zoom între 11 și 18.
- Componenta umple containerul (`w-full h-full`) și se redimensionează corect: ResizeObserver → `map.resize()` / `invalidateSize()`.
- Fără scroll pe pagină; rotița de zoom e activă doar când harta are focus, sau cu Ctrl.

## API-ul componentei
```ts
type Severity = 'critical' | 'high' | 'medium' | 'info'
interface MapCamera { id: string; name: string; location: string; lat: number; lng: number; status: 'online' | 'offline'; openAlerts: number; worst?: Severity }
interface MapPatrol { id: string; callsign: string; lat: number; lng: number; status: 'available' | 'busy' | 'break'; area?: string }
interface MapAlert  { id: string; cameraId: string; severity: Severity; label: string }

interface IasiMapProps {
  cameras: MapCamera[]
  patrols?: MapPatrol[]
  alerts?: MapAlert[]              // the most severe open alert gets pulsing rings on its camera
  focusCameraId?: string           // fly-to animation to this camera
  editable?: boolean               // drag markers to set GPS positions from the frontend
  onCameraClick?: (id: string) => void
  onPatrolClick?: (id: string) => void
  onPositionChange?: (kind: 'camera' | 'patrol', id: string, lat: number, lng: number) => void
  className?: string
}
```

## Straturi
1. **Camere:** cerc de 14 px cu un iconiță de cameră, bordura colorată după `worst` (fără alerte: `#3DA5FF`; offline: gri `#536070`), badge cu `openAlerts` când e > 0. Eticheta cu numele apare la hover. La click: popup dark cu nume, locație, stare, „N alerte deschise” și butoanele „Redă clipuri” / „Dosar”, care apelează `onCameraClick`.
2. **Alertă activă:** pe camera cu cea mai gravă alertă deschisă, 3 inele concentrice pulsante (animație CSS de ~1,6 s) și eticheta tipului alertei.
3. **Patrule:** marker dreptunghiular rotunjit cu indicativul (ex. `IS-21-POL`). Culoare: disponibilă `#2ED47A`, în misiune `#FF8A1F`, pauză `#7D8A9B`. Arată tranziție lină când primește coordonate noi (pentru mișcare simulată).
4. **Opțional, suprapuneri GeoJSON:** Centura Iași, axele principale (Bd. Ștefan cel Mare, Bd. Independenței, Bd. Carol I, Bd. Nicolae Iorga, Șos. Păcurari, Bd. Socola) evidențiate subțire cu `#2D445D`. Ia geometria din OSM (Overpass) și salvează fișierul static `public/geo/iasi-roads.geojson`. Nu face cereri la Overpass la rulare.

## Mod editare (`editable`)
- Markerele de cameră și de patrulă pot fi trase cu mouse-ul. La eliberare se apelează `onPositionChange` cu coordonatele noi rotunjite la 6 zecimale.
- Click dreapta pe hartă afișează coordonatele și le copiază în clipboard, ca să le punem ușor în `src/lib/iasi.ts`.
- Un buton mic „Exportă poziții” descarcă JSON-ul cu toate pozițiile curente.

## Date inițiale (aproximative; de corectat în modul editare)
```ts
export const IASI_CAMERAS = {
  'demo-highway':    { name: 'Centura Iași – DN28, pasarelă',      location: 'Centura Iași, DN28 km 4',              lat: 47.1305, lng: 27.6551 },
  'demo-urban':      { name: 'Pasaj Octav Băncilă',                location: 'Bd. Independenței',                    lat: 47.1662, lng: 27.5793 },
  'mx-avenue':       { name: 'Bd. Ștefan cel Mare și Sfânt',       location: 'trecere de pietoni',                   lat: 47.1647, lng: 27.5822 },
  'mx-bridge-night': { name: 'Pasaj Mihai Eminescu (noapte)',      location: 'sens Copou',                           lat: 47.1712, lng: 27.5719 },
  'mx-interchange':  { name: 'Nod rutier Podu Roș (vedere de sus)', location: 'Podu Roș × Bd. Nicolae Iorga',        lat: 47.1540, lng: 27.5893 },
  'mx-junction':     { name: 'Intersecție Piața Unirii',           location: 'Piața Unirii',                          lat: 47.1658, lng: 27.5770 },
}
export const IASI_PATROLS = [
  { id: 'IS-21', callsign: 'IS-21-POL', lat: 47.1800, lng: 27.5680, status: 'available', area: 'Copou' },
  { id: 'IS-14', callsign: 'IS-14-POL', lat: 47.1545, lng: 27.5900, status: 'busy',      area: 'Podu Roș' },
  { id: 'IS-07', callsign: 'IS-07-POL', lat: 47.1610, lng: 27.6080, status: 'available', area: 'Tătărași' },
  { id: 'IS-33', callsign: 'IS-33-POL', lat: 47.1370, lng: 27.5770, status: 'break',     area: 'Nicolina' },
]
```
Coordonatele sunt orientative (am estimat pozițiile pentru demo). Verifică-le pe hartă și ajustează-le cu modul de editare.

## Integrare
- Panoul principal (`/app`, coloana din dreapta), harta mică: camerele din `useDataStore` (cu `lat`/`lng` din `IASI_CAMERAS`), patrulele MOCK și alertele din coada deschisă.
- `/app/camere`, modul Hartă: harta pe tot ecranul, cu `editable` doar pentru admin.
- Harta se încarcă leneș (`React.lazy`), ca să nu îngreuneze bundle-ul inițial.

## Livrabile
- `src/components/IasiMap.tsx`, `src/lib/iasi.ts` (camere și patrule), `public/geo/iasi-roads.geojson` (opțional);
- stiluri pentru markere și popup în tema de mai sus;
- funcționare la 1440×860 și 1280×720, fără scroll; `npx tsc -b` și `npm run build` fără erori.
