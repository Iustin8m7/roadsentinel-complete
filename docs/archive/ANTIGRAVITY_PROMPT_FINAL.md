Implementează 1:1 designul din cele 8 imagini atașate (Design System, Landing, Login, Panou, Dosar alertă, Camere, Arhivă, Statistici) în aplicația existentă RoadSentinel.

## PROIECT
- Folder: C:\Users\Calin\Desktop\costan calin pfa\roadsentinel\frontend  (Vite + React 19 + TypeScript + Tailwind 4 + React Router 7 + Zustand, lucide-react)
- Rulare: npm install, apoi npm run dev → http://localhost:5173 (proxy /api și /media către http://localhost:8000).
- Branch git: feat/simple-auth. Lucrezi DOAR local; nu face commit, push sau deploy. Deploy-ul îl facem noi la final.
- Backend real: backend/ (FastAPI). Contractul API e în ../API.md. Login: admin / <demo-password> și operator / <demo-password> (fără MFA).

## REGULA DE DATE (foarte important)
Tot ce există în backend se citește din API-ul real. Ce nu există încă se face cu date mock, ținute într-un singur loc (src/mocks/ + store), marcate în cod cu `// MOCK:` ca să le putem înlocui ulterior.

| Element din design | Sursă |
|---|---|
| Login / logout / sesiune | REAL: POST /api/login {operator, password}, POST /api/logout, GET /api/me (cookie + header CSRF din GET /api/auth/csrf; vezi src/lib/api.ts, păstrează-l) |
| Coada de alerte, lista de alerte | REAL: GET /api/events (id, type, priority, camera_name, location, occurred_at, video_t, object_class, speed_kmh, rule, keyframe_url, clip_url, vlm_status, vlm_text, status, action) |
| Alerte noi în timp real | REAL: GET /api/stream (SSE, evenimentele `alert` și `audit`) |
| Dosar alertă: detalii + istoric | REAL: GET /api/events/{id} (Event + audit[]); POST /api/events/{id}/view la deschidere |
| Confirmă / Respinge + acțiune | REAL: POST /api/events/{id}/decision {decision: confirm\|reject, action, note}; 409 = deja decis → reîncarcă |
| Etichete tipuri + lista de acțiuni | REAL: GET /api/meta |
| Player video, cadru cheie, „Descarcă clip” | REAL: clip_url și keyframe_url (cer cookie, se folosesc direct în <video>/<img>; „Descarcă clip” = link download către clip_url) |
| Camere (nume, locație, video) | REAL: GET /api/cameras; MOCK: miniaturi, telemetrie, viteză medie, „ultima imagine”, harta camerelor când lipsesc coordonatele |
| Căutare în arhivă | REAL: GET /api/search?q= → {filter.explanation, results: Event[]} (chip-urile „Am înțeles” din filter); MOCK: procentul „Potrivire %”, filtrele avansate din dreapta aplicate client-side |
| Statistici: total, pe gravitate, pe tip | REAL: GET /api/stats (by_priority, by_status, by_type) |
| Statistici: trend „vs luna trecută”, timp mediu de reacție, pe cameră, heatmap oră × zi | MOCK, sau calculat client-side din GET /api/events când e posibil (pe cameră și heatmap din occurred_at) |
| Patrule, distanțe, ETA, „Trimite patrulă B-21”, pozițiile pe hartă | MOCK (backend-ul are doar acțiunea dispatch_patrol în decizie: butonul trimite decizia reală cu action=dispatch_patrol și afișează patrula mock) |
| Jurnal de audit | REAL: GET /api/audit?limit=200 |
| Selector „Ultimele 30 de zile”, „Exportă raport” | Export CSV client-side din datele încărcate; intervalul filtrează client-side |
| Landing page, „Ai uitat parola?”, „Adaugă cameră” | Static / MOCK (ai uitat parola → mesaj „Contactați administratorul”; adaugă cameră → modal care afișează mesajul „disponibil după integrarea pipeline-ului”) |

Nu modifica backend-ul. Dacă un endpoint lipsește, folosește mock și notează-l în README-ul din frontend, secțiunea „De integrat”.

## DESIGN SYSTEM (din imaginea „RoadSentinel UI Design System”)
Tokens în src/index.css (@theme Tailwind 4 + variabile CSS); elimină toate stilurile vechi (insigne aurii, panglici, Matrix).
- Fundal: Deep Void #0A0E14 · Panel #111821 · Elevation #17202B · Borders/Dividers #1E2A36
- Text: Primary #E6EDF3 · Secondary #7D8A9B
- Stări: Critical #FF3B3B · Warning/Ridicat #FF8A1F · Caution/Mediu #FFC23D · Info/Action #3DA5FF · Active/OK #2ED47A
- Fonturi (Google Fonts): Inter (UI), Barlow Condensed (KPI, titluri de pagină, cifre mari), JetBrains Mono (timestamp-uri, ID-uri, coordonate, overlay CCTV)
- Componente: badge-uri de gravitate tip pastilă cu punct (CRITIC/RIDICAT/MEDIU/INFO); buton primar albastru cu glow; RESPINGE roșu; CONFIRMĂ verde; Disabled gri; card KPI (titlu, cifră mare, sparkline verde, delta „+2 de la ultima oră”); rând de alertă (ID, gravitate, tip, timestamp, stare, Action, …); indicatori ONLINE/OFFLINE; input de căutare cu focus ring albastru; iconițe line 1px 24×24 (lucide).
- Colțuri 8–12px, borduri 1px #1E2A36, fără umbre grele; accent glow doar pe primar și pe alertele critice.

## ECRANE (copiază exact layout-ul din imagini)
1. LANDING `/` — header (logo RoadSentinel + „Cum funcționează”, „Securitate”, „Contact”, buton „Autentificare →”), hero „Fiecare cameră, un ochi care nu doarme.” + subtitlu, butoanele „Intră în dispecerat →” (→ /login) și „Vezi demo”; în dreapta un monitor CCTV cu colțuri albastre, bounding boxes (autoturism 0.97, camion 0.94, SENS INTERZIS) și bara „CAM-07 · A1 km 23 · 18:42:07” (folosește un cadru real din /media dacă există, altfel o imagine statică din public/); fundal cu linii de drum și noduri luminoase; jos bandă cu 4 pași (1 Detecție → 2 Reguli → 3 Verificare AI → 4 Alertă roșu). Adaugă sub fold secțiunile „Cum funcționează”, „Securitate” (decizia la om, fără recunoaștere facială, blur, GDPR/2016/680, audit) și „Contact”.
2. LOGIN `/login` — fundal hartă stradală întunecată, card centrat cu logo + „RoadSentinel”, „Acces securizat dispecerat”, Utilizator (icon user), Parolă (icon lacăt + ochi afișare), „Ține-mă minte”, „Ai uitat parola?”, buton „Intră în sistem”, sub card „Acces exclusiv personal autorizat · Toate acțiunile sunt auditate”, stânga-jos în mono „● Sistem operațional · 9/10 camere online” (cifrele din /api/cameras).
3. SHELL — sidebar îngust vertical: logo sus, iconițe + etichete (Panou, Alerte, Camere, Arhivă, Statistici, Setări), item activ cu bară albastră în stânga, „v2.4” jos. Topbar per pagină: titlu „Secțiune / Subtitlu” în Barlow Condensed, căutare, ceas mare HH:MM:SS, avatar + inițiale + status.
4. PANOU `/app` — 4 KPI cu sparkline (Alerte deschise, Camere online 9/10, Patrule disponibile 4/6 cu bară, Rată alarme false); „Coada de alerte” cu carduri: miniatura cadrului cheie pentru prima/critice, titlu UPPERCASE „SENS INTERZIS – A1 km 23”, badge gravitate, chip „AI: confirmat 96%”, „acum 3 min”, bară laterală colorată după gravitate, card critic cu contur roșu și glow; în dreapta hartă întunecată (react-leaflet cu tile dark CARTO) cu iconițe de camere, mașini de patrulă și puls roșu la alerta critică; „Patrule pe teren” cu stare colorată și distanță.
5. DOSAR ALERTĂ `/app/alerte/:id` — breadcrumb „Alerte / #A-2041”, titlu + badge gravitate + pastila „În verificare”, ceas; player mare tip CCTV (colțuri albastre, overlay mono cu cameră și oră, bounding box cu clasa și încrederea), bară de timp cu marker roșu ⚠ la momentul alertei, controale −5s / play / +5s / 1× (viteză 0.25–2×), „Descarcă clip”; filmstrip de cadre cu ora, cadrul alertei evidențiat portocaliu; în dreapta „Verificare AI” cu inel de progres (procent) și descrierea vlm_text; „Context” (Cameră, Regulă, Viteză, Durată); „Primary Actions”: CONFIRMĂ verde / RESPINGE roșu (respingerea cere notă într-un modal); „Secondary Action”: „Trimite patrulă B-21” cu „la 4,2 km · ETA 5 min”; jos „Istoric eveniment” ca timeline orizontală (Detecție, Regulă declanșată, Verificare AI, Alertă creată, Deschisă de dispecer) din audit[].
   PLAYER: dacă există înregistrarea completă a camerei (video_url din /api/cameras), pornește la video_t − 3 s și pune marker la video_t; altfel redă clip_url (clip de ±3 s în jurul evenimentului) cu markerul la mijloc.
6. CAMERE `/app/camere` — titlu „Camere de trafic”, sub-titlu „9 online · 1 fără semnal”, comutator Grilă / Hartă, buton „Adaugă cameră”; grilă 5 coloane de monitoare: bară sus mono (CAM-xx · coordonate · oră), pastila Online, badge cu numărul de alerte (portocaliu/roșu/gri), imagine, jos „CAM-01 · A1 km 12 · LIVE” + stare și telemetrie mono; camera offline cu ⚠ și „Fără semnal · ultima imagine 17:58”; la hover butoanele „Deschide” / „Istoric”.
7. ARHIVĂ `/app/arhiva` — bară mare de căutare (icon lupă + baghetă AI, buton „Caută →”), chip-uri „Am înțeles:” cu ×, „+ Adaugă filtru”, „N clipuri găsite · sortate după relevanță”; grilă 4 coloane de carduri video (miniatură cu bounding box, durată, cameră · loc, „ieri · 15:37”, „Potrivire 92%” colorat), play la hover; în dreapta panou „FILTRARE AVANSATĂ” (Camere cu checkbox-uri, Tip vehicul, Durată minimă cu slider).
8. STATISTICI `/app/statistici` — titlu „Statistici / Analiză și performanță”, selector „Ultimele 30 de zile”, „Exportă raport”; 4 KPI (Total alerte cu „+14% vs luna trecută”, Alerte confirmate %, Timp mediu reacție, Alarme false %) cu săgeți de trend; donut „Alerte pe gravitate” cu legendă și procente; „Alerte pe tip” cu bare orizontale colorate și valori; „Alerte pe cameră” bare verticale colorate după gravitatea dominantă; heatmap „Distribuție oră × zi” (Lun–Dum × 00–23, scală albastru → portocaliu → roșu). Folosește recharts.
9. Păstrează și restilizează în același sistem paginile existente: Alerte (listă), Patrule, Reguli, Audit, Setări, 403, 404.

## CERINȚE
- Textele în română exact ca în imagini (corectează doar typo-urile din imagini, ex. „camioane”).
- Desktop 1440–1920 fără scroll de pagină pe Panou, Dosar și Statistici (scroll doar în panouri); responsive pe tabletă/telefon.
- Stări de încărcare (skeleton), gol și eroare cu „Reîncearcă”; sesiune expirată (401) → /login.
- Gravitatea se distinge și fără culoare (text + punct/formă).
- Logo: scut cu ochi și drum, ca în imagini (SVG original, în src/assets/brand/), fără însemnele oficiale ale Poliției Române.
- La final: `npx tsc -b` și `npm run build` fără erori; testează login-ul demo pe backend-ul local.
- Listează la final ce e REAL și ce e MOCK.
