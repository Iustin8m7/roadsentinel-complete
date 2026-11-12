# Security/privacy regression — fresh real browser, 2026-11-11

Backend423 passed/0 failed/2 explicit legacy opt-in skips; root221, React24, secure-PWA9. Fresh native four-role MFA and isolated first-enrollment/recovery acknowledgement pass. Passing tests do not certify production security/legal compliance. Full details: REAL_BROWSER_AUTH_MFA_VERIFICATION.md, FEATURE_1_REAL_BROWSER_E2E.md, FEATURE_2_REAL_BROWSER_E2E.md and TEST_EXECUTION_LEDGER_UPDATED.md.

| Boundary | Executed evidence | Remaining limitation |
|---|---|---|
| RLS/lookup owner | Native exact DB identity,0022,32 named ENABLE+FORCE tables; app/migrator NOBYPASS; dedicated NOLOGIN identifier-only lookup role, password_hash/schema CREATE denied; fresh PostgreSQL regressions | Admin role exists only for guarded setup/backup, not HTTP runtime |
| Tenant/roles | Native four-role browser denied admin routes; B app-role/HTTP negatives for uploads/candidates/media/cameras/alerts/cases/exports; UnitB users invisible in native UnitA read | Not every cross-tenant permutation repeated in Chromium |
| Password/MFA/session | Wrong password401, correct password requires factor, wrong TOTP401, real TOTP, dashboard/new tab/refresh/logout401; genuine QR enrollment B and acknowledged recovery codes | No production IdP or full long-idle browser soak |
| CSRF/cookies | Existing token/Origin protections retained; real cookie-preserving browser mutations and backend negative tests | Native loopback development HTTP uses its explicit pre-existing Secure=false; production remains Secure/TLS |
| HMAC/control plane | Actual body signatures/nonce/time/account/camera checks, lease before source, exact revision/model ACK, duplicate-worker refusal, real disable and no late alerts | Comprehensive malicious network threat matrix/long soak incomplete |
| Evidence | Real redacted keyframe/clip encrypted RSE1, authenticated playback, independent approved package download, SHA checks/tampered copy refusal, OS restart/ciphertext preservation | Worker retry staging is private/redacted but lacks encryption/TTL; manifest unsigned, no external custody anchor |
| Worker process privilege | Actual browser Start launches allowlisted profile and scoped HMAC process; environment excludes DB/admin/master/session/cloud keys; private per-worker scratch | Same OS user controls process; this is no production OS isolation boundary |
| Consent/source | Explicit licensed local replay grant and provenance; SYNTHETIC TEST + RECORDED/LOCAL REPLAY labels survive worker/alert/UI/export | No external stream rights assumed or tested; full grant UI incomplete |
| Redaction/privacy | Real model-based heuristic masking applied before evidence/preview; fixture labels do not falsely turn full redaction into synthetic redaction | Masks are heuristic and may miss personal data; no complete anonymization claim |
| Audit | Actual login/review/note/bookmark/approvals/config/worker actions use canonical audit; hash-chain regression passes | No independent immutable external audit anchoring |
| Retention/recovery | Native backup actually restored/rehearsed before additive migration; no reset; B case/media persist across new API process | Full crash-orphan, quota, long-term retention/hold matrix remains backlog |
| Secrets | Saved password unchanged; protected0600 file and0700 authenticators; current screenshots mask QR/manual secret/recovery/OTP; sanitized traces contain method/path/status only | Local development authenticator fixture is sensitive and user-controlled; never commit/share it |
| Test artifacts | Fixture user repr now hides password/TOTP; public failure logs scanned/redacted, session state stays0600 in unique test dirs | Native secrets are never included in screenshots/reports/packages |
| Preservation | Both reference HEADs and608 source hashes unchanged; no original DB writes, no original venv install, NO GITHUB PUSH | Hash inventory covers source, not every ignored user file |
