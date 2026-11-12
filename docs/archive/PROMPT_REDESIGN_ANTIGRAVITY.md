# Prompt pentru Antigravity: redesign complet RoadSentinel („operațional sobru”)

> Copiază tot de mai jos în Antigravity. Lucrează în `frontend/`.

---

Faci **redesign vizual complet** pentru aplicația React din `frontend/` (Vite + React 19 + TS + Tailwind 4 + React Router 7 + Zustand). Este UI-ul de dispecerat **RoadSentinel**, al Poliției Rutiere Iași.

Designul actual arată învechit și „generat de AI”: negru cu glow cian, titluri condensed uppercase, puncte care pulsează, chip-uri CCTV, Inter peste tot și carduri identice cu bordură. **Îl înlocuim complet** cu o direcție **„operațional sobru”**: un instrument de lucru real, ca software-ul de dispecerat, trading sau monitorizare de infrastructură. Interfața e calmă, densă, lizibilă și fără decor. Culoarea apare **doar** când spune ceva, adică la gravitate și stare.

## 0. Ce NU ai voie să atingi (logica funcționează și e testată)
Nu modifica comportamentul acestor fișiere. Poți schimba doar clasele CSS și markup-ul din componente, nu logica:
- `src/lib/api.ts`, `src/lib/adapters.ts`, `src/lib/demo.ts`, `src/lib/iasi.ts`, `src/lib/permissions.ts`, `src/store/*`, `src/hooks/*`, `src/App.tsx` (rutele);
- în `src/components/EvidencePlayer.tsx` păstrează **toată** logica: cache-ul blob (`getClip`/`cachedClip`), thumbnail-urile din canvas, scurtăturile, viteza implicită 0,25×, marcajul evenimentului la jumătatea clipului. Restilizezi doar markup-ul;
- în `src/components/IasiMap.tsx` păstrează Leaflet, tile-urile OSM și `referrerPolicy`. Restilizezi markerele, popup-urile și overlay-urile, iar funcțiile de editare sunt eliminate (vezi secțiunea 4b);
- în `src/layouts/AppLayout.tsx` păstrează ecranul de preîncărcare a clipurilor (logica `preloadClips`) și redirecționările.

Funcțiile trebuie să rămână identice: decizia umană (Confirmă / Respinge cu notă obligatorie / Confirmă și trimite patrulă), coada paginată, player-ul în modal, filtrele din arhivă, harta.

## 1. Fundația: design tokens (fă asta PRIMUL)
În `src/index.css` definește **toate** culorile, razele, umbrele și fonturile ca variabile CSS, cu `@theme` din Tailwind 4, ca să existe clase precum `bg-surface` sau `text-muted`. Apoi **elimină toate culorile hex scrise direct în componente** (`#0A0E14`, `#111821`, `#3DA5FF` etc.) și folosește doar token-uri. Verificare: `grep -rn "#[0-9A-Fa-f]\{6\}" src --include=*.tsx` nu trebuie să mai găsească nimic, în afară de `src/mocks`.

**Paletă: grafit neutru, ușor rece, fără albastru-neon**
| Token | Valoare | Folosire |
|---|---|---|
| `--bg` | `#0F1113` | fundalul aplicației |
| `--surface` | `#16191C` | panouri, carduri |
| `--surface-2` | `#1D2125` | hover, rânduri selectate, input-uri |
| `--border` | `#2A2F34` | separatoare (folosește-le rar) |
| `--text` | `#E8EAEC` | text principal |
| `--text-muted` | `#9AA1A8` | text secundar |
| `--text-faint` | `#6B7278` | etichete, metadate |
| `--accent` | `#D8DEE4` | acțiuni primare: buton deschis la culoare cu text închis, nu albastru |
| `--focus` | `#7FA7D9` | doar inelul de focus (accesibilitate) |
| `--crit` | `#E5484D` | gravitate critică |
| `--high` | `#E58A3A` | ridicată |
| `--med` | `#D9B23F` | medie |
| `--info` | `#6E8FB8` | info |
| `--ok` | `#3FA56B` | confirmat / online |

Culorile de gravitate apar doar ca **punct de 8 px + text** sau ca o bandă subțire de 3 px. Nu le folosi ca fundal plin, cu glow sau cu umbră colorată. Fundal colorat e permis numai pentru butonul de confirmare (`--ok` atenuat) și pentru starea „critică nouă” (`--crit` la 10% opacitate).

**Tipografie: Geist + Geist Mono, găzduite local**
- CSP-ul gateway-ului permite fonturi numai de pe propriul domeniu (`font-src 'self'`), deci **nu folosi Google Fonts**. Instalează pachetul npm `geist` (sau `@fontsource-variable/geist` și `@fontsource-variable/geist-mono`) și importă-l local.
- Elimină complet Inter, Barlow Condensed și JetBrains Mono, inclusiv din `index.html`.
- Scară: 12 / 13 (corp implicit) / 14 / 16 / 20 / 28 px. Greutăți: 400, 500, 600; **nu folosi 700–800**.
- **Fără uppercase** pentru titluri și butoane. Folosește majusculă doar la început de propoziție („Coada de alerte”, nu „COADA DE ALERTE”). Etichetele mici de secțiune pot avea 12 px, culoarea `--text-faint` și `letter-spacing: 0.02em`, tot fără uppercase.
- Geist Mono se folosește **doar** pentru ID-uri (`#107`), ore, coordonate și valori numerice din tabele. Cifrele din KPI-uri sunt Geist cu `font-variant-numeric: tabular-nums`, la 28 px, greutate 500.

**Formă și spațiere**
- Raze: 6 px pentru carduri și input-uri, 4 px pentru butoane și badge-uri. Nu folosi `rounded-xl` sau `rounded-2xl`.
- Grilă de spațiere 4 px. Padding pentru carduri: 16 px; gap între carduri: 12 px.
- **Fără umbre colorate, glow, gradient, backdrop-blur sau glassmorphism.** Este permisă o singură umbră neutră, pentru modale: `0 8px 24px rgba(0,0,0,.4)`.
- **Fără animații decorative:** nu folosi `animate-pulse`, `animate-ping`, radar sau scanline. Rămân doar tranzițiile de 120 ms la hover și focus, plus un singur indicator de „nou” (un punct fix, care nu clipește).
- Separă zonele prin spațiu și prin `--surface` față de `--bg`, nu prin borduri peste tot. Bordurile de 1 px apar doar unde chiar delimitează: tabele, input-uri.

**Componente de bază** (fă-le reutilizabile în `src/components/ui.tsx`): `Button` (primar, secundar, ghost, pericol; înălțime 32 px), `Badge` pentru gravitate (punct + text), `StatusBadge`, `Card` (header opțional cu titlu de 14 px / 600 și acțiuni în dreapta), `Kpi`, `IconButton`, `Input`, `Select`, `Modal`, `EmptyState`, `Skeleton`. Iconurile rămân lucide-react, cu `strokeWidth={1.75}` și 16 px.

## 2. Reguli de layout (la fel pe toate paginile)
- Aplicația ocupă exact viewport-ul, **fără scroll de pagină** (verifică la 1440×860 și 1280×720). Listele se paginează, așa cum fac deja.
- **Sidebar:** 220 px lățime, pe `--surface`. Sus logo-ul RoadSentinel (fără glow) și „Iași”. Apoi elementele de meniu ca rânduri orizontale de 32 px, cu icon 16 px și text 13 px: Panou (cu numărul de alerte de verificat aliniat la dreapta, cu `--crit`), Camere, Arhivă, Statistici, iar Setări / Audit / Patrule / Reguli doar pentru admin, într-un grup „Administrare”. Elementul activ are fundal `--surface-2` și text `--text`, fără bară colorată. Jos: utilizatorul, rolul și „Ieșire”. Sidebar-ul se poate restrânge la 56 px.
- **Topbar:** 48 px. Stânga: breadcrumb (`Panou` sau `Panou / Alertă #107`). Dreapta: căutarea (240 px), ceasul HH:MM:SS cu Geist Mono la 13 px (nu cifre gigantice) și indicatorul de conexiune live (punct `--ok` fix și „Live”).
- **Ecranul de preîncărcare** (din AppLayout): fundal `--bg`, logo, „Se pregătesc dovezile video”, o bară de progres subțire de 2 px, „12 / 40” și linkul „Continuă” cu `--text-faint`.

## 3. Pagini (aceeași structură, stil nou)

### Panou `/app`
Structura rămâne: **4 KPI-uri sus; coada de alerte în stânga (7/12); harta și patrulele în dreapta (5/12).**
- **KPI-urile** formează o bandă: 4 celule pe `--surface`, separate prin linii verticale de 1 px, nu 4 carduri distincte. Fiecare celulă are eticheta (12 px, `--text-muted`), valoarea (28 px) și o linie mică de context (12 px, `--text-faint`, ex. „din 6 camere”).
- **Coada de alerte** e un card cu titlul „Coada de alerte”, la dreapta „1–7 din 12” și săgeți ghost. Rândurile au **56 px**, separate prin linii de 1 px, nu carduri. Coloanele sunt:
  - bandă de gravitate de 3 px;
  - miniatură 16:9 cu lățimea 80 px, rază 4 px, cu un icon ▶ discret la hover, care deschide modalul;
  - tipul (14 px / 500) și dedesubt camera · viteza (12 px, `--text-muted`);
  - badge-ul de gravitate;
  - timpul relativ (12 px, `--text-faint`, aliniat dreapta);
  - butonul secundar „Verifică”.

  Hover pe rând: `--surface-2`.
- **Harta:** card fără titlu decorativ („Radar tactic” dispare), cu eticheta discretă „Iași · 6 camere” în colțul din stânga sus. Markerele camerelor sunt cercuri de 10 px pe `--surface`, cu bordură în culoarea gravității celei mai mari, fără inele pulsante. Alerta critică primește un singur inel static de 2 px. Patrulele sunt pătrate mici de 8 px cu indicativul la hover. Tile-urile întunecate rămân cum sunt (filtrul `.rs-dark-tiles`), dar fă-le mai neutre, mai puțin albăstrui.
- **Patrule pe teren:** un card mic cu listă de 4 rânduri de 28 px: punct de stare, indicativ (mono), stare, cartier. Eticheta „Demo” rămâne cu `--text-faint`.

### Dosarul alertei `/app/alerte/:id`
Structura rămâne: **player 8/12 în stânga; Verificare umană, Context și Istoric în dreapta (4/12).**
- **Header:** „← Panou” (ghost), `#107` (mono, `--text-faint`), titlul (20 px / 600, fără uppercase), badge-ul de gravitate și starea.
- **Player:** fundal negru, rază 6 px. Bara de control are 40 px, pe `--surface`, cu iconuri ghost de 16 px. Bara de progres e subțire, de 3 px (6 px la hover), cu marcajul evenimentului ca o **linie verticală** `--crit` de 2 px, nu romb. Eticheta „DOVADĂ” cu punct roșu pulsant dispare; overlay-ul de sus păstrează doar „Camera · ora”, cu text pe un gradient negru discret. Filmstrip-ul are 6 cadre cu rază 4 px; cadrul activ are bordură `--text`, iar cel al evenimentului are o bandă `--crit` sub el.
- **Verificare umană** e cardul principal: titlul „Verificare umană”, textul „Decizia aparține exclusiv dispecerului.” (12 px, `--text-muted`) și butoanele:
  - „Confirmă”: primar, fundal `--ok` atenuat, text deschis;
  - „Respinge”: secundar, cu text `--crit`;
  - „Confirmă și trimite patrulă”: secundar, pe toată lățimea.

  Modalul de respingere e sobru, cu titlul „Motivul respingerii” și nota obligatorie.
- **Context:** listă cheie / valoare pe 2 coloane, etichetele cu `--text-faint`.
- **Istoric:** timeline vertical cu puncte de 6 px și linie de 1 px, ora în mono.

### Camere `/app/camere`
Header: titlul „Camere” (20 px), „6 online”, comutatorul Grilă / Hartă (segmented control) și butonul secundar „Adaugă cameră”. Grila are 3 coloane la 1440 px. Cardurile au imaginea 16:9 sus, iar dedesubt numele (14 px / 500), locația (12 px, `--text-muted`), starea (punct + „Online”) și „N alerte deschise”. Nu mai există badge-uri suprapuse peste imagine, în afară de un mic „N” cu `--crit` când sunt alerte. La hover, sub imagine, apar două butoane ghost: „Redă clipuri” și „Istoric”. Modul Hartă arată harta pe tot conținutul.

### Arhivă `/app/arhiva`
Stânga: bara de căutare (40 px, cu icon), apoi „Căutări rapide” ca chip-uri neutre (`--surface-2`, 28 px, rază 4 px), rândul „Filtre aplicate” și grila de 4 coloane de carduri video (miniatură 16:9, tipul evenimentului, camera · ora, clasa vehiculului ca text, nu badge colorat). Dreapta: panoul „Filtre” (260 px) cu checkbox-uri sobre și slider.

### Statistici `/app/statistici`
Aceeași bandă de 4 KPI-uri ca pe Panou, apoi graficele în carduri. **Graficele sunt monocrome** (nuanțe de `--text-muted`), cu culorile de gravitate doar pe graficul „pe gravitate”. Heatmap-ul „oră × zi” folosește o singură nuanță, cu opacitate variabilă. Fără gradient și fără glow pe bare.

### Setări, Audit, Patrule, Reguli
Tabele dense: rânduri de 36 px, header sticky 12 px `--text-faint`, linii de 1 px, mono pentru ore și ID-uri. Toggle-urile din Setări folosesc componente sobre, de 32 px.

### Login `/login`: NU îl atinge
`/` redirecționează la `/login`, iar landing page-ul a fost șters. **Pagina de login (`src/pages/LoginPage.tsx`) o face Claude Code, separat.** Nu edita fișierul și nu recrea landing-ul.

## 4. Ce trebuie să dispară peste tot
- glow, `shadow-[0_0_…]`, `animate-pulse`, `animate-ping`, radar, scanline, vigneta, colțurile HUD (`cctv-hud-*`);
- uppercase pe titluri, butoane și etichete, plus fonturile condensed;
- culori hex hardcodate, folosite în locul token-urilor;
- texte decorative fără sens („CARTO DARK TACTICAL”, „#FF8A1F” scris ca text, „Mono”, „36% [|||||]”);
- orice verificare AI / VLM sau procent de încredere.

## 4a. ATENȚIE: nu rescrie fișiere din copii vechi
Fișierul `IasiMap.tsx` a fost suprascris o dată cu o versiune veche, care a readus modul de editare și a pierdut trei reparații de producție. **Înainte de fiecare editare, citește fișierul de pe disc.** În `IasiMap.tsx` trebuie să rămână:
- `import 'leaflet/dist/leaflet.css'`;
- pe `TileLayer`: `className="rs-dark-tiles"` și `referrerPolicy="strict-origin-when-cross-origin"`, fără `subdomains`;
- în `index.css`: clasa `.rs-dark-tiles`;
- în `src/lib/iasi.ts`: `tileUrl` pe `tile.openstreetmap.org`, nu CARTO (CARTO cere cheie și CSP-ul o blochează).

Fonturile Geist sunt acum găzduite în `public/fonts/` (`url('/fonts/Geist-Variable.woff2')`), iar build-ul trece. Nu schimba această parte.

## 4b. Funcții eliminate în paralel (nu le reintroduce)
Claude Code șterge **în paralel cu tine** funcțiile inutile: modul de editare al hărții, „Exportă poziții”, click dreapta cu coordonate, intrările `cam-01`…`cam-10`, „Adaugă cameră”, „Ai uitat parola?”, „Adaugă filtru”, slider-ul „Durată minimă”, selectorul de perioadă din Statistici, toggle-ul de blur (nu avea efect), opțiunile din Setări care merg doar în modul demo, cifrele inventate de pe landing și **landing page-ul întreg**. Setările au acum doar cardul „Notificări” (semnal sonor).
- **Nu le reintroduce și nu le restiliza.** Dacă un fișier are modificări pe care nu le-ai făcut tu, reîncarcă-l de pe disc înainte să-l editezi și nu suprascrie modificările altcuiva.
- Lucrează pe fișierul curent de pe disc, nu pe o copie veche.

## 5. Criterii de acceptare (verifică-le înainte să zici că e gata)
1. `npx tsc -b` și `npm run build` trec fără erori, iar `npx vitest run` e verde.
2. `grep -rn "Barlow\|JetBrains\|Inter'" src index.html` nu găsește nimic. Fonturile Geist se încarcă local (fără cereri externe de fonturi).
3. `grep -rn "animate-pulse\|animate-ping\|shadow-\[0_0" src` nu găsește nimic.
4. Panoul, Dosarul, Camerele, Arhiva și Statisticile nu au scroll de pagină la 1440×860 și 1280×720.
5. `grep -rn "editable\|onPositionChange\|Exportă poziții\|cam-01\|Ai uitat parola" src` nu găsește nimic.
6. Funcțiile merg ca înainte:
   - ecranul de preîncărcare apare și dispare;
   - player-ul din dosar și din modal pornește la 0,25×, derulează și are cadre reale;
   - Confirmă, Respinge (cu notă) și Trimite patrulă funcționează;
   - coada se paginează;
   - harta afișează Iașiul cu markere.
7. Contrast text / fundal cel puțin 4.5:1 pentru textul principal și secundar. Focus vizibil (`--focus`) pe toate elementele interactive.
8. Testează în modul demo: `VITE_USE_MOCKS=1 npx vite`, login cu admin / <demo-password>.

Lucrează **în această ordine:** token-uri și fonturi → componente de bază → AppLayout (sidebar, topbar) → Panou → Dosar și Player → Camere → Arhivă → Statistici → Setări / Audit / Patrule / Reguli. (Login-ul nu e sarcina ta.) După fiecare pas rulează `npx tsc -b`. Nu face commit și nu face deploy: le fac eu după verificare.
