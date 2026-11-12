# DEPRECATED: legacy dashboard

`web/` and `roadsentinel/server.py` are the original single-file demo (local event store, one shared
password, no MFA, no tenant isolation). They are frozen: no new features, not part of CI beyond the
existing unit tests, not deployed by `deploy/`. Use `frontend/` (operators) and `secure-pwa/`
(patrol, auditor, admin) against `backend/`. Remove the Railway `api` service that still runs it.
