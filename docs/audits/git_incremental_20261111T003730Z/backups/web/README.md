# Operator dashboard

Run the dashboard with the demonstration API from the repository root after installing
the pipeline requirements:

```sh
COOKIE_SECURE=0 DASHBOARD_PASSWORD=local-password .venv/bin/python -m uvicorn web.dev_server:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`, enter an operator name and `local-password`. This launcher
serves `app.js` and `app.css` alongside the real demonstration API and sends a strict
Content Security Policy. The original `roadsentinel.server:app` serves the HTML shell
only; use this launcher for the dashboard's external assets.

For the secure backend, serve this directory at the same origin as `/api` and `/media`.
The host must serve `/app.js` and `/app.css` with JavaScript/CSS MIME types and enforce
at least `script-src 'self'; style-src 'self'; font-src 'self'`. All fonts are system fonts.

The dashboard bootstraps `/api/auth/csrf` and sends the readable `__Secure-rs_csrf`
cookie as `X-CSRF-Token` on POST requests (`rs_csrf` in HTTP development). A 404 on
CSRF bootstrap is tolerated for the older demonstration API; other errors are displayed.

Login supports the password/MFA contract: `/api/login`, then `/api/login/mfa`. A 404
on the latter falls back to the secure backend's `/api/auth/mfa/verify`; after verification,
`/api/me` confirms the session. Invalid codes never trigger a route fallback. First-login
MFA enrollment links to the secure application's `/login` page. The demonstration API
supports password login only.

Events marked `redaction: "heads_only"` display a warning that license plates remain
visible. Queue, evidence, audit, and camera template values are escaped before insertion.

Quick syntax check:

```sh
node --check web/app.js
```

In browser developer tools, confirm the response CSP and absence of CSP violations
while logging in, selecting an event, submitting a decision, searching, and reconnecting
the live stream. The local launcher is for development; deploy the secure backend for
per-user sessions, MFA, CSRF enforcement, and protected evidence.
