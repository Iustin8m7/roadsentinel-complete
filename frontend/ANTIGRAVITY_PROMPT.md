# Prompt pentru Antigravity — RoadSentinel „Matrix”

> Lipește tot textul de mai jos în Antigravity. Poți atașa și `design-ref/moodboard-eye.png` ca referință pentru motivul „ochiului din cod” (dar culorile sunt cele de mai jos, verde Matrix, nu cyan).

---

Ești designerul UI al aplicației **RoadSentinel**, o interfață de dispecerat pentru poliția rutieră care monitorizează camerele de trafic cu AI.

**Locația proiectului:** `C:\Users\Calin\Desktop\costan calin pfa\roadsentinel\frontend` (Vite + React 19 + TypeScript + Tailwind 4). Deschide acest folder ca workspace. Pornire: `npm install`, apoi `npm run dev` → http://localhost:5173. **Logica e gata și funcțională** — tu faci doar designul vizual și UX-ul. Citește întâi `DESIGN_BRIEF.md` (ce ai voie și ce nu ai voie să modifici) și `README.md` din acest folder.

## Concept: „Sistemul vede codul din spatele traficului”

Stil **Matrix**: totul pare un terminal care rulează pe un monitor cu fosfor verde. Ploaie de caractere care cade pe verticală, text verde strălucitor pe negru, interfețe de tip consolă, efecte de decodare. Vreau **efect wow la prima vedere**, dar operatorul trebuie să poată lucra 12 ore fără să obosească: efectele sunt pe fundal și pe accente, nu peste conținut.

### Paletă
- Fundal: negru absolut cu tentă verde `#000000` → `#010A04`, cu vignetă.
- Verde Matrix (accent principal): `#00FF41` (strălucitor), `#00C832` (mediu), `#008F11` (stins), `#003B00` (borduri / grile).
- Text principal: verde pal `#B8FFC8`, ca să fie lizibil (nu tot textul în `#00FF41`). Text secundar: `#4E8F5A`.
- Glow: `text-shadow` / `box-shadow` verde la 30–50%, doar pe titluri, cifre mari, accente și elemente active.
- Gravitate: păstrează lumea verde, dar alertele grave trebuie să „rupă” Matrix-ul:
  - **Critică:** roșu „red pill” `#FF2B2B`, cu glow și efect glitch
  - **Ridicată:** chihlimbar `#FFB000` (ca un monitor de fosfor ambră)
  - **Medie:** verde-gălbui `#C6FF00`
  - **Informativă:** verde Matrix `#00FF41`
- Definește totul ca tokens în `src/index.css` (`@theme` Tailwind 4 + variabile CSS). Dark e singurul mod principal. Light mode e opțional, dar nu trebuie să se strice.

### Tipografie (totul monospace)
- Titluri, brand și cifre mari: **VT323** sau **Share Tech Mono** (Google Fonts), mari, cu glow.
- Text și date: **JetBrains Mono** sau **IBM Plex Mono**, 14–15px, cu cifre tabulare.
- Etichete de secțiune în stil prompt de terminal, ex. `root@roadsentinel:~$ alerte --open --sort=gravitate` sau `> COADĂ ALERTE [08]`.
- Cursor care clipește `█` la titluri sau câmpuri active.

### Delimitarea secțiunilor
- Panouri ca **ferestre de terminal**: bordură de 1px `#003B00`, cu o bară de titlu sus (`┌─[ PANOU DISPECERAT ]────── ● LIVE ─┐`, desenată cu caractere box-drawing sau CSS).
- Colțuri drepte, fără rotunjiri mari. Separatoare din linii punctate sau `─────`.
- Fundal global: **ploaie digitală Matrix** pe `<canvas>`: coloane de caractere (katakana jumătate de lățime, cifre 0–9 și câteva litere) care cad, cu primul caracter alb-verde strălucitor și trena care se stinge. Pe fundal opacitatea e mică (≤ 8–10%), mai intensă doar pe login.
- Scanlines CRT foarte subtile (gradient repetat) și un ușor flicker doar pe login.
- Performanță: canvas la max ~30fps, oprit când tab-ul e ascuns și dezactivat complet la `prefers-reduced-motion`.

### Siglă și identitate
- Creează o **emblemă originală RoadSentinel** în SVG, fără să copiezi stema, sigla sau însemnele oficiale ale Poliției Române / MAI și fără să le imiți îndeaproape. Direcție: **un scut hexagonal desenat din linii verzi, cu un ochi stilizat în centru, iar irisul format din caractere/cod**; o bandă de drum trece prin pupilă. Variante:
  1. emblemă completă (login): se „decodează” la încărcare, adică caracterele aleatoare se transformă în emblemă,
  2. monogramă `RS` în hexagon (sidebar, favicon),
  3. insignă mică de unitate pentru patrule / utilizator (ex. `[B-21]` într-un scut).
- Salvează-le în `src/assets/brand/` ca SVG și ca componentă `<Logo variant="full|mark|badge" />`. Actualizează `public/favicon.svg`.
- Pe login poți scrie „Sistem de alertare rutieră pentru poliție”. Nu folosi denumiri sau însemne oficiale ca și cum aplicația ar fi produsul unei instituții reale.

## Ecrane — ce vreau să fie „wow”

**Login (`/login`)**: ploaie Matrix pe tot ecranul. În centru apare emblema, apoi un text tastat literă cu literă: `Wake up, operator...` → `Sistem de alertare rutieră. Autentificare necesară.` Formularul arată ca o fereastră de terminal cu prompturi: `login: _` și `password: ****`. La autentificare reușită: `ACCESS GRANTED`, ploaia accelerează scurt și se trece în aplicație (≤ 1s). La eroare: `ACCESS DENIED` în roșu, cu glitch scurt și shake.

**Shell (sidebar + topbar)**:
- Sidebar ca listă de comenzi de terminal: `> panou`, `> alerte [8]`, `> camere`… Elementul activ e evidențiat invers (fundal verde, text negru) și are cursor `█`.
- Topbar ca bară de status: ceas `HH:MM:SS` care curge, `FEED: LIVE ●` pulsând, uptime, numărul de camere online și contorul de critice în roșu cu glitch. În dreapta, utilizatorul ca `user: admin@brigada-rutiera [ADMIN]`.

**Panou dispecerat (`/`)**:
- KPI-uri ca **cifre mari VT323** care se „decodează” la încărcare (caractere aleatoare care se opresc pe valoarea reală), cu bare ASCII de progres `[█████░░░░░] 52%`.
- Coada de alerte e elementul central (vezi mai jos).
- **Hartă tactică** verde pe negru: puncte ale camerelor care pulsează când au alertă deschisă (`react-leaflet` cu tile dark și filtru CSS verde, sau o hartă SVG wireframe; coordonatele sunt în `src/mocks/cameras.ts`).
- Patrulele ca listă de terminal: `[B-21] SECTOR 6 / A1 ........ DISPONIBIL`.

**Alertele — complet altfel decât un tabel:**
- Fiecare alertă e un **bloc de log**: `[12:07:12] CRIT  SENS_INTERZIS  CAM-BUN-02  VLM:CONFIRMAT 94%` pe o linie, iar dedesubt titlul în română și camera. Bară verticală de gravitate în stânga.
- Gravitatea se vede **și fără culoare**: etichete text fixe (`[CRIT]`, `[HIGH]`, `[MED]`, `[INFO]`) și simboluri diferite (`▲▲`, `▲`, `■`, `·`).
- **Critic:** roșu, cu efect **glitch** (decalaj RGB scurt, la câteva secunde, nu continuu), bordură roșie pulsantă și eticheta `!! BREACH !!` sau `!! CRITIC !!`.
- **Ridicat:** ambră, cu glow static. **Mediu/Info:** verde, discret.
- O alertă nouă din fluxul live apare ca o linie care se **tastează** de la stânga la dreapta, cu un flash scurt.
- **Toast-ul** pentru critice: fereastră de terminal roșie în colț, `>>> INCOMING ALERT <<<`, cu o bară ASCII de timp care se golește și comenzile `[ENTER] DESCHIDE DOSARUL` / `[ESC] IGNORĂ` (fă și tastele să funcționeze).
- Pagina `/alerte` rămâne tabel pentru densitate, dar stilizat ca output de terminal: rânduri monospace, hover cu fundal verde închis, header sticky, filtre ca flag-uri `--severitate=critica`.

**Dosarul alertei (`/alerte/:id`)** — cel mai important ecran:
- Playerul video placeholder arată ca **feed-ul unei camere de supraveghere văzut prin Matrix**: tentă verde, scanlines, `REC ●`, ID cameră și timestamp care curge, cutii de detecție (bounding boxes) verzi desenate cu CSS, cu etichete `VEHICUL 0.94`.
- Cadrele cheie ca filmstrip, cu marcaje pe o timeline ASCII.
- Verdictul VLM ca panou `> AI_ANALYSIS.log`, cu textul descrierii tastat o singură dată și o bară de încredere ASCII.
- Butoanele de decizie mari: `[ CONFIRMĂ ]` (verde) și `[ RESPINGE ]` (roșu), cu stare de confirmare. Acțiunile (patrulă, panou, constatare) ca butoane-comandă.
- Istoricul de audit ca log de terminal cu timestamp-uri.

**Arhivă (`/arhiva`)**: căutarea e un terminal: `query> camioane oprite pe acostament ieri între 14 și 18█`. Când se caută, rulează câteva linii fake de log (`parsing query... indexing 166 clips... match: 3`). Chip-urile „Am înțeles” apar ca `--vehicul=camion --interval=14-18`. Rezultatele: grilă de thumbnails verzi cu overlay; când blur-ul e activ se vede pixelare.

**Statistici (`/statistici`)**: instalează `recharts`, grafice verzi pe negru cu glow și grilă `#003B00`, tooltip ca terminal. Folosește doar datele din `useStats()`. Heatmap oră × zi în nuanțe de verde, dacă îți permite timpul.

**Camere / Patrule / Reguli / Audit / Setări**: același limbaj de terminal. Camerele sunt monitoare CRT verzi; cele offline afișează zgomot static și `NO SIGNAL`. Regulile sunt linii de config cu toggle-uri `[ON]` / `[OFF]`.

## Mișcare
- Folosește `framer-motion` (sau `motion`) pentru tranziții de pagină scurte (fade + o scurtă decodare a titlului) și intrarea în cascadă a elementelor.
- Efectele de decodare și tastare rulează **o singură dată** la apariție, nu în buclă, și durează ≤ 600ms.
- **Respectă `prefers-reduced-motion`**: fără ploaie, glitch, tastare sau flicker.

## Reguli stricte
- **Nu modifica**: `src/store/*`, `src/mocks/*`, `src/lib/*`, `src/hooks/*`, `src/types/*`, rutele din `src/App.tsx`, `src/components/guards.tsx`, props-urile componentelor din `src/components/ui.tsx`, apelurile către store și verificările `useCan(...)`.
- Păstrează toate textele de conținut în **română**. Fraze scurte în engleză sunt ok doar ca decor de terminal (`ACCESS GRANTED`, `REC`). Păstrează mesajele de garanție: „Decizia rămâne la om…”, blur implicit, „±3–5 km/h, doar triaj”, nota de audit de pe login.
- **Lizibilitate înainte de efecte**: contrast minim WCAG AA, paragrafele în verde pal, nu în neon. Ploaia nu trece niciodată peste text sau peste panouri (panourile au fundal opac sau aproape opac).
- Responsive: dispecerat 1440–1920px, tabletă, telefon (sidebar → bară jos sau drawer).
- Fonturile se încarcă din Google Fonts în `index.html`.
- La final: `npm run build` trebuie să treacă fără erori de TypeScript. Testează login-ul cu `admin / admin`, apoi cu `patrula / patrula` (meniu redus).

## Livrabile
1. `src/index.css` rescris (tokens, panouri de terminal, scanlines, animații).
2. Emblema SVG și componenta `<Logo />` în `src/assets/brand/`, plus favicon nou.
3. Componente vizuale noi (ex. `MatrixRain`, `TerminalPanel`, `DecodeText`, `TypeText`, `AlertLogLine`, `CameraMonitor`, `AsciiBar`) în `src/components/`.
4. Toate paginile restilizate.
5. O scurtă notă în `DESIGN_BRIEF.md` cu deciziile de design și tokenii principali.
