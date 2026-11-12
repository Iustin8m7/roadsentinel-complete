# RoadSentinel — predare completă (context pentru un nou asistent)

> Lipește acest document ca prim mesaj într-o sesiune nouă. Conține tot ce trebuie ca să continui fără istoricul conversației anterioare. Ultima actualizare: 2026-10-18.

## 0. STADIUL ACTUAL (2026-10-18, după-amiază) — de aici continui
**În producție (https://web-production-efbca.up.railway.app), totul pe branch-ul `feat/simple-auth`, comis și urcat:**
- UI nou (design „tactical” din cele 8 imagini, implementat de Antigravity) + corecturile de după:
  - rute: landing `/` și `/login` doar pentru vizitatori; utilizatorul logat e trimis mereu în `/app`; `/alerte/:id` vechi → `/app/alerte/:id`; logo-ul din aplicație duce la `/app`.
  - rolul vine din `GET /api/auth/me` (`tenant_admin` → admin în UI), deci adminul vede Setări/Audit.
  - **fără etichete inventate**: KPI, statistici, camere, arhivă și dosarul alertei sunt calculate din alertele reale; chip-ul „AI x%” apare doar dacă VLM-ul chiar a rulat; fără „B-21 / 4,2 km / ETA”, fără ore fixe; patrulele din panou au rămas MOCK (backend-ul nu are patrule).
  - dosar alertă: filmstrip ±3 s din ora evenimentului, istoric din auditul real, mesaj „Clip video indisponibil” când dovada lipsește.
  - arhivă: **căutări rapide prestabilite** = filtre exacte pe alertele reale (viteză >100, depășiri de viteză, schimbări de bandă, frânări, accidente probabile, camioane, Pasaj Basarab noaptea, autostradă) — toate dau rezultate; căutarea liberă folosește `/api/search` (parser de cuvinte cheie, slab).
- **Date:** 128 de alerte în `unit-a`; **70 deschise, toate reale**: 37 viteză foarte mare, 19 schimbări de bandă, 8 frânări bruște, 4 aglomerare, 2 accident probabil. Cele 58 „pieton pe carosabil” (false, de pe `mx-junction` și `mx-avenue`) au fost **respinse** de admin cu nota „fals pozitiv – calibrare zonă” (rămân în audit).
- **Video:** doar ~40 de alerte au clipul disponibil (cele procesate după mutarea dovezilor în `/tmp/rs-evidence`); celelalte și-au pierdut fișierele la redeploy-uri și afișează „Clip video indisponibil”. Serverul nu răspunde cu 206 la cereri Range (derularea în player e limitată); fix-ul cere redeploy backend.
- ⚠️ **NU redeploya `secure-api` înainte de prezentare** (șterge clipurile din `/tmp`). Redeploy pe `web` e sigur.

**Actualizare 2026-10-18 seara (doar frontend, deploy `web`):**
- Player nou (`frontend/src/components/EvidencePlayer.tsx`): descarcă clipul o dată în memorie (blob), deci derularea merge fără suport Range; cadre reale în filmstrip, pas cu pas pe cadre, sari la eveniment, viteză, ecran complet, scurtături (spațiu, ←/→, `,`/`.`). Modal mare cu player (`ClipModal.tsx`) pe Panou, Camere și Arhivă.
- Verificarea e **strict umană**: tot ce ținea de „Verificare AI/VLM” a fost scos din UI.
- Pagina „Jurnal centralizat alerte” a fost ștearsă; `/app/alerte` redirecționează la panou, iar dosarul rămâne la `/app/alerte/:id`. Panoul și dosarul încap în ecran, fără scroll (coada se paginează).
- Alertele `pedestrian_on_road` sunt ascunse din frontend (`HIDDEN_TYPES` în `store/data.ts`); statisticile se calculează doar din alertele afișate.
- Denumiri Iași: UI-ul le suprascrie după slug (`frontend/src/lib/iasi.ts`); comanda de pornire a backend-ului de mai jos (§6) folosește deja numele din Iași, deci le scrie și în DB la următorul deploy al `secure-api`.

**Următorii pași, în ordine:**
1. (făcut) Alertele false cu pietoni au fost respinse. Notă: trimiterea de text cu diacritice din Git Bash cu `curl -d` eșuează; folosește Python/httpx.
2. După prezentare: stocare permanentă pentru dovezi (S3/R2 sau volum mai mare), suport Range (206) în `/api/media`, apoi reprocesare camere.
3. Merge `feat/simple-auth` → `main` (actualizează testele MFA) + deploy automat (legare Railway–GitHub sau `RAILWAY_TOKEN`).
4. VLM real (cheie Anthropic pe pipeline), patrule în backend, înregistrarea completă a camerei pentru player.

## 1. Ce este proiectul
**RoadSentinel**: sistem de alertare rutieră pentru poliție (proiect de hackathon, accent business). Monitorizează automat camerele de trafic cu AI și trimite alerte în timp real dispecerilor, cu dovezile pregătite.
- **Problema:** camerele produc mii de ore de video nemonitorizat; incidentele se află târziu (după 112); probele se caută manual.
- **Cum funcționează:** (1) YOLO + ByteTrack detectează și urmăresc vehicule/pietoni, calculează viteza, frânările, schimbările de bandă, distanța; (2) reguli configurabile pe zone și praguri generează evenimente tipizate și explicabile; (3) VLM opțional (Claude) confirmă/infirmă și descrie clipul; (4) alerta ajunge în dashboard, ordonată după gravitate; operatorul confirmă/respinge și trimite patrula; totul e auditat.
- **Garanții:** decizia rămâne la om; viteza din video ±3–5 km/h doar pentru triaj; fără recunoaștere facială; GDPR + Directiva UE 2016/680; audit complet.
- **Pitch:** salvarea vieților prin detecție și răspuns rapid; „Fiecare cameră, un ochi care nu doarme.” Software peste camerele existente (fără hardware nou); clienți: Poliția Rutieră/IGPR, CNAIR, primării, concesionari de autostrăzi; SaaS per cameră.

## 2. Oameni și conturi
- Utilizator: Costan Călin (Calin). Coechipier: Cristian Gavrilean (autorul backend-ului securizat, CI, primul fine-tune pe Mac M2).
- GitHub (privat): https://github.com/CristiMachine25/roadsentinel  — git push merge din laptopul lui Calin (credențiale salvate în Windows Credential Manager).
- Railway: proiect `roadsentinel`, mediul `production`, cont **juhavrocladen@gmail.com** (CLI-ul `railway` e logat cu el și folderul e legat cu `railway link`).
- Local: `C:\Users\Calin\Desktop\costan calin pfa\roadsentinel` (Windows 11, Git Bash + PowerShell, GPU RTX 3050 4 GB, Docker Desktop).

## 3. URL-uri și autentificare
- **Aplicația publică:** https://web-production-efbca.up.railway.app  (UI poliție + /api prin gateway)
- Login (fără MFA): **admin / <demo-password>** (administrator) și **operator / <demo-password>** (operator). Celelalte conturi sunt dezactivate.
- Backend direct: https://secure-api-production-fef6.up.railway.app · backend vechi demo: https://api-production-e62e.up.railway.app

## 4. Structura repo-ului
| Folder | Ce este |
|---|---|
| `backend/` | **Backend-ul real** (FastAPI, Postgres, multi-tenant cu RLS, audit cu hash-chain, dovezi criptate, ingest semnat HMAC). Contract: `API.md`. CLI: `python -m app.cli …` |
| `frontend/` | **UI-ul de poliție** (Vite + React 19 + TS + Tailwind 4 + React Router 7 + Zustand). `VITE_USE_MOCKS=1` = mod demo cu date mock; altfel API real |
| `roadsentinel/` | **Pipeline-ul de detecție** (`pipeline.py`, `rules.py`, `sink.py`) + serverul demo vechi (`server.py`) |
| `cameras/*.yaml` | Configurarea fiecărei camere: video, calibrare (4 puncte → metri), zone (poligoane, tip, direcție), reguli active, praguri |
| `training/` | Fine-tuning YOLO: `extract_frames.py`, `prelabel.py`, `split.py`, `train.py`, `evaluate.py`, `RESULTS.md` |
| `deploy/` | `docker-compose.yml` (stack local), `railway-web/` (gateway Caddy: UI + proxy /api) |
| `secure-pwa/` | PWA-ul securizat al lui Cristian (mutat din `frontend/`, nefolosit în demo) |
| `web/` | Dashboard-ul clasic vechi (scos din gateway) |
| `scripts/` | `deploy_secure_backend.sh`, `deploy_web_gateway.sh`, `deploy_demo.sh`, `gen_dev_secrets.py`, `download_data.sh` |
| `data/` (gitignored) | `videos/` (Roboflow demo), `mixkit/` (8 clipuri cameră fixă + `moving/`), `romania/` (Wikimedia), `mendeley/annotated_dataset.zip` (7,4 GB cadre etichetate YOLO, Creative Commons) |

## 5. Branch-uri
- `main` — integrat de Cristian (PR #1–#18). Are MFA obligatoriu și workflow de deploy automat (`.github/workflows/deploy.yml`) care **nu funcționează**: serviciile Railway nu sunt legate de GitHub și lipsește secretul `RAILWAY_TOKEN`.
- **`feat/simple-auth`** — **branch-ul de lucru curent, cel deployat în producție.** Conține: login fără MFA, comanda `demo-accounts`, scoaterea rutei /dispecerat, regula `probable_crash`, camere Mixkit, pipeline pe CUDA, fără blurare, o singură copie a dovezilor, `scripts/deploy_demo.sh`. **Nu e merge-uit în `main`** (testele de securitate ale backend-ului ar pica, pentru că verifică MFA).
- `integration/full-stack`, `feat/police-frontend` — vechi, depășite.

## 6. Deploy (manual, prin Railway CLI, din Git Bash, din folderul `roadsentinel`)
Serviciile: `secure-api` (backend), `web` (gateway UI), `api` (vechi), `Postgres`. Pe Windows nu există `rsync`, deci folosim `git archive`/`tar`.

**Backend** — comanda de pornire creează conturile demo și înregistrează camerele (idempotent):
```bash
reg() { echo "python -m app.cli register-camera --tenant unit-a --slug $1 --name '$2' --location '$3'"; }
R="$(reg demo-highway 'Centura Iași – DN28, pasarelă' 'Centura Iași, DN28 km 4, pasarelă pietonală') && $(reg demo-urban 'Pasaj Octav Băncilă' 'Bd. Independenței, pasaj Octav Băncilă') && $(reg mx-avenue 'Bd. Ștefan cel Mare și Sfânt' 'Bd. Ștefan cel Mare, trecere de pietoni') && $(reg mx-bridge-night 'Pasaj Mihai Eminescu (noapte)' 'Pasaj Mihai Eminescu, sens Copou') && $(reg mx-interchange 'Nod rutier Podu Roș (vedere de sus)' 'Podu Roș × Bd. Nicolae Iorga') && $(reg mx-junction 'Intersecție Piața Unirii' 'Piața Unirii, Iași')"
S=$(mktemp -d); git archive HEAD backend scripts | tar -x -C "$S"; rm -rf "$S/backend/tests"
sed '/^CMD \[/,$d' backend/Dockerfile > "$S/Dockerfile"
printf 'CMD ["sh", "-c", "python -m app.cli migrate && python -m app.cli demo-accounts --tenant unit-a --password <demo-password> && %s && exec uvicorn app.main:create_app --factory --host :: --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips \\"*\\" --no-server-header"]\n' "$R" >> "$S/Dockerfile"
railway up "$S" --path-as-root --service secure-api --detach --message "backend"
```
**UI (gateway)**:
```bash
W=$(mktemp -d); git archive HEAD frontend deploy/railway-web | tar -x -C "$W"; cp deploy/railway-web/Dockerfile "$W/Dockerfile"
railway up "$W" --path-as-root --service web --detach --message "web"
```
(Pentru a include modificări necomise din `frontend/`, folosește `cp -r frontend deploy "$W/"` fără `node_modules`/`dist` în loc de `git archive`.)
Status: `railway deployment list --service <svc>` · log-uri: `railway logs --service secure-api`.

**Variabile importante pe `secure-api`:** `RS_ENV=production`, `RS_DATABASE_URL`, `RS_JWT_SECRET`, `RS_MASTER_KEYS`, `RS_URL_SIGNING_KEY`, `RS_PUBLIC_ORIGIN`, **`RS_EVIDENCE_DIR=/tmp/rs-evidence`**. Setează variabile cu `MSYS_NO_PATHCONV=1 railway variables --service secure-api --set "K=V"` (altfel Git Bash strică căile).

⚠️ **Stocarea dovezilor:** volumul `/data` (434 MB) e **plin**, deci dovezile stau acum în `/tmp/rs-evidence` (disc container, 2 TB liberi, dar **se șterge la fiecare redeploy al `secure-api`**). Orice redeploy al backend-ului = clipurile și cadrele alertelor existente dispar (alertele rămân). După ultima procesare înainte de demo, **nu mai redeploya backend-ul**. Soluție permanentă: volum mai mare sau stocare S3/R2.

## 7. Cum se generează alerte în producție (pipeline local pe GPU)
1. Mediu: `.venv` (Python 3.13, torch 2.11+cu128, ultralytics 8.4) — deja instalat. `ffmpeg` e în `.venv/ffbin` (din `imageio-ffmpeg`).
2. Cheia HMAC a contului de serviciu `pipeline-demo-laptop` e în **`prod.local.env`** (gitignored: `RS_API_URL`, `RS_INGEST_KEY_ID`, `RS_INGEST_SECRET`). Dacă se pierde: login ca admin → `POST /api/service-accounts {name}` → `POST /api/service-accounts/{id}/keys`.
3. Rulare (Git Bash, din `roadsentinel`):
```bash
set -a; . ./prod.local.env; set +a
export PATH="$PWD/.venv/ffbin:$PATH" RS_REDACTION=off RS_EXPERIMENT_TRACKING=off PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
for c in mx-bridge-night mx-avenue mx-interchange demo-highway demo-urban; do
  .venv/Scripts/python -m roadsentinel.pipeline cameras/$c.yaml --live --no-wandb > pipeline-$c.log 2>&1
done
```
Fiecare alertă e trimisă semnat la `/api/ingest/events` cu clip ±3 s și cadru cheie. O cameră nouă cere: fișier `cameras/<slug>.yaml` + înregistrare în producție (`register-camera`, adică redeploy backend cu linia în `R`).
- `mx-junction` e scoasă din rulare: genera zeci de „Pieton pe carosabil” false (pietoni pe trecere). În producție există ~58 astfel de alerte false; pot fi respinse în bloc din API ca admin (`POST /api/events/{id}/decision {"decision":"reject","note":"fals pozitiv – calibrare zonă"}`).

### 7b. Camere live (flux public, în timp real)
- Prima cameră live: **Piața Unirii, Iași** (`cameras/iasi-piata-unirii.yaml`, flux HLS public 1080p de la WebcamRomania.ro / Grand Hotel Traian). Fluxul aparține proprietarului: îl folosim pentru demo, cu sursa menționată; cerem acordul înainte de o prezentare publică.
- Rulare (camera trebuie înregistrată în producție cu `register-camera`; cheia unui cont de serviciu stă într-un fișier env în afara git):
  `scripts/run_live_cameras.sh <fișier-env> cameras/iasi-piata-unirii.yaml` — repornește pipeline-ul dacă se oprește; log-uri în `~/.roadsentinel/live-logs/`.
- Pipeline-ul citește fluxul pe un fir separat și procesează mereu cel mai nou cadru (dacă GPU-ul e ocupat, sare cadre, nu rămâne în urmă), trimite alertele în fundal și un heartbeat la 30 s. Camera apare **LIVE** în UI cât timp heartbeat-ul e mai nou de 2 minute, iar pagina Camere redă fluxul public (hls.js).
- La intersecții cu semafor sunt active doar regulile de viteză și accident probabil (frânările și opririle sunt normale; virajele arătau ca schimbări de bandă). Tramvaiele sunt detectate ca autobuze și frânează în stație, de aceea `crash_ignore_classes: [bus]`.
- Alte fluxuri publice verificate (Gara Pașcani, Palatul Culturii, Ploiești, Piața Romană etc.) sunt în `docs/public-live-cameras.md`.

## 8. Reguli de detecție (`roadsentinel/rules.py`, oglindite în `backend/app/core/catalog.py` — trebuie ținute identice)
| Tip | Gravitate | Condiție |
|---|---|---|
| wrong_way | critică | mișcare constantă contra direcției zonei |
| pedestrian_on_road | critică | pieton în zonă de carosabil |
| **probable_crash** (nou) | critică | frânare bruscă de la >30 km/h urmată de oprire completă în ≤4 s pe carosabil |
| very_high_speed | ridicată | viteza mediană > prag |
| stopped_emergency_lane / stopped_on_road | ridicată | viteză < prag mai mult de N s |
| hard_braking | medie | decelerare > prag |
| tailgating | medie | distanță în timp < prag ≥1 s |
| dangerous_lane_change | medie | deplasare laterală mare cu vecin la <15 m |
| congestion | info | multe vehicule, viteză medie mică |
Pragurile sunt per cameră, în `cameras/*.yaml` (cele demo sunt coborâte intenționat pentru mai multe alerte, marcate `demo-tuned`).

## 9. Rulare locală (opțional)
- Stack complet: `python scripts/gen_dev_secrets.py` apoi `docker compose --env-file .env -f deploy/docker-compose.yml -f deploy/docker-compose.local.yml up -d --build`. UI poliție pe http://localhost:8088 (portul 8080 e rezervat de Windows). Conturi: `docker compose … exec backend python -m app.cli demo-accounts`.
- Doar UI: `cd frontend && npm install && npm run dev` (proxy /api → localhost:8000; cu Docker backend-ul nu e publicat pe 8000).

## 10. Design și Antigravity
- Designul final e definit de 8 imagini (Design System, Landing, Login, Panou, Dosar, Camere, Arhivă, Statistici): dark „tactical”, culori #0A0E14/#111821/#17202B/#1E2A36, text #E6EDF3/#7D8A9B, gravitate #FF3B3B/#FF8A1F/#FFC23D/#3DA5FF, OK #2ED47A, fonturi Inter / Barlow Condensed / JetBrains Mono.
- Prompt pentru Antigravity: `frontend/ANTIGRAVITY_PROMPT_FINAL.md` (ce e REAL din API și ce e MOCK). **Antigravity lucrează acum local în `frontend/`; modificările lui nu sunt încă comise.** La final: verifică `npx tsc -b && npm run build`, testează cu backend-ul, commit pe `feat/simple-auth`, apoi deploy `web`.
- Spec complet pentru generare de imagini UI: `frontend/GEMINI_UI_SPEC.md`.

## 11. Antrenare
- Primul fine-tune (Cristian, Mac M2): `training/RESULTS.md` — distilare yolo11m → yolo11s pe pseudo-etichete; puțin mai bun pe mașini/camioane, mai slab pe autobuze; greutățile doar pe Mac-ul lui.
- Pe laptopul lui Calin nu s-a antrenat nimic încă. Date gata: Mendeley (7,4 GB, etichete umane YOLO, de dezarhivat în `data/mendeley/`). Estimare: 20 de epoci yolo11s 640 px pe RTX 3050 ≈ 1–2 h. Pentru demo se folosește `yolo11s.pt` standard.
- Dataset-uri care cer acces (de trimis cereri): TU-DAT (accidente), TSBOW (vreme rea), AAU RainSnow, AI City Challenge, BrnoCompSpeed (viteze reale), UA-DETRAC.

## 12. Probleme cunoscute / de făcut pentru MVP
1. Stocarea dovezilor (vezi §6): volum plin, `/tmp` se golește la redeploy → S3/R2 sau volum mai mare.
2. Deploy automat din GitHub: legare servicii Railway la repo sau `RAILWAY_TOKEN` + merge în `main` (cu actualizarea testelor MFA).
3. UI afișează rolul „operator” și pentru admin (backend-ul nu întoarce rolul în `/api/me`).
4. Player-ul din dosar: înregistrarea completă a camerei nu se încarcă în modul `--live`, deci se redă doar clipul ±3 s.
5. (rezolvat) Alertele false „Pieton pe carosabil” au fost respinse.
6. VLM dezactivat (fără cheie Anthropic); de activat pe pipeline pentru „Verificare AI” reală.
7. Securitate demo: MFA scos, parole slabe, conturi recreate la fiecare pornire — doar pentru hackathon.
