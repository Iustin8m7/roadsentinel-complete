> Current runtime verification — 2026-11-10
> Existing integrated login is now VERIFIED with MFA on5175/8003/rsint_20261110b:55446 after backup/rehearsed narrow lookup-owner repair and0022. Use [FINAL_LOGIN_HANDOFF.md](FINAL_LOGIN_HANDOFF.md), [POST_INTEGRATION_RUNTIME_VERIFICATION.md](POST_INTEGRATION_RUNTIME_VERIFICATION.md) and [FULL_INTEGRATION_E2E_VALIDATION.md](FULL_INTEGRATION_E2E_VALIDATION.md).
> Historical observations below retain their original scope/date.

# Pre-flight

Write root: /home/justin7m8/Documents/roadsentinel-integration (resolved, distinct).
Read-only roots: /home/justin7m8/Documents/roadsentinel and /home/justin7m8/Documents/roadsentinel-github-review.
Original interpreter may be executed with bytecode writes disabled; never install into it.
Current backend PID 1655813 cwd resolves to integration/backend, port 8003; frontend PID 1671183 port 5175 uses RS_API_ORIGIN=http://127.0.0.1:8003. Both direct and proxied /api/health/live returned alive.
Other services on 8001/8002/5173/5174 and PostgreSQL 55432/55444/55446 are preserved.
Credentials sources: backend/.env.integration.local and backend/.integration-test-credentials.json; contents excluded.
Existing auth changes from prior task are present. Multiple Codex processes exist; no inference of ownership from process name. No other writer has been detected from source inspection. No existing DB mutations performed.
Temporary mission cluster will be independently initialized under a unique /tmp/rsmission-* directory, TCP loopback only, with a distinct port and DB name. Tests must print effective nonsecret DB identity and guard destructive fixtures.
Compatibility risks: legacy server vs secure contract, offline origin vs alert semantics, pipeline YAML vs control config, historical docs with stale test counts, absent model artifact in integrated model path, hard-coded rs_test fixture.
