# RoadSentinel police interface

> Current integration: the secure FastAPI backend is the supported source of
> truth. Start it with `uvicorn app.main:create_app --factory` from `backend/`
> after a guarded PostgreSQL migration, then use the frontend Vite proxy. The
> legacy `roadsentinel.server` instructions below are for the standalone demo.
> The secure client now includes a tenant-scoped Romania incident map and a
> persisted in-app notification bell; see [API.md](../API.md) and
> [the current notification evidence](../docs/completion/NOTIFICATIONS_20261112.md).

The default mode uses the HTTP contract in `../API.md`: session authentication, events, decisions, cameras, audit, search, statistics, and live SSE updates. Real session and event state stays in memory; the server authorizes every request.

## Local development

Start the demo API from the repository root:

```sh
.venv/bin/uvicorn roadsentinel.server:app --port 8000
```

Then run the UI:

```sh
cd frontend
npm ci
npm run dev
```

Vite serves port 5173 and proxies `/api` and `/media` to `http://localhost:8000`. The demo server supports password login when `DASHBOARD_PASSWORD` is set and otherwise allows a local operator. Set `COOKIE_SECURE=0` for local HTTP password testing.

Copy `.env.example` to `.env.local` if needed. `VITE_API_URL` is an optional API origin (without `/api`); leave it empty for same-origin deployments and the development proxy. Cross-origin setups must allow credentials and make the CSRF cookie readable from the UI origin. Production should serve the UI and API on the same origin.

## De integrat (REAL vs MOCK)

Toate funcționalitățile existente în backend sunt consumate din API-ul real. Componentele vizuale avansate din noul Design System care nu au încă suport în backend-ul curent sunt marcate în cod cu `// MOCK:` și centralizate:

| Funcționalitate / Element UI | Status curent | Endpoint / Sursă | Notă de integrare |
|---|---|---|---|
| Autentificare / Sesiune / CSRF | **REAL** | `POST /api/login`, `POST /api/logout`, `GET /api/me`, `GET /api/auth/csrf` | Cookie de sesiune securizat + `X-CSRF-Token` |
| Coada de alerte & evenimente | **REAL** | `GET /api/events` | Listă evenimente, priorități, video_t, bounding box, clip_url |
| Flux SSE în timp real | **REAL** | `GET /api/stream` (SSE) | Evenimentele `alert` și `audit` |
| Dosar alertă & detalii | **REAL** | `GET /api/events/{id}`, `POST /api/events/{id}/view` | Cadrul cheie, clipul video, istoricul audit |
| Decizii (Confirmă / Respinge) | **REAL** | `POST /api/events/{id}/decision` | Decizii reale; 409 reîncarcă starea |
| Meta tipuri & acțiuni permise | **REAL** | `GET /api/meta` | Acțiuni disponibile pentru decizie |
| Jurnal audit | **REAL** | `GET /api/audit?limit=200` | Istoric complet al deciziilor și acțiunilor operatorilor |
| Camere de trafic | **REAL** | `GET /api/cameras`, `PATCH /api/cameras/{uuid}` | Listă și sănătate cameră; administratorii tenantului pot edita nume, locație, coordonate și fus orar prin endpoint-ul cu MFA și audit. `video_url` indică o înregistrare, nu un flux live. |
| Căutare în arhivă | **REAL** | `POST /api/search`, `POST /api/saved-searches` | Parser de cuvinte cheie, căutări salvate per utilizator; textul original nu este persistat |
| Statistici de bază | **REAL** | `GET /api/stats` | Grupate pe gravitate, status și tip incident |
| Telemetrie camere & viteză medie | **MOCK** | `src/pages/CamerasPage.tsx` | De integrat când camerele transmit telemetrie în timp real |
| Hartă tactică & radar patrule | **MOCK** | `src/components/TacticalMap.tsx` | De integrat cu modulul GPS/AVL pentru poziționarea patrulelor |
| Procent potrivire arhivă | **MOCK** | `src/pages/ArchivePage.tsx` | Calculat client-side / mock relevanță semantică |
| Trimitere patrulă B-21 | **MOCK + REAL** | `POST /api/events/{id}/decision` (`dispatch_patrol`) | Trimite decizia reală în backend cu acțiunea `dispatch_patrol` |
| Heatmap oră × zi & trend lunar | **MOCK / Client-side** | `src/pages/StatsPage.tsx` | Calculat client-side din `occurred_at` |
| Adăugare flux cameră nouă | **MOCK** | `src/pages/CamerasPage.tsx` | Afișează dialogul „disponibil după integrarea pipeline-ului” |
