# Real-browser authentication and MFA — PASS

Updated 2026-11-10T23:54:00.244161+00:00 (local date 2026-11-11, Europe/Bucharest).

Runtime A: existing UI5175 → API8003 → `rsint_20261110b@127.0.0.1:55446`, app `rsint_app_261110b`, Alembic0022.
Runtime B: new uniquely named clusters, databases and test-owned files; actual identities are in each run's `database.json`.
Runtime C: both original source trees/databases, read-only and never used for writes.
All browser actions use genuine Chromium156.0.8078.4 via Playwright, real Vite/FastAPI/PostgreSQL, no network interceptions or mocked success responses.
[Live identity/proxy/RLS proof](runtime_verification/browser-20261111T011541+0200/active-runtime-final.json); [timestamped screenshot hashes](REAL_BROWSER_SCREENSHOTS/2026-11-11/index.json).


[Fresh native browser log](runtime_verification/browser-20261111T011541+0200/auth-final-code.log); [216 sanitized request outcomes](runtime_verification/browser-20261111T011541+0200/auth-final-code/live-browser-result.json); [operator dashboard](REAL_BROWSER_SCREENSHOTS/2026-11-11/A-auth-live-operator.png).

| Criterion | Result | Actual assertion |
|---|---|---|
| Blank login and accessible labels | PASS | `/login`, Utilizator, Parolă, Intră, no page JS errors |
| Incorrect password | PASS | Actual password POST401; protected auth/me401; generic error, no session |
| Password alone cannot authenticate | PASS | Correct POST200 returns MFA challenge; auth/me remains401 |
| Invalid TOTP | PASS | First operator challenge deliberately submits invalid code, receives401 |
| Valid enrolled TOTP | PASS | Four role-specific fresh contexts plus repeat operator; real challenge accepted |
| Operator/admin protected UI | PASS | `/app`, populated server-backed dashboard and navigation |
| Patrol | PASS | `/app`, only permitted navigation; admin route blocked |
| Auditor | PASS | `/app/audit`, audit data, camera/admin write denied |
| Refresh/new tab | PASS | Valid session remains associated with original identity |
| Logout/back/direct protected URL | PASS | Logout invalidates session, auth/me401; UI returns to login |
| New account first enrollment | PASS in B | Real QR setup, TOTP confirmation,8 recovery codes, explicit acknowledgement; me401 before factor |
| Unit B resource probing | PASS in B API/RLS tests | Source-job/camera/alert/media/case/export ownership enforced; not a separate Unit B browser tour |
| Expired-session browser clock advance | NOT RUN | Invalid token tests exist; no long idle browser soak |
| Full accessibility/mobile/HTTPS install | NOT RUN | Keyboard-labelled tested screens only; no compliance certification |

Native accounts: operator.a@roadsentinel.local, admin.a@roadsentinel.local, patrol.a@roadsentinel.local, auditor.a@roadsentinel.local, tenant unit-a. Password remains in `backend/.integration-test-credentials.json`0600 and is unchanged. Existing factors are preserved; tests did not reset them. Native TOTP replay waits for the real next step. B fixtures may reset their own last-used step for repeated fixture logins; no production bypass exists.

MFA seeds, cookies and recovery codes are never report inputs. Protected local authenticator files are under `backend/.integration-authenticators/`0700. The corresponding private HTML QR can be imported into the user's authenticator. The command in FINAL_BROWSER_HANDOFF prints a TOTP only when run by the user locally.

Login root cause and completed repair: FORCE RLS applied to a non-BYPASS SECURITY DEFINER owner, hiding already existing tenants and users. Duplicate slug was evidence of hidden data, not absence. Six identifier lookups now have a dedicated NOLOGIN, column-limited owner; application/migrator remain NOBYPASSRLS. Existing passwords/MFA were preserved. See INTEGRATED_LOGIN_RECOVERY_REPORT.md and migration0022. The UI also now maps actual native roles/permissions, sends auditors to audit, waits for recovery acknowledgement, and finishes an empty dashboard load.

HTTP development uses loopback with the configured non-Secure development cookie mode; production Secure/SameSite/CSRF/MFA controls were not globally relaxed. Browser mutations use CSRF tokens, protected endpoints enforce role policy, and no UI password/MFA material appears in screenshots.
