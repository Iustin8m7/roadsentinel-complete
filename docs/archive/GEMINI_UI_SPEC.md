# RoadSentinel — specificație completă de interfață (prompt pentru Gemini)

Ești designer de produs și frontend developer. Generează o interfață web completă, modernă și memorabilă pentru produsul descris mai jos: **landing page public + aplicația de dispecerat**. Stack: React 19 + TypeScript + Tailwind CSS 4, React Router 7, iconițe `lucide-react`, grafice `recharts`, hartă `react-leaflet`. Toate textele în **limba română**.

---

## 1. Produsul

**RoadSentinel** este un sistem de alertare rutieră pentru poliție. Monitorizează automat camerele de trafic cu AI și trimite alerte în timp real către operatorii dispeceratului, cu dovezile deja pregătite pentru verificare.

**Problema:** camerele produc mii de ore de video pe care nimeni nu le poate urmări integral. Incidentele sunt descoperite târziu, de obicei după un apel la 112, iar probele se caută manual în arhive.

**Cum funcționează (4 pași):**
1. **Detecție continuă:** pe fiecare cameră rulează un detector YOLO cu tracking, care urmărește vehiculele și pietonii și calculează viteza, frânările, schimbările de bandă și distanța dintre vehicule.
2. **Reguli configurabile:** fiecare unitate de poliție își definește zonele (bandă de urgență, trecere de pietoni, sens unic) și pragurile (viteză, timp de staționare). Când o regulă e îndeplinită, se generează un eveniment tipizat, explicabil și repetabil.
3. **Verificare cu AI vizual (VLM):** un model vizual-lingvistic analizează doar clipul semnalat, confirmă sau infirmă alerta și scrie o descriere, de exemplu „Camion oprit pe banda de urgență, avarii pornite, două persoane lângă el.” Asta reduce alarmele false.
4. **Alertă către operator:** alerta ajunge pe dashboard, ordonată după gravitate. Operatorul confirmă sau respinge; totul intră în jurnalul de audit.

**Garanții (trebuie să apară vizibil în produs):**
- Decizia rămâne la om. Sistemul alertează și pregătește dovezi, nu sancționează automat.
- Viteza măsurată din video (±3–5 km/h) e doar pentru alertare și triaj, nu pentru amenzi.
- Fără recunoaștere facială și fără urmărirea persoanelor; numerele de înmatriculare și ocupanții sunt blurați în dovezi.
- Conformitate GDPR și Directiva UE 2016/680; fiecare vizualizare și decizie e auditată.

---

## 2. Utilizatori și conturi (demo)

| Utilizator | Parolă | Rol | Ce poate face |
|---|---|---|---|
| `admin` | `<demo-password>` | Administrator | tot: panou, alerte + decizii, camere, patrule, reguli (editare), arhivă, statistici, audit, setări |
| `operator` | `<demo-password>` | Operator dispecerat | panou, alerte + decizii + trimitere patrulă, camere, patrule, reguli (doar citire), arhivă, statistici |

Meniul și butoanele se ascund automat după rol. Sesiunea afișează în topbar: grad + nume (ex. „Comisar-șef Administrator Sistem”, „Agent-șef Andrei Popescu”), rol, insignă (RS-0001 / RS-1042), unitate.

---

## 3. Harta rutelor

| Rută | Ecran | Acces |
|---|---|---|
| `/` (public) | **Landing page** | oricine |
| `/login` | Autentificare | neautentificat |
| `/app` | Panou dispecerat | admin, operator |
| `/app/alerte` | Lista alertelor | admin, operator |
| `/app/alerte/:id` | Dosarul alertei | admin, operator |
| `/app/camere` | Camere | admin, operator |
| `/app/patrule` | Patrule | admin, operator |
| `/app/reguli` | Reguli și zone | admin (editare), operator (citire) |
| `/app/arhiva` | Căutare în arhivă | admin, operator |
| `/app/statistici` | Statistici | admin, operator |
| `/app/audit` | Jurnal de audit | admin |
| `/app/setari` | Setări | admin |
| `*` | 404 / 403 | — |

---

## 4. Modelul de date (ce afișează UI-ul)

**Tipuri de evenimente** (cu gravitate):

| Tip | Etichetă | Gravitate |
|---|---|---|
| `wrong_way` | Sens interzis | Critică |
| `pedestrian_on_road` | Pieton pe carosabil | Critică |
| `very_high_speed` | Viteză foarte mare | Ridicată |
| `stopped_emergency_lane` | Vehicul oprit pe banda de urgență | Ridicată |
| `stopped_on_road` | Vehicul oprit pe carosabil | Ridicată |
| `hard_braking` | Frânare bruscă | Medie |
| `tailgating` | Distanță prea mică | Medie |
| `dangerous_lane_change` | Schimbare de bandă periculoasă | Medie |
| `congestion` | Aglomerare | Informativă |

**Gravitate:** Critică · Ridicată · Medie · Informativă. Trebuie să se distingă și **fără culoare** (iconiță/formă + text).

**Stare alertă:** Nouă · Confirmată · Respinsă (în modul demo și: În verificare, Închisă).

**Verificare AI (VLM):** confirmat · infirmat · incert · în așteptare · omis, plus o descriere de o propoziție și un procent de încredere.

**Acțiuni la confirmare:** Trimite patrulă · Activează panou de avertizare · Transmite către procedura de constatare · Doar monitorizare.

**Alertă (câmpuri):** ID, tip, gravitate, cameră (nume + locație), data/ora, momentul în clip, ID track, clasa obiectului (autoturism, camion, autobuz, motocicletă, pieton), viteza km/h, regula declanșată în text („Viteză 155 km/h > prag 150 km/h (limită 130)”), cadru cheie (imagine), clip video, verdict + text VLM, stare, acțiune, cine a decis și când, notă.

**Cameră:** ID, nume, drum, direcție, coordonate GPS, stare (online / offline / semnal degradat), FPS, calibrată da/nu, reguli active, alerte deschise.

**Patrulă:** indicativ (B-21), vehicul, zonă, stare (disponibilă / în deplasare / la fața locului / în afara serviciului), alerta curentă.

**Regulă:** ID, nume, tip eveniment, zonă (nume + tip: bandă de urgență, trecere de pietoni, sens unic, autostradă, carosabil, intersecție), camere, praguri (viteză, timp de staționare, distanță, decelerare), activă da/nu, ultima modificare (cine, când).

**Intrare audit:** data/ora, utilizator, rol, acțiune (autentificare, deconectare, a vizualizat, a confirmat, a respins, a trimis patrulă, a activat panou, a transmis la constatare, căutare, modificare regulă, export), țintă, detalii.

---

## 5. Ecranele, în detaliu

### 5.1 Landing page (`/`) — NOU, public
Scop: să explice produsul juriului și publicului în 30 de secunde și să ducă spre „Intră în dispecerat”.
- **Hero:** titlu puternic (ex. „Fiecare cameră, un ochi care nu doarme.”), subtitlu cu problema, două butoane („Intră în dispecerat” → `/login`, „Vezi cum funcționează” → ancoră), vizual: un mock de dashboard sau un cadru de cameră cu cutii de detecție animate.
- **Problema în cifre:** mii de ore de video, incidente descoperite târziu, probe căutate manual.
- **Cum funcționează:** cei 4 pași (Detecție → Reguli → Verificare AI → Alertă), cu iconițe și animație de flux.
- **Tipuri de alerte:** tabelul de gravitate ca 4 carduri colorate.
- **Fluxul unei alerte:** detectare → dosar cu dovezi → decizie umană → patrulă / panou / constatare → audit.
- **Căutare în limbaj natural:** demonstrație cu o interogare tastată („camioane oprite pe acostament ieri între 14 și 18”) și rezultate.
- **Garanții și confidențialitate:** decizia la om, fără recunoaștere facială, blur, GDPR / 2016/680, audit.
- **Beneficii:** timp de reacție mai mic, mai puține alarme false, probe automate, statistici pentru decizii (radare, semafoare, patrule).
- **Footer:** „Proiect hackathon 2026”, echipa, link spre login. Fără sigle oficiale ale Poliției Române / MAI.

### 5.2 Autentificare (`/login`)
Utilizator + parolă, „Păstrează-mă autentificat”, buton „Intră în sistem”, stare de încărcare („Se verifică…”), eroare „Utilizator sau parolă incorectă.”, secțiune pliabilă „Conturi demo” cu cele 2 conturi, nota „Acces exclusiv personal autorizat. Toate acțiunile sunt înregistrate în jurnalul de audit (Directiva UE 2016/680).”

### 5.3 Shell-ul aplicației
- **Sidebar:** Panou, Alerte (badge cu numărul de alerte deschise), Camere, Patrule, Reguli și zone, Căutare în arhivă, Statistici, Jurnal de audit, Setări — filtrate după rol.
- **Topbar:** ceas live, indicator „Flux live activ” (punct care pulsează), pastilă roșie „N critice deschise” (click → alerte critice), profilul utilizatorului, deconectare.
- **Toast alertă nouă:** la fiecare alertă critică/ridicată din fluxul live: tipul, camera, butoane „Deschide dosarul” / „Închide”; semnal sonor scurt la critice (dezactivabil).

### 5.4 Panou dispecerat (`/app`)
- KPI: alerte deschise (din care critice), camere online x/y, patrule disponibile x/y, rată alarme false %, acord AI–operator %.
- **Coada de alerte** (elementul principal): ordonată după gravitate, apoi vechime; fiecare rând = gravitate, tip, cameră, verdict AI + %, stare, „acum 3 minute”; click → dosar.
- Hartă cu camerele (puncte care pulsează când au alertă deschisă).
- Patrule cu stare; distribuția alertelor pe gravitate.

### 5.5 Alerte (`/app/alerte`)
Tabel/listă filtrabilă: căutare text (ID, tip, descriere), gravitate, stare (inclusiv „Deschise”), cameră. Coloane: ID, gravitate, eveniment, cameră, verificare AI, stare, oră. Filtrele se păstrează în URL.

### 5.6 Dosarul alertei (`/app/alerte/:id`) — cel mai important ecran
- Antet: tip, ID, data/ora, gravitate, stare.
- **Dovezi video:** player cu clipul, cadrele cheie (timeline), mențiunea „Fețele și numerele sunt blurate implicit”.
- **Verificare AI:** verdict, încredere %, descrierea în ghilimele.
- **Context:** cameră + direcție, regula (ID + nume), zona, declanșarea în text, clasa obiectului, viteza „(±3–5 km/h, doar triaj)”.
- **Decizie operator:** notă (obligatorie la respingere), butoane **Confirmă** / **Respinge**; după decizie: „Confirmată de X la ora Y” + nota. Mesaj fix: „Decizia rămâne la om. Sistemul nu sancționează automat.”
- **Acțiuni** (după confirmare): alege patrula disponibilă → Trimite; Activează panou de avertizare; Transmite către constatare; Închide dosarul. Lista acțiunilor efectuate.
- **Istoric (audit) al alertei:** cine a văzut, ce a decis, când.
- Deschiderea dosarului se înregistrează automat ca „a vizualizat”.

### 5.7 Camere (`/app/camere`)
Grilă de „monitoare”: flux live/placeholder, nume, drum, direcție, stare, FPS, calibrare („Necalibrată — viteze orientative”), reguli active, link „N alerte deschise”. Camerele offline afișează „Fără semnal”.

### 5.8 Patrule (`/app/patrule`)
Tabel: indicativ, vehicul, zonă, stare (editabilă de operator/admin), alerta curentă (link).

### 5.9 Reguli și zone (`/app/reguli`)
Listă de reguli: ID, nume, gravitate, tip, zonă, praguri, camere, ultima modificare; comutator Activă/Inactivă; editor (nume + praguri) doar pentru admin.

### 5.10 Căutare în arhivă (`/app/arhiva`)
Bară mare de căutare în limbaj natural; exemple clicabile („camioane oprite pe acostament ieri între 14 și 18”, „accident pe bulevardul Unirii marți dimineață”, „viteză mare pe A1 săptămâna trecută”, „pietoni pe autostradă azi”, „ceață pe A2 noaptea”). Stare „Se caută…”. Chip-uri „Am înțeles: camioane · oprire pe acostament · vineri 16 octombrie · ora 14–18”. Grilă de clipuri (durată, tip, cameră, dată, descriere), blur vizibil. Stare goală: „Niciun clip găsit — încearcă un interval mai larg.”

### 5.11 Statistici (`/app/statistici`)
KPI: total, confirmate, rată alarme false, timp mediu de decizie. Grafice: pe gravitate, pe tip, pe cameră („puncte negre”), pe oră din zi, evoluție pe zile; opțional heatmap oră × zi.

### 5.12 Jurnal de audit (`/app/audit`, admin)
Tabel filtrabil după utilizator și acțiune; Export CSV; ID-urile de alertă sunt linkuri.

### 5.13 Setări (`/app/setari`, admin)
Flux live simulat (on/off, interval în secunde), semnal sonor la critice, blur implicit (on/off) + lista garanțiilor de confidențialitate, tabelul utilizatorilor (2 conturi) cu roluri, „Resetează datele demo”, „Golește jurnalul de audit” (cu confirmare).

### 5.14 Stări comune
Încărcare (skeleton), gol, eroare cu „Reîncearcă”, 403 „Acces restricționat”, 404, sesiune expirată → login. Responsive: desktop 1366–1920 (fără scroll de pagină pe dashboard, scroll doar în panouri), tabletă, telefon.

---

## 6. Direcție vizuală (propunere, liberă)
Instrument operațional serios, dar cu efect „wow”: dark mode implicit, accent puternic pentru gravitate, tipografie condensată pentru cifre (KPI, ore, viteze), cifre tabulare, micro-animații discrete (intrarea alertelor noi, puls la critice), respectă `prefers-reduced-motion`, contrast WCAG AA. Logo original (scut + ochi/cameră + drum), **fără** stema sau însemnele oficiale ale Poliției Române / MAI.

## 7. Ce trebuie livrat
Toate ecranele de mai sus ca pagini React funcționale, cu date demo realiste (10 camere din București și împrejurimi, ~60 de alerte pe ultimele 7 zile, 6 patrule, 14 reguli, ~160 de clipuri în arhivă) și autentificare demo cu cele 2 conturi. Datele demo stau într-un singur strat (`src/mocks/` + un store), ca să poată fi înlocuite ulterior cu API-ul real (`/api/login`, `/api/events`, `/api/events/{id}/decision`, `/api/search`, `/api/stats`, `/api/cameras`, `/api/audit`, `/api/stream` SSE).
