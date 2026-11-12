# 5-minute security demo (for judges)

Preparation (before the demo):

```bash
python scripts/gen_dev_secrets.py
docker compose --env-file .env -f deploy/docker-compose.yml up --build -d --wait
docker compose --env-file .env -f deploy/docker-compose.yml exec backend python scripts/seed.py
```

Open https://localhost (trust Caddy's local certificate). The dev password for every seeded
account is `RS_SEED_PASSWORD` in `.env`. Log in once beforehand with `operator.a`, `admin.a`,
`auditor.a` and `operator.b` to enroll TOTP (QR on first login), and keep the authenticator
app at hand. Use two browser profiles (Unit A / Unit B).

Shortcut for the terminal: `alias dc='docker compose --env-file .env -f deploy/docker-compose.yml'`.

---

## 1. Unit B cannot see Unit A (≈ 1 min)

1. Browser A (`operator.a@roadsentinel.local`): open any alert, copy its URL (`/alerts/<id>`).
2. Browser B (`operator.b@roadsentinel.local`): paste the URL → **"Alert not found"** (HTTP 404,
   the same answer as for an id that does not exist).
3. Browser B as `auditor.b`, Audit page → entry `security.cross_tenant_access`. Unit A's audit
   log records the probe too.
4. Say: *isolation is enforced twice – the API derives the tenant only from the session, and
   PostgreSQL Row-Level Security (forced, restricted role, fail-closed) filters every query.*
   Optional proof: `dc exec postgres psql -U postgres -d roadsentinel -c "SET ROLE rs_app; SELECT count(*) FROM alerts;"` → `0`.

## 2. Audit tampering is detected (≈ 1 min)

1. `auditor.a` → Audit → **Verify integrity** → ✔ chain intact.
2. Terminal: `dc run --rm migrate python scripts/audit_tamper_demo.py --tenant unit-a --keep`
   (a superuser disables triggers and rewrites one entry).
3. Click **Verify integrity** again → ✖ *Tampering detected at entry #N*; the row is highlighted.
4. Say: *the app role cannot UPDATE/DELETE the audit table at all, triggers block even the owner,
   and the hash chain catches a superuser.* (Run the script without `--keep` to restore.)

## 3. Unblur needs a second person, and it is audited (≈ 1.5 min)

1. `operator.a`: open a critical alert → evidence is **blurred**, plate shown as `B****Z`.
2. Request access → kind *Unblur*, case `CASE-2026-0042`, justification → submitted.
3. Show that the operator cannot approve it, and that an admin cannot approve **their own** request
   (button replaced by "Needs another admin"; server returns 403).
4. `admin.a` → Approvals → **Approve** → MFA step-up prompt → enter code.
5. `operator.a`: refresh the alert → "Unblur granted until …", full plate visible,
   **Show original** works for 30 minutes and can be revoked.
6. `auditor.a` → Audit: `approval.requested`, `approval.approved`, `evidence.url_issued`,
   `evidence.viewed`.

## 4. The database only holds ciphertext (≈ 45 s)

```bash
dc exec postgres psql -U postgres -d roadsentinel -c \
  "SELECT encode(plate_enc,'hex') AS plate, encode(plate_bidx,'hex') AS blind_index FROM alerts LIMIT 3;"
dc exec backend sh -c 'ls /data/evidence/*/ | head -4; head -c 64 /data/evidence/*/*.original.enc | xxd | head -3'
```

Point out the `F1` (field) and `RSE1` (file) headers followed by random bytes: AES-256-GCM with a
per-tenant key wrapped by the master key. Optional:
`dc exec backend python -m app.cli rotate-tenant-key --tenant unit-a` → new key version, data still readable.

## 5. Installable PWA with generic push (≈ 45 s)

1. In Chrome/Edge: install icon in the address bar → RoadSentinel opens as a standalone app.
2. Sessions page → **Enable alert notifications on this device**.
3. Terminal: `dc exec backend python -m app.cli demo-alert --tenant unit-a --priority critical`
   (dev-only helper; operators can also create alerts with `POST /api/alerts`). The notification
   reads only **"New alert, priority: critical"**: no plate, place or image. Details appear only
   after login.
4. DevTools → Application → Cache Storage: only the static shell (no API responses).
   Click **Sign out** → caches and IndexedDB are emptied. Leave the app idle for 5 minutes → it locks.
