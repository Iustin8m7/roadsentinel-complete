# Prompt: frontend nou RoadSentinel (stare la 2026-10-18)

> Copiază tot de mai jos într-un generator de UI / asistent de cod. Descrie exact ce există azi pe fiecare pagină, cum e așezat și de unde vin datele.

---

Construiește interfața web **RoadSentinel** pentru dispecerii Poliției Rutiere **Iași**: un sistem care urmărește automat camerele de trafic și trimite alerte. **Verificarea fiecărei alerte este strict umană:** nu există verificare AI/VLM, scoruri de încredere sau verdict automat în UI. Limba interfeței este româna, cu diacritice.

## Stack și reguli generale
- Vite + React 19 + TypeScript + Tailwind 4 + React Router 7 + Zustand, iconuri lucide-react, date cu date-fns (locale `ro`).
- **Desktop-first, fără scroll de pagină**: în aplicație fiecare ecran ocupă exact viewport-ul (`h-screen`, `overflow-hidden`). Listele lungi se **paginează** după cât loc este (ResizeObserver), nu se derulează. Ținte testate: 1440×860 și 1280×720.
- Temă dark „tactical”: fundal `#0A0E14`, panouri `#111821`, ridicat `#17202B`, borduri `#1E2A36`; text `#E6EDF3` / secundar `#7D8A9B` / stins `#536070`; accent `#3DA5FF`; OK `#2ED47A`. Gravitate: critică `#FF3B3B`, ridicată `#FF8A1F`, medie `#FFC23D`, info `#3DA5FF`.
- Fonturi: Inter (text), Barlow Condensed (titluri, cifre KPI, butoane, uppercase), JetBrains Mono (ore, ID-uri, telemetrie).
- Carduri cu `rounded-xl`, bordură 1 px și padding 12–14 px. Gravitatea se arată ca bandă colorată de 4 px în stânga rândului și ca badge.

## Rute
| Rută | Pagină | Acces |
|---|---|---|
| `/` | Landing | doar vizitatori (logatul → `/app`) |
| `/login` | Login | doar vizitatori |
| `/app` | Panou principal (dispecerat) | operator, admin |
| `/app/alerte/:id` | Dosarul alertei | operator, admin |
| `/app/camere` | Camere | operator, admin |
| `/app/arhiva` | Arhivă video | operator, admin |
| `/app/statistici` | Statistici | operator, admin |
| `/app/setari` | Setări | doar admin |
| `/app/audit`, `/app/patrule`, `/app/reguli` | secundare (meniu „extra”) | admin |
`/app/alerte` (lista) **nu mai există**: redirecționează la `/app`. Rutele vechi `/alerte/:id` → `/app/alerte/:id`.

## Layout aplicație (`/app/*`)
- **Sidebar îngust stânga (~72 px)**, iconuri cu etichete mici uppercase sub ele: Panou (cu badge roșu = numărul de alerte de verificat), Camere, Arhivă, Statistici, Setări (doar admin). Elementul activ are o bară albastră de 4 px în stânga. Jos sunt versiunea și meniul extra.
- **Bara de sus** (~56 px): titlul paginii („DISPECERAT / PANOU PRINCIPAL” + punct roșu live), căutare globală (trimite la arhivă cu `?q=`), ceas mare HH:MM:SS și utilizatorul cu rolul. Dosarul alertei și Camere își desenează propriul header.
- **Ecran de încărcare la intrare**: logo, titlul „Pregătire dosare video”, bară de progres, „X / N clipuri încărcate” și un link mic „Continuă oricum (restul se încarcă în fundal)”. Toate clipurile alertelor se descarcă în memorie (blob) înainte de afișare, ca să nu existe buffering la prezentare.

## Pagini

### 1. Landing `/`
Header cu logo și butonul „Autentificare”. **Hero pe 2 coloane:**
- **stânga:** chip „MONITORIZARE RUTIERĂ CU INTELIGENȚĂ ARTIFICIALĂ”, titlul „Fiecare cameră, un ochi care **nu doarme.**”, subtitlu (detecție YOLO, dovezi video pregătite instant, verificare exclusiv umană), CTA „Intră în dispecerat” și „Vezi cum funcționează”, 3 indicatori (fluxuri live, timp de procesare, „OM ÎN BUCLĂ – decizia finală aparține operatorului”);
- **dreapta:** monitor CCTV simulat („CAM-07 · Bd. Ștefan cel Mare”) cu chenare de detecție, o alertă roșie pulsantă „SENS INTERZIS DETECTAT” și bara de jos „AI: YOLO11s + ByteTrack · Verificare: dispecer · FPS 25”.

Sub hero:
- banda cu **4 pași**: Detecție continuă → Reguli configurabile → **Verificare umană** → Alertă către operator;
- secțiunea „Cum funcționează” (4 carduri);
- „Conformitate legală și etică” (GDPR, Directiva UE 2016/680, fără recunoaștere facială, fără sancțiuni automate);
- „Căutare în arhivă”;
- footer cu „Unitatea de Monitorizare Trafic Iași”.

### 2. Login `/login`
Fundal cu rețea de drumuri estompată. Card centrat (~420 px) cu: logo, „Acces securizat dispecerat”, câmpurile Utilizator și Parolă (cu ochi), „Ține-mă minte”, „Ai uitat parola?” (modal), butonul „INTRĂ ÎN SISTEM” și **conturi demo rapide** (admin – Administrator, operator – Dispecer rutier). Jos: „Sistem operațional · N camere active”.

### 3. Panou principal `/app` (fără scroll)
- **Rândul 1, 4 KPI-uri:** Alerte de verificat · Camere online (x/y) · Patrule disponibile (x/y, MOCK) · Rată alarme false (%).
- **Rândul 2, grilă de 12 coloane:**
  - **Coada de alerte (7 col.):** header „COADA DE ALERTE” cu paginare „1–7 din 12” și săgeți ‹ ›. Rânduri fixe de 60 px, câte încap. Fiecare rând are:
    - miniatura cadrului cheie (88 px) cu ▶, care deschide **player-ul mare în modal**;
    - tipul alertei (uppercase, bold);
    - camera și viteza „~xx km/h”;
    - badge-ul de gravitate;
    - timpul relativ „acum 4 s / 1 minut în urmă”;
    - butonul „Verifică”, care deschide dosarul.
  - **Dreapta (5 col.):** harta tactică a Iașiului (camere ca noduri colorate după gravitate, inele roșii pulsante la camera cu cea mai gravă alertă, patrule) și dedesubt „Patrule pe teren” (4 patrule IS-xx-POL pe 2 coloane: stare colorată, cartier; eticheta DEMO).
- **Ordinea cozii (demo):** întâi comportamentele agresive (accident probabil, sens interzis, **nepăstrarea distanței**, schimbare de bandă periculoasă, frânare bruscă), apoi oprire pe carosabil, viteză, aglomerare.

### 4. Dosarul alertei `/app/alerte/:id` (fără scroll)
- **Header:** „← Panou”, `#ID`, titlul regulii (uppercase), badge-ul de gravitate și badge-ul de stare (Nouă / În verificare / Confirmată / Respinsă).
- **Grilă 8 + 4 coloane:**
  - **Stânga, player de dovezi** (detalii mai jos), plus un **filmstrip de 6 cadre reale** extrase din clip. Cadrul evenimentului e marcat cu portocaliu („EVENIMENT”), iar celelalte arată ora.
  - **Dreapta, 3 carduri:**
    1. **Verificare umană:** text scurt „Decizia aparține exclusiv dispecerului”, butoanele **CONFIRMĂ** (verde) și **RESPINGE** (contur roșu; deschide un modal cu nota obligatorie, salvată în audit), plus **„Confirmă și trimite patrulă”** (albastru). După decizie: starea, cine a decis și când, nota.
    2. **Context:** cameră, locație, ora, viteză (~km/h, prag), tipul obiectului.
    3. **Istoric · audit:** timeline vertical (Detecție automată → Vizualizat de … → Confirmat …), ultimele 5 intrări.
- **Player-ul (componentă reutilizabilă):**
  - clipul (±3 s în jurul evenimentului) se ia din memorie, deci derularea e instantă;
  - pornește automat, mut, în buclă, la **viteza 0,25×** (opțiuni 0,25 / 0,5 / 1);
  - bara de progres are un **romb roșu la mijloc**: momentul evenimentului, pe care se poate da click;
  - butoane: −1 s, cadru ‹, play/pauză, cadru ›, +1 s, timp `0:01.5 / 0:06.0`, „Eveniment” (sare la moment), viteză, ecran complet, descarcă;
  - scurtături: spațiu, ←/→, `,` / `.`;
  - stări: încărcare cu procent; „Clip video indisponibil” cu text explicativ.

### 5. Camere `/app/camere`
- **Header:** titlul „CAMERE DE TRAFIC”, „N online · M fără semnal”, comutator Grilă / Hartă și butonul „+ Adaugă cameră” (modal cu formular; nota că fluxurile RTSP/ONVIF vin după integrare).
- **Grilă:** 5 coloane de carduri 16:10.
  - Fiecare card are: bara de sus cu numele camerei și „ultima alertă dd.mm hh:mm”, imaginea (ultimul cadru cheie sau un instantaneu static `/cams/<slug>.jpg`), badge-urile „● Online” și „N alerte”, iar jos numele, starea și „N alerte deschise”.
  - **La hover:** „Redă clipuri” (modal cu player mare și toate clipurile camerei, ‹ › între ele, „Dosar alertă”) și „Istoric” (arhiva filtrată pe cameră).
- **Mod Hartă:** harta pe toată suprafața.

### 6. Arhivă `/app/arhiva`
- **Stânga, zona principală:**
  - bară de căutare în limbaj natural;
  - „Căutări rapide:” cu chip-uri prestabilite (Viteză peste 100 km/h, Depășiri de viteză, Schimbări de bandă periculoase, Frânări bruște, Accidente probabile, Camioane implicate, Pasaj Mihai Eminescu noaptea, Centura Iași), plus „Resetează”;
  - rândul „Am înțeles:” cu chip-urile filtrelor interpretate și „+ Adaugă filtru”;
  - sumarul „N clipuri găsite”;
  - grila de 4 coloane cu carduri video: miniatură, eticheta tipului de eveniment, ▶ la hover care deschide **player-ul mare în modal**, apoi cameră, oră și clasa vehiculului.
- **Dreapta, panoul „Filtrare avansată”:** checkbox-uri pentru Camere și Tip vehicul, slider pentru Durata minimă.

### 7. Statistici `/app/statistici`
- **Header:** perioada și „Exportă raport”.
- **Rândul 1, 4 KPI-uri:** Total alerte · Alerte confirmate (%) · Timp mediu de reacție · Alarme false (%).
- **Rândul 2:** grafice pe gravitate și pe tip.
- **Rândul 3:** grafic pe camere și heatmap „Distribuție oră × zi” (00–23).

Totul se calculează **doar din alertele afișate**.

### 8. Setări `/app/setari` (admin)
- Simulare flux live (generează alerte, semnal sonor la incidente critice, resetează demo-ul);
- Confidențialitate și GDPR (blur implicit, garanții: decizia aparține operatorului);
- tabelul utilizatorilor (Utilizator, Nume, Unitate, Drepturi).

### 9. Audit `/app/audit` (extra)
Filtre (utilizator, acțiune), „Exportă CSV”. Tabel: Timestamp · Utilizator · Acțiune · Țintă/dosar · Detalii.

### 10. Patrule și Reguli (extra, MOCK)
- **Patrule:** tabel cu Indicativ · Vehicul · Zonă · Stare · Alertă curentă.
- **Reguli & zone:** carduri ACTIVĂ / INACTIVĂ cu pragurile fiecărei reguli.

## Date (API real, prin același domeniu, cookie de sesiune + header `X-CSRF-Token`)
- **Autentificare:** `GET /api/auth/csrf`, `POST /api/login {operator, password}`, `GET /api/auth/me` (rolul: `tenant_admin` → admin), `POST /api/logout`.
- **Alerte și camere:**
  - `GET /api/events`: listă `{id, camera_id, type, priority, occurred_at, speed_kmh, object_class, rule, details, keyframe_url, clip_url, status: new|confirmed|rejected}`;
  - `GET /api/events/:id` (cu `audit[]`) și `POST /api/events/:id/view`;
  - `POST /api/events/:id/decision {decision: confirm|reject, action, note}`. La confirmare, `action` este obligatoriu și ia una din valorile `dispatch_patrol | warning_sign | enforcement | monitor`; 409 înseamnă că alerta e deja decisă.
  - `GET /api/cameras`, `GET /api/stats`, `GET /api/meta` (etichetele tipurilor), `GET /api/audit?limit=100`, `GET /api/search?q=`, flux SSE pentru alerte noi.
- **Media:** `keyframe_url` și `clip_url` sunt URL-uri semnate `/api/media/<uuid>?exp=&sig=`. Serverul **nu suportă Range**, deci clipurile se descarcă întregi (fetch → blob) și se redau din memorie. Cheia de cache e calea fără query.
- **Tipuri de alertă:** probable_crash, wrong_way, pedestrian_on_road, tailgating, dangerous_lane_change, hard_braking, stopped_on_road, stopped_emergency_lane, very_high_speed, congestion.

## Strat demo pentru pitch (doar în frontend, păstrează-l separat, ex. `lib/demo.ts`)
- Denumirile camerelor din Iași după slug: demo-highway „Centura Iași – DN28, pasarelă”, demo-urban „Pasaj Octav Băncilă”, mx-avenue „Bd. Ștefan cel Mare și Sfânt”, mx-bridge-night „Pasaj Mihai Eminescu (noapte)”, mx-interchange „Nod rutier Podu Roș (vedere de sus)”, mx-junction „Intersecție Piața Unirii”.
- Se ascund tipul `pedestrian_on_road` și o listă de ID-uri curate manual (alerte false și duplicate). Alertele de viteză care sunt de fapt **nepăstrarea distanței** (ID-urile 107, 96, 99, 100) se reclasifică.
- Timpii relativi din coadă sunt simulați după poziție (prima alertă „acum câteva secunde”, apoi crescător) și curg în timp real.
- Patrulele sunt MOCK (IS-21/14/07/33-POL; Copou, Podu Roș, Tătărași, Nicolina).

## Ce NU trebuie să apară
- Verificare AI, procente de încredere, verdict VLM;
- pagina cu jurnalul / lista de alerte;
- etichete inventate (km, ETA, nume de patrule în date reale);
- scroll de pagină în aplicație;
- referințe la București.
