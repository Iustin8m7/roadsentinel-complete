# GitHub source baseline

Remote https://github.com/CristiMachine25/roadsentinel.git; review HEAD 451beb99447dcce88f1bf7288195322689f368c4; target/origin-main 47e3e85aa687a24eb000df1ee57b810e587e5fd8.33 reachable commits,60 files,3804 insertions/464 deletions; no deletions or detected renames/copies. Ancestry exit0, diff-check exit0. All60 snapshot blobs match pinned Git objects. Full commit parent log/name-status/stat/numstat/binary delta are retained. No fetch/remote mutation was performed.

Destination has no Git metadata. Baseline source preimages and mode-preserving backups are private under backups/; secrets/models/media/runtime data excluded. Historical Codex processes exist, an advisory lock is held and preimage checks detected no independent source edits. Original reference source hashes/status/HEAD are captured in reference-baseline.json.

The current app's authentication and data safeguards take precedence over source demo shortcuts. Candidate merges are review inputs only. No schema migration or live seed is planned; additive source-kind serialization uses existing columns and editor fields use existing JSONB. Tests use uniquely named disposable clusters. Runtime identity is verified in runtime-baseline.json, never inferred from dotenv alone.

## Reproducible read-only discovery

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
git -C ../roadsentinel-github-review remote get-url origin
git -C ../roadsentinel-github-review rev-parse HEAD origin/main 47e3e85
git -C ../roadsentinel-github-review merge-base --is-ancestor 451beb99447dcce88f1bf7288195322689f368c4 47e3e85
git -C ../roadsentinel-github-review log --format='%H%x09%P%x09%s' 451beb99447dcce88f1bf7288195322689f368c4..47e3e85
git -C ../roadsentinel-github-review diff --find-renames --name-status 451beb99447dcce88f1bf7288195322689f368c4 47e3e85
git -C ../roadsentinel-github-review diff --stat 451beb99447dcce88f1bf7288195322689f368c4 47e3e85
git -C ../roadsentinel-github-review diff --check 451beb99447dcce88f1bf7288195322689f368c4 47e3e85
```

All paths were physically resolved before writes. The optional `../roadsentinel-github-latest-47e3e85` snapshot exists and its 60 relevant blobs match the pinned Git objects; no guessed snapshot or newer unreviewed commit was used. Source extraction under this audit directory is not a served runtime directory. `source/`, `base/`, `candidates/` and `backups/` are archived preimages with their original link roots, not current product documentation. The docs checker excludes only these archive subdirectories; current reports are still checked.

## Runtime and reference identity

- Native A before: Vite PID1671183 at5175, FastAPI PID2033731 at8003, integration cwd, actual SQL `rsint_20261110b / 127.0.0.1 / 55446 / rsint_app_261110b`, revision0022,32 FORCE RLS tables, app NOBYPASSRLS. [Baseline](runtime-baseline.json).
- Native A after: only owned FastAPI restarted as PID2107404 after scoped development-tenant jobs/leases were zero. No migration/seed. [Pre-restart check](native-pre-restart.json), [restart](native-restart.log), [actual final probes](runtime-after.json).
- Tests B: newly named `rsmission_verify_*` databases in newly initialized `/tmp/rsverify-*` loopback clusters; every run has `database.json`, exact commands/timestamps and owned shutdown. No competing service was launched on native ports.
- References C: [759 selected source hashes and both tracked statuses/HEADs unchanged](reference-after.json): original381, review378. This is a selected-source comparison, not a hash of private media, credentials, logs or ignored runtime files. Existing original uncommitted changes were preserved.
- System UTC advanced discontinuously between early baseline work and later test execution. Per-command timestamps and monotonic durations are retained in `commands.json`; directory naming is the initial checkpoint time, not a claim of uninterrupted wall-clock execution.

Final late-timing source activation: the same owned restart checks ran again after the additive output-FPS change; final backend PID2150043, frontend PID1671183. [Final runtime](runtime-final.json), [late pre-restart](native-timing-pre-restart.json), [late restart](native-timing-restart.log), [fresh final four-role browser proof](native-final/live-browser-result.json). No migration/seed in either restart.
