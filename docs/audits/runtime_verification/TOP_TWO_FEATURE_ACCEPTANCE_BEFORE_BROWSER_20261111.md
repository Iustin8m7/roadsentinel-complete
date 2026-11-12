# Current selected-feature acceptance — 2026-11-10

Existing login PASS on A: actual5175→8003→rsint_20261110b:55446, four roles QR/TOTP/recovery acknowledgement, normal TOTP challenge, protected dashboard, refresh/restart/logout. Wrong password401; privilege denials403;32 FORCE RLS tables and runtime NOBYPASSRLS retained.

| ID | Observed acceptance | Result |
|---|---|---|
| F1-01 | Real YOLOX-S/ByteTrack on explicitly synthetic licensed frozen-frame derivative;60 samples; nonempty candidates | PASS fixture; no real incident accuracy |
| F1-02 | Owned upload/crop/analysis via HTTP; explicit operator promotion; recorded/synthetic source; encrypted redacted playable JPEG/MP4 | PASS B |
| F1-03 | Duplicate returns same alert; cross-tenant404; patrol/auditor403; private media denied | PASS B |
| F1-04 | Chromium candidate resubmission→alert→actual rejection→case note→protected playback | PASS B; first creation/upload done via HTTP |
| F1-05 | Admin license grant, self-approval denied, independent export approval, package download, manifest/member SHA-256 | PASS HTTP B; no signed/external custody claim |
| F1-06 | Whole case/archive/browser export and restart/crash durability | NOT FULLY TESTED |
| F2-01 | Actual admin browser registration; genuine two-admin API draft/validate/submit/approve/activate | PASS B; not every control editor action in browser |
| F2-02 | HMAC lease before source open, real model, ACK1, changing operator browser preview | PASS LOCAL RECORDED REPLAY |
| F2-03 | Competing actual worker refused before source open; revision2 independent activation→fresh lease/ACK | PASS B |
| F2-04 | Forced source outage→reconnecting→expired preview404→real recovery; disable/re-enable/final pause | PASS B |
| F2-05 | Eligible model-derived managed incident/evidence/case export in one run | NOT VERIFIED; moving replay had0 eligible events |
| F2-06 | Two-camera soak, abrupt worker crash/expiry, external authorized live | NOT TESTED / EXTERNAL RIGHTS BLOCKED |

Broader Feature1 PARTIAL; Feature2 PARTIAL. Actual fixture component gates pass; missing gates are not marked green. See FULL_INTEGRATION_E2E_VALIDATION.md and its repeatable44-test command.

---

# Historical acceptance checklist

# Final acceptance gates

F1-01 PASS PARTIAL REAL INPUT: 60 actual model samples, 9 candidates from synthetic frozen licensed frame; no representative incident accuracy.
F1-02 PASS: HTTP operator explicit promotion into canonical new alert; recorded origin and synthetic label; encrypted redacted JPEG and playable bounded MP4.
F1-03 PASS: repeated submission idempotent; other tenant 404; patrol/auditor 403; cross-tenant media denied.
F1-04 PASS PARTIAL BROWSER: actual password/TOTP, candidate-list resubmission links same alert, rejected state and playable clip. First upload/promotion/decision performed by HTTP. Full case/archive/export/restart browser not passed.
F1-05 PASS EXPORT: real HTTP case note, explicit license grant, independent approval, signed download and offline manifest/member hash verification. Package unsigned. Crash/restart durability remains UNVERIFIED.

F2-01 PASS LOCAL REPLAY: fixture-approved managed source acquires lease before source open; real model and reference check; ACK revision 1.
F2-02 PASS: signed preview, two distinct payloads, authenticated tenant access, actual YOLOX/ByteTrack pipeline.
F2-03 PASS: second epoch receives stop; model mismatch/revision/revocation unit negatives; actual disable stops worker and managed preview reads are gated.
F2-04 PASS LOCAL RECOVERY: source socket disruption -> reconnecting -> preview expires -> recovered frames. Approved config reload/rollback, multi-camera stress and live detail browser remain UNVERIFIED.
F2-05 UNVERIFIED: eligible model-derived live incident with approved export; recorded positive + exported package and signed live replay remain separately verified components.
External live: BLOCKED (no verified source-specific processing/recording authorization).

Overall: Feature 1 PARTIAL; Feature 2 PARTIAL. No all-green completion claim.
