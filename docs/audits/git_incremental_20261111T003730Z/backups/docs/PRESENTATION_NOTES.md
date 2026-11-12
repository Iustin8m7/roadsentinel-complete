# 5-minute demo script (only verified features, synthetic data)

Setup before the room fills (once): `python scripts/demo.py --profile strict` (or `--profile demo` for password-only accounts on your own laptop), then `cd frontend && npm run dev`. Everything on screen is seeded **SINTETIC** data; say so first.

| Min | Show | Say (and nothing more) |
|---|---|---|
| 0:00 | Login with TOTP | "Two-factor is mandatory for every account. Sessions expire after 30 idle minutes." |
| 0:30 | Alert queue, severity order | "These are synthetic alerts. Priority comes from the event type, never from the client." |
| 1:15 | Open a case: keyframe, rule that fired, the SINTETIC / redaction chip, audit trail | "Each alert says which rule fired and with what numbers. Redaction is a heuristic and the chip says what the system reports. Speed would read *orientativ*." |
| 2:00 | Confirm one alert (confirm dialog), reject another | "The human decides. Both decisions are in the audit log with who and when." |
| 2:30 | Assign a patrol (secure app, Alerte → case → Patrulă); switch to the patrol account and press *Am plecat spre locație* | "Real accounts only, forward-only status, no invented positions." |
| 3:15 | Cameras page: measured fps and "Nu poate produce la acest ritm: …" | "The system tells you which alert types a slow camera cannot produce." |
| 3:45 | Statistics: *Timpi de răspuns măsurați* | "Measured from stored timestamps; n and the window are shown. We do not show accuracy because it has not been measured on real footage." |
| 4:15 | Admin: retention dry-run; *Recuperare cont* flow in one sentence; audit chain verify | "Evidence is deleted by policy and the deletion is audited; legal hold blocks it. Account recovery needs a second admin." |
| 4:45 | Honest close (below) | |

## Say this at the end
"What is built: the full loop from rule to human decision to audit, with encryption, tenant isolation, signed ingestion and four-eyes controls. What is **not** done: accuracy has not been measured on real cameras at night or in rain, speed is not calibrated for enforcement, redaction is heuristic, there is no legal/DPIA sign-off, and we have not load-tested beyond a laptop. Those are the next phase, in that order."

## Numbers you may quote (and their conditions)
* Ingest request ≈ 42 ms median, event on the operator's screen ≈ 0.5–1 s (1 s polling), measured on one laptop over loopback with up to 51 viewers (docs/LIMITS.md).
* Test counts: see docs/FINAL_STATUS.md. Say "tests pass" only about the suites listed there.
* Do **not** quote: accuracy, mAP, false alarms per hour, speed error, "AI confirms", "GDPR compliant", "blurred by default" (it is *on by default and heuristic*).
* If someone asks about the live Iași camera: it is off until the webcam owner's written permission is recorded.
