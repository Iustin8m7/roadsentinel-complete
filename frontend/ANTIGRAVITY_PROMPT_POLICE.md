Ești designerul UI al aplicației RoadSentinel, o interfață de dispecerat pentru poliția rutieră care monitorizează camerele de trafic cu AI.

LOCAȚIA PROIECTULUI: C:\Users\Calin\Desktop\costan calin pfa\roadsentinel\frontend
(Vite + React 19 + TypeScript + Tailwind 4). Pornire: npm install, apoi npm run dev → http://localhost:5173.
Logica e gata și funcțională. Tu faci DOAR designul vizual și layout-ul. Citește întâi DESIGN_BRIEF.md și README.md.

SARCINA: înlocuiește complet designul actual (stil Matrix/terminal) cu un stil „POLICE BADGE”, după imaginea atașată design-ref/moodboard-badges.png: insigne flat vectoriale bleumarin + auriu, panglici, stele, lauri.

## 1. CERINȚA PRINCIPALĂ: DASHBOARD FĂRĂ SCROLL
- Fiecare secțiune (Panou, Alerte, Dosar alertă, Camere, Patrule, Reguli, Arhivă, Statistici, Audit, Setări) încape integral în ecran (100vh) pe desktop 1366×768 până la 1920×1080. Pagina NU are scroll.
- Layout cu CSS Grid pe înălțime fixă: `html, body, #root { height: 100% }`, shell `height: 100vh; overflow: hidden`, zona de conținut `grid` cu `min-height: 0`.
- Fiecare pagină e un grid de „widget-uri” (tile-uri). Când o listă are mai multe elemente decât încap (coada de alerte, tabele, audit, rezultatele căutării), scroll-ul e DOAR în interiorul acelui widget (`overflow: auto`, scrollbar subțire stilizat), cu header-ul widget-ului fix (sticky).
- Densitate: font de bază 13–14px, padding compact, KPI-uri pe un singur rând sus, fără spații goale mari.
- Sub 1024px (tabletă/telefon) se acceptă scroll normal pe pagină, cu widget-urile unul sub altul.

Layout propus pe pagini:
- Panou: rând KPI (4–5 insigne-KPI) | dedesubt grid 12 coloane: Coada de alerte (7 col, toată înălțimea rămasă) + coloana dreaptă (5 col) cu Hartă camere (sus) și Patrule + Distribuție gravitate (jos).
- Alerte: bară de filtre compactă + tabel care umple restul înălțimii (scroll intern).
- Dosar alertă: 3 coloane. Stânga (video + cadre cheie). Mijloc (verdict VLM + context). Dreapta (decizie, acțiuni, istoric audit cu scroll intern).
- Camere: grid de monitoare care se adaptează ca toate 10 să încapă (5×2 pe desktop).
- Statistici: 4 KPI + 4 grafice în grid 2×2, fiecare grafic umple tile-ul (ResponsiveContainer).
- Celelalte: același principiu (header pagină compact + tile-uri care umplu ecranul).

## 2. PALETĂ (din imagine)
- Fundal aplicație: gri-albastru ardezie ca în imagine, #5F6B7F, cu gradient subtil spre #525D70 și o textură fină de zgomot sau grilă de puncte la 4–6% opacitate. Culoarea asta îmi place, păstreaz-o.
- Bleumarin (panouri, sidebar, insigne): #1E2B4A, #233358 (suprafețe), #2E4170 (hover / borduri interioare).
- Auriu (accent principal, panglici, stele, titluri): #F5B82E, #E9A21B (umbră), #FFD36B (highlight).
- Text: alb-crem #F4F1E8 pe bleumarin, bleumarin #1E2B4A pe auriu, gri deschis #AEB8CC pentru secundar.
- Gravitate, cu formă de insignă diferită, nu doar culoare:
  - Critică: roșu #E5484D, insignă stea cu 6 colțuri + eticheta CRITIC
  - Ridicată: portocaliu #F2994A, scut + RIDICAT
  - Medie: auriu #F5B82E, cerc + MEDIU
  - Informativă: albastru deschis #5B9BF0, pătrat rotunjit + INFO
- Totul ca tokens în src/index.css (@theme Tailwind 4 + variabile CSS). Elimină complet stilurile Matrix (ploaie de caractere, scanlines, verde, monospace peste tot, glitch).

## 3. TIPOGRAFIE (Google Fonts, în index.html)
- Titluri, etichete pe panglici, cifre KPI: „Oswald” sau „Bebas Neue”, UPPERCASE, letter-spacing 0.06em. Alternativ „Teko” pentru cifre.
- Text și tabele: „Inter” sau „Barlow”, 13–14px.
- ID-uri, ore, viteze: „Roboto Mono”, cu cifre tabulare.

## 4. STILUL VIZUAL „INSIGNĂ”
- Widget-urile sunt panouri bleumarin cu colțuri rotunjite 14–16px, contur interior auriu subțire (1px la 40%), umbră moale jos (ca insignele din imagine), fără glow neon.
- Antetul fiecărui widget e o PANGLICĂ aurie (ribbon cu capete crestate, din CSS clip-path sau SVG) cu titlul în Oswald bleumarin, plus o iconiță într-un mic cerc/stea în stânga. În dreapta: contor / acțiuni.
- Ornamente discrete preluate din imagine: stele mici ★ pe panglici, lauri stilizați la insignele mari, linii orizontale (chevron) pe headere.
- KPI-urile sunt INSIGNE: fiecare KPI e o insignă (scut / cerc / stea) cu cifra mare în centru și eticheta pe panglica de dedesubt.
- Butoanele: primar auriu cu text bleumarin (pastilă, umbră jos), secundar bleumarin cu contur auriu, pericol roșu. Stările de hover/focus sunt clare (focus ring auriu).
- Badge-urile de stare (Nouă, În verificare, Confirmată, Respinsă, Închisă) sunt mici pastile cu iconiță.
- Iconițe: lucide-react (deja instalat), în cercuri sau insigne mici.

## 5. SIGLE / INSIGNE (generate de tine, SVG)
- Creează un set ORIGINAL de insigne RoadSentinel în stilul imaginii (flat, bleumarin + auriu, scut, stea, panglică, lauri). NU copia și NU imita stema, sigla sau însemnele oficiale ale Poliției Române / MAI. Nu scrie „POLIȚIA ROMÂNĂ”. Folosește „ROADSENTINEL”, „DISPECERAT RUTIER”, „UNITATE RUTIERĂ”, anul „2026”.
- Variante, în src/assets/brand/ ca SVG + componentă <Logo variant="full|mark|badge|star" />:
  1. Emblema principală (login + sidebar): scut cu stea aurie în centru, un ochi/cameră stilizată în stea, panglică „ROADSENTINEL” și lauri.
  2. Monogramă „RS” într-o stea cu 6 colțuri (sidebar colapsat, favicon → actualizează public/favicon.svg).
  3. Insignă de unitate pentru patrule (scut cu indicativul, ex. B-21) și pentru rolul utilizatorului (ADMIN / OPERATOR / ANCHETATOR / PATRULĂ, fiecare cu altă formă: stea, scut, cerc, insignă cu aripi).
  4. Insigne pentru tipurile de gravitate (vezi paleta).

## 6. ECRANE
- LOGIN: fundal ardezie ca în imagine, cu un pattern discret de insigne mici estompate. În centru, emblema mare (scut + stea + lauri) și dedesubt un card bleumarin cu panglica „AUTENTIFICARE”. Câmpuri cu fundal bleumarin închis și contur auriu la focus, buton auriu „INTRĂ ÎN SISTEM”. Eroarea apare pe o panglică roșie. Textul „Sistem de alertare rutieră pentru poliție” și nota de audit rămân.
- SHELL: sidebar bleumarin îngust (icon + text), emblema sus, link activ cu bară aurie și fundal #2E4170. Topbar compact: ceas, indicator „FLUX LIVE” (punct verde pulsând discret), insignă roșie cu numărul de critice deschise, profilul utilizatorului cu insigna rolului.
- ALERTE (în coadă): fiecare alertă e un rând-card compact: insigna de gravitate în stânga, titlu + cameră, verdict VLM ca pastilă cu procent, timp scurs în dreapta. Cele critice au fundal ușor roșiatic și o bordură stângă roșie groasă; o alertă nouă intră cu o animație scurtă de slide + highlight auriu.
- TOAST critic: card bleumarin cu panglică roșie „ALERTĂ CRITICĂ”, insignă-stea, butoane „DESCHIDE DOSARUL” / „ÎNCHIDE”.
- DOSAR: video placeholder ca monitor cu ramă bleumarin și overlay (ID cameră, oră, REC), cadre cheie ca miniaturi. Verdictul VLM e un card cu insignă „VERIFICARE AI”. Butoane mari CONFIRMĂ (auriu) / RESPINGE (roșu). Istoric ca timeline cu puncte-stea.
- HARTĂ: react-leaflet cu tile-uri sobre (de ex. CARTO Positron sau Voyager) în tile bleumarin, camerele ca mici insigne-pin (stea/scut) colorate după stare și alerta deschisă. Coordonatele sunt în src/mocks/cameras.ts.
- STATISTICI: instalează recharts; bare și linii aurii/albastre pe bleumarin, grilă discretă, tooltip ca mică insignă.
- CAMERE: monitoare cu ramă bleumarin și panglică cu numele camerei; offline = „FĂRĂ SEMNAL” pe panglică roșie.
- REGULI: carduri compacte cu toggle auriu; editorul se deschide inline sau într-un drawer lateral (fără să creeze scroll de pagină).

## 7. MIȘCARE
- Animații scurte (150–250ms): hover pe insigne (ridicare ușoară + umbră), intrarea widget-urilor în cascadă, pulsul discret la critice.
- Fără animații de fundal continue. Respectă prefers-reduced-motion.

## 8. REGULI STRICTE
- NU modifica: src/store/*, src/mocks/*, src/lib/*, src/hooks/*, src/types/*, rutele din src/App.tsx, src/components/guards.tsx, props-urile componentelor din src/components/ui.tsx, apelurile către store și verificările useCan(...).
- Toate textele rămân în ROMÂNĂ. Păstrează: „Decizia rămâne la om…”, blur implicit, „±3–5 km/h, doar triaj”, nota de audit de pe login.
- Contrast WCAG AA: text crem pe bleumarin, text bleumarin pe auriu; fără text auriu mic pe fundalul ardezie.
- Gravitatea se distinge și fără culoare (formă de insignă + text).
- La final npm run build trece fără erori. Verifică la 1366×768 și 1920×1080 că NICIO pagină nu are scroll vertical (doar în widget-uri). Testează cu admin / admin și patrula / patrula.

## LIVRABILE
1. src/index.css rescris (tokens police, panouri-insignă, panglici, layout 100vh).
2. Set de insigne SVG + componenta <Logo /> în src/assets/brand/, favicon nou.
3. Componente noi în src/components/: BadgePanel (widget cu panglică), RibbonHeader, BadgeKpi, SeverityBadge (insignă pe formă), RoleBadge, CameraMonitor, plus layout-ul DashboardGrid fără scroll.
4. Toate paginile restilizate și rearanjate pe ecran fix.
5. Componentele Matrix eliminate (MatrixRain etc.), dacă există.
6. O notă scurtă în DESIGN_BRIEF.md cu noul stil și tokenii principali.
