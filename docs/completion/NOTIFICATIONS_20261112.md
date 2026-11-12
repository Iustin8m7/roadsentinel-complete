# Local incident notification integration — 2026-11-12

## Implemented path

The canonical `Alert` and its evidence/location links remain the source of truth.
Signed live ingestion, explicit recorded-candidate promotion and manual alert creation
append `NotificationEvent` in the same PostgreSQL transaction as the alert. Operator
confirm/reject, independent approved location correction, assignment and patrol status
append separate revisions. Events are immutable, tenant-scoped, source-labeled and
suppressed for explicitly synthetic/test-only incidents. A per-tenant transaction lock
allocates a monotonic cursor; an authenticated SSE reader polls committed rows every
two seconds across API workers. Session, active role, and object visibility are
rechecked. The inbox uses per-user read/ack/dismiss receipts and a saved sound opt-in.

The operator client shows a bell, persisted count, inbox and toast. The map refreshes
from its tenant-scoped database query on a notification, with an eight-second fallback.
Unknown locations still have no marker. Candidate/confirmed/rejected and recorded
points have distinct map styles; source precision labels remain visible. SSE never
contains coordinates or protected media. Browser Notification API and native background
push are outside this in-app mechanism.

## Actual verification

- Fresh disposable PostgreSQL migration through `0028`, FORCE RLS and non-bypass app
  role: `docs/audits/runtime_verification/runs/20261111T235853Z-1833e8a5/schema-security.log`.
- Real Chromium recorded workflow, actual YOLOX-S/ByteTrack on licensed moving traffic,
  explicit **SYNTHETIC TEST** frozen-frame candidate, location correction, independent
  export, process restart, manual test notification to an already-open operator tab,
  badge/toast/ack and reload: `docs/audits/runtime_verification/runs/20261111T235853Z-1833e8a5/browser.log`;
  screenshots in its `screenshots/` directory, especially
  `manual-transport-notification.png` and `synthetic-incident-map.png`.
- Frontend: `npm run lint`, `npm run build`, `npm test -- --run` passed; 112 unit tests.
- Pipeline rules: a single hard stop is now suppressed for `probable_crash`. The
  review-only two-vehicle interaction rule requires calibrated closing trajectories;
  `37` focused rule/catalog tests and `236` pipeline tests passed with the configured
  local YOLOX-S model path. This is synthetic rule evidence, not collision accuracy.
- Existing integration database identity was checked before backup/migration. Revision
  `0028`, runtime app role `NOBYPASSRLS`, and FORCE RLS for all three notification
  tables were queried directly. The backup/restore rehearsal and ciphertext checksums
  are in private `backend/.integration-backups/notifications-20261111T235825Z-e3a81153/`;
  backup artifacts are intentionally not linked or copied to reports.
- The former `/tmp` ciphertext source (three files) was copied byte-for-byte to
  `backend/.integration-evidence` with SHA-256 verification. The original source
  remains untouched. The integration API was restarted by checked PID and
  `/api/health/ready` returned `{"status":"ready"}`.

## Limits and remaining gates

The browser notification proof uses a clearly manual test alert in a disposable
database. The model-derived positive incident is from an explicitly synthetic
frozen-frame fixture and is intentionally absent from operational notifications.
Moving licensed traffic footage yielded real boxes, tracks, counts and heatmap, but
it is not an independently labeled incident. This run does not establish real-world
incident accuracy, external live-camera rights, two-worker load capacity, HTTPS/PWA
background push, or completion of all 193 historical README coverage rows. The
broader README backlog must be evaluated separately; the historical matrix is not
evidence that every row passed now. A first full backend run reached 440 passed,
2 skipped and one migration-metadata mismatch (an existing notification index
missing from SQLAlchemy metadata); the metadata was corrected and a new isolated
full run is in progress.

No Git push, remote modification, database reset, account reseed or original-tree
edit was performed.
