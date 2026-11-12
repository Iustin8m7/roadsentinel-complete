# Pipeline integration

The running detector is in `roadsentinel/`, with camera configuration in `cameras/`.
This directory holds integration documentation and the standalone signing example when
`feature/pipeline-hmac` is merged; it is not a second detector implementation.

## Secure backend contract

The coordinated integration uses **`POST /api/ingest/events`**, authenticated with a
per-tenant HMAC service account. Do not write directly to the secure backend database.
The event endpoint is delivered by `feature/contract-api` (PR #12); this branch's
baseline backend provides the HMAC connectivity check at `POST /api/ingest/ping`.
The matching sender is delivered by `feature/pipeline-hmac`.

Configure the sender with `RS_API_URL`, `RS_INGEST_KEY_ID` and `RS_INGEST_SECRET`.
Create the service account inside the secure stack:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml exec backend \
  python -m app.cli create-service-account --tenant unit-a --name pipeline-1
```

The secret is shown once; keep it out of source control and logs. Register the camera
in the same tenant and ensure the account's camera scope permits it (see [API.md](../API.md)).

Each request carries `X-RS-Key-Id`, `X-RS-Timestamp` (Unix seconds), `X-RS-Nonce` and
`X-RS-Signature`. Sign the exact bytes sent, including multipart boundaries:

```text
METHOD\nPATH?QUERY\nTIMESTAMP\nNONCE\nhex(sha256(body))
```

The signature is HMAC-SHA256 with the service secret, encoded as base64url without padding.
The timestamp must be within 60 seconds and each nonce is single-use. Build the HTTP request
once, read its body once, and send that same request; do not rebuild multipart after signing.
See [integration plan §3.3](../docs/INTEGRATION_PLAN.md#33-per-tenant-hmac-ingestion-replacing-ingest_token).

The multipart fields are `event` (JSON), `keyframe` (`keyframe.jpg`, JPEG) and `clip`
(`clip.mp4`, MP4). Do not send `priority`; the server derives it from the event type.
The secure backend rejects unknown event fields and validates camera ownership and media.

## Evidence and reset behavior

Only redacted evidence goes through this transport. Redact before producing keyframes,
clips or external uploads; label the mode accurately (`full` or `heads_only` in event
`details.redaction`). `heads_only` leaves plates visible and requires the UI warning.
The secure backend stores uploaded media as encrypted redacted evidence; this transport
does not supply an original variant. Do not claim that originals are available for unblur.
Plate text belongs only in the backend's encrypted plate field, never descriptions or logs.

Use `--live` for append-only remote operation. In the secure contract, camera reset
(`DELETE /api/ingest/cameras/{id}`) returns `403` in production; development reset only
supersedes undecided events and retains decisions, evidence and audit history. The
legacy local demo reset is destructive and must not target an operational event store.

For an offline demo, leave `RS_API_URL` unset and use the separate legacy
`roadsentinel.server` / local store. Legacy bearer-token ingestion is not authentication
for the secure backend. See the root [README](../README.md) for local starts.
