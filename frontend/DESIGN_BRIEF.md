# RoadSentinel — brief de design (pentru Antigravity)

> Copiază acest fișier ca prompt în Antigravity. Logica, rutele, auth-ul mock și datele sunt deja gata și funcționale. **Rolul tău este doar designul vizual / UX.**

## Context

RoadSentinel este o platformă pentru **Poliția Română** (Brigada Rutieră) care monitorizează camerele de trafic cu AI (YOLO + verificare VLM) și trimite alerte în timp real către operatorii de dispecerat și patrule, cu dovezile deja pregătite. Vezi `../README.md` pentru descrierea completă.

Utilizatori: operatori de dispecerat care stau ore întregi în fața ecranului (de multe ori noaptea), anchetatori, agenți de patrulă, administratori. Interfața e în **limba română**.

## Direcție vizuală

- Instrument operațional, nu site de marketing: dens, calm, lizibil la distanță, fără decorațiuni inutile.
- **Dark mode ca implicit** (camere de dispecerat întunecate), cu light mode funcțional.
- Gravitatea trebuie să fie recunoscută dintr-o privire și **nu doar prin culoare** (icon + text + culoare; accesibil pentru daltonism):
  - Critică — roșu · Ridicată — portocaliu · Medie — galben/chihlimbar · Informativă — albastru
- Identitate sobră, instituțională (albastru Poliție). Fără sigle oficiale reale ale Poliției Române / MAI.
- Responsive: desktop principal (1440–1920px, ecrane de dispecerat), tabletă și telefon pentru agenții de patrulă.
- Tipografie cu cifre tabulare pentru ore, viteze și contoare.

## Ce poți modifica liber

- `src/index.css` — e un **placeholder**; rescrie-l complet (tokens, componente, layout).
- Markup-ul și clasele din `src/components/ui.tsx`, `src/layouts/AppLayout.tsx` și `src/pages/*.tsx`.
- Poți adăuga librării UI/animație/grafice (ex. `recharts` pentru Statistici, `leaflet`/`react-leaflet` pentru o hartă a camerelor — coordonatele sunt în `src/mocks/cameras.ts`).
- Iconițe: `lucide-react` este deja instalat.

## Ce NU trebuie modificat (contractul cu logica)

- `src/store/*`, `src/mocks/*`, `src/lib/*` (în afară de `format.ts` dacă vrei alt format), `src/hooks/*`, `src/types/*`, `src/App.tsx` (rutele), `src/components/guards.tsx`.
- Numele props-urilor componentelor din `ui.tsx` (le folosesc paginile).
- Apelurile către store (`confirmAlert`, `rejectAlert`, `addAction`, `login`, etc.) și verificările de permisiuni (`useCan(...)`).
- Textele legale/de garanție: „Decizia rămâne la om”, blur implicit, ±3–5 km/h doar pentru triaj, nota de audit de pe login.

## Hook-uri de stil existente (atribute data-*)

`data-severity` (critical/high/medium/info), `data-status` (new/in_review/confirmed/rejected/closed), `data-variant` pe butoane (default/primary/danger/ghost), `data-blurred`, `data-camera-status` (online/offline/degraded), `data-patrol-status`, `data-vlm` (confirmed/rejected/uncertain), `data-audit-action`, `data-on` pe indicatorul live.

## Ecrane de designat

| Rută | Ecran | Note |
|---|---|---|
| `/login` | Autentificare | Card centrat, sobru. Stări: loading („Se verifică…”), eroare, „păstrează-mă autentificat”. Conturile demo sunt într-un `<details>`. |
| `/` | Panou dispecerat | KPI-uri sus, coada de alerte ordonată după gravitate (elementul principal), patrule, distribuție pe gravitate. Ideal: hartă cu camere. |
| `/alerte` | Listă alerte | Tabel filtrabil (gravitate, stare, cameră, căutare). Rândurile critice trebuie să iasă în evidență. |
| `/alerte/:id` | Dosarul alertei | **Cel mai important ecran.** Video + cadre cheie (placeholdere), verdict și descriere VLM, context (cameră, regulă, zonă, metrici), decizie Confirmă/Respinge (nota e obligatorie la respingere), apoi acțiuni: trimite patrulă, panou de avertizare, constatare, închide dosarul. Istoric de audit. |
| `/camere` | Camere | Grilă de carduri cu „flux live” placeholder și stare. |
| `/patrule` | Patrule | Tabel cu stare editabilă. |
| `/reguli` | Reguli și zone | Listă de reguli cu toggle și editor inline pentru praguri. |
| `/arhiva` | Căutare în arhivă | Bară mare de căutare în limbaj natural, chip-uri cu exemple, chip-uri „Am înțeles: …”, grilă de clipuri. |
| `/statistici` | Statistici | KPI-uri + grafice (acum sunt bare simple — înlocuiește cu grafice reale; datele vin din `useStats()`). |
| `/audit` | Jurnal de audit | Tabel cu filtre și Export CSV. |
| `/setari` | Setări (doar admin) | Flux live simulat, confidențialitate, utilizatori/roluri, resetare demo. |
| — | Toast alertă nouă | Apare în colț la alerte critice/ridicate din fluxul live; trebuie să atragă atenția fără să fie agresiv. |
| — | 403 / 404 | Pagini simple. |

## Comportamente de reținut

- Fluxul live generează o alertă nouă la fiecare 30s (configurabil în Setări) — gândește animații discrete de intrare în listă.
- Meniul din stânga se filtrează după rol (autentifică-te cu `operator`, `anchetator`, `patrula` pentru a vedea variantele).
- Badge-ul de pe „Alerte” arată numărul de alerte deschise; în topbar apare o pastilă cu numărul de alerte critice.

## Conturi

`admin / admin` (acces complet) · `operator / operator` · `anchetator / anchetator` · `patrula / patrula`

---

## Notă Design UI: Conceptul „Matrix Phosphor Terminal” (Implementat)

### 1. Filosofie Vizuală & Ergonomie
- **Stil Terminal CRT cu Fosfor Verde**: Interfața transpune operatorul în rolul unui dispecer avansat care vizualizează codul și telemetria AI din spatele traficului.
- **Confort pe Ture Lungi (12h)**: Textul principal folosește o nuanță relaxantă de verde pal (`#B8FFC8`, contrast WCAG AA), evitând saturația neon pe paragrafe extinse.
- **Sistemul de Alertare „Rupe Matrix-ul”**:
  - Alertele **Critice** rup atmosfera verde cu accente „Red Pill” (`#FF2B2B`), animație de glitch RGB și glow pulsant.
  - Alertele **Ridicate** folosesc ambră fosfor (`#FFB000`).
  - Alertele **Medii** folosesc galben-verzui (`#C6FF00`), iar cele **Informative** verde Matrix (`#00FF41`).
- **Recunoaștere Accesibilă a Severității**: Fiecare nivel are cod dedicat de caractere (`[CRIT] ▲▲`, `[HIGH] ▲`, `[MED] ■`, `[INFO] ·`).

### 2. Tokens & Tipografie
- **Display & Cifre**: `VT323` (Google Fonts) cu glow fosfor verde pentru contoare, viteze și brand.
- **Etichete & Comenzi Consolidate**: `Share Tech Mono` pentru prompturi, tabele și badge-uri.
- **Corp & Tabele**: `JetBrains Mono` cu cifre tabulare pentru aliniere perfectă.
- **Paletă de Culori Principale**:
  - Fundal: `#000000` la `#010A04` cu vignetă CRT și scanlines opționale.
  - Border: `#003B00` (linie discretă de 1px), Highlight `#008F11`, Accent `#00FF41`.

### 3. Componente Cheie Adăugate
- `<MatrixRain />`: Canvas optimizat throttled la ~30fps cu katakana, cifre și simboluri (se oprește automat la document ascuns sau `prefers-reduced-motion`).
- `<TerminalPanel />`: Casete de terminal cu bară ASCII de status `┌─[ ... ]────── ● LIVE ─┐`.
- `<DecodeText />` & `<TypeText />`: Efecte de decodare și tastare care rulează o singură dată (≤ 600ms).
- `<AsciiBar />`: Barometru de progres în stil terminal ASCII `[████████░░░░] 67%`.
- `<CameraMonitor />`: Monitor CRT pentru camerele de trafic cu scanlines, timestamp OSD, bounding boxes animate și zgomot static TV pentru camerele offline.
- `<TacticalMap />`: Hartă radar vector tactical cu coordonatele camerelor din Ilfov/București și puls optic la alertă deschisă.
- `<Logo variant="full|mark|badge" />`: Emblemă hexagonală originală cu ochi cibernetic, iris de cod binar și perspectivă de drum prin pupilă.

---

## Notă Design UI: Conceptul „POLICE BADGE” (Implementat)

### 1. Filosofie Vizuală & Structură Fără Scroll (100vh)
- **Stil Vectorial Flat „Police Badge”**: Inspirat direct din `design-ref/moodboard-badges.png`, utilizând panouri bleumarin rotunjite (14–16px), accente și panglici aurii cu capete crestate, stele cu 6 colțuri și lauri.
- **Cerința Critică de Înălțime Fixă (100vh)**:
  - Nicio pagină nu are scroll vertical pe desktop (1366×768 până la 1920×1080).
  - `html, body, #root { height: 100%; overflow: hidden; }`
  - Shell `height: 100vh; overflow: hidden;`.
  - Conținutul fiecărei pagini este organizat într-un grid compact. Scroll-ul apare **strict în interiorul widget-urilor** care au conținut numeros (coada de alerte, tabele, jurnal audit, rezultatele căutării), cu headerele widget-urilor fixate.

### 2. Paletă & Tokens
- **Fundal Aplicație**: Gri-albastru ardezie `#5F6B7F` spre `#525D70`, cu textură discretă de puncte fine la 4–6% opacitate.
- **Bleumarin (Panouri & Sidebar)**: `#1E2B4A` (bază), `#233358` (suprafețe), `#2E4170` (hover / borduri interioare).
- **Auriu (Accente, Panglici & Stele)**: `#F5B82E`, `#E9A21B` (umbră), `#FFD36B` (highlight).
- **Text**: Crem `#F4F1E8` pe bleumarin, bleumarin `#1E2B4A` pe auriu, gri `#AEB8CC` pentru text secundar.
- **Niveluri de Gravitate (cu forme distincte de insignă)**:
  - **Critică**: Roșu `#E5484D`, stea cu 6 colțuri + `CRITIC`.
  - **Ridicată**: Portocaliu `#F2994A`, scut + `RIDICAT`.
  - **Medie**: Auriu `#F5B82E`, cerc + `MEDIU`.
  - **Informativă**: Albastru `#5B9BF0`, pătrat rotunjit + `INFO`.

### 3. Tipografie (Google Fonts în index.html)
- **Titluri, Panglici & Cifre KPI**: `Oswald`, UPPERCASE, letter-spacing 0.05em.
- **Text Principal & Tabele**: `Inter`, 13–14px.
- **ID-uri, Ore & Viteze**: `Roboto Mono`, cifre tabulare.

### 4. Componente Implementate
- `<BadgePanel />`: Container stil insignă cu antet de tip panglică aurie (`<RibbonHeader />`) și conținut scrollabil intern.
- `<BadgeKpi />`: Insignă compactă pentru indicatori de performanță.
- `<SeverityBadge />`: Insignă grafică vectorială conform severității.
- `<RoleBadge />`: Insigne specifice pentru fiecare rol (ADMIN, OPERATOR, ANCHETATOR, PATRULĂ).
- `<CameraMonitor />`: Monitor cu ramă bleumarin și banner OSD (FLUX LIVE / FĂRĂ SEMNAL).
- `<TacticalMap />`: Hartă radar vector discretă pentru camerele din Ilfov/București.

