"""Create the private local record for the owner-attested Ilișești source scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "cameras" / "ilisesti-dn17.yaml"
TARGET = ROOT / "cameras" / ".local" / "ilisesti-dn17-attestation.json"
SCOPE = (
    "One-camera local transient YOLOX-S/ByteTrack processing; no recorded video, "
    "evidence export, retention, or redistribution; annotated preview remains in "
    "the existing tenant-scoped in-memory preview service."
)


def write_attestation() -> Path:
    import yaml

    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    target_dir = TARGET.parent
    target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target_dir.is_symlink():
        raise RuntimeError("private attestation directory must not be a symlink")
    os.chmod(target_dir, 0o700)
    if target_dir.stat().st_uid != os.geteuid():
        raise RuntimeError("private attestation directory must be owned by the current user")
    payload = {
        "schema_version": 1,
        "camera_id": "ilisesti-dn17",
        "source_url_sha256": hashlib.sha256(profile["video"].encode()).hexdigest(),
        "authorization_kind": "owner_attested_written_provider_approval",
        "processing_allowed": True,
        "recording_allowed": False,
        "redistribution_allowed": False,
        "attested_by": "project owner",
        "attested_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scope": SCOPE,
        "evidence": "written provider approval, held offline by project owner; scope details not copied into repository",
    }
    fd, temp_name = tempfile.mkstemp(prefix=".attestation-", dir=target_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, TARGET)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return TARGET


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-narrow-scope",
        action="store_true",
        help="confirm the transient, no-recording/no-redistribution scope shown by this command",
    )
    args = parser.parse_args()
    if not args.confirm_narrow_scope:
        parser.error("owner confirmation required: pass --confirm-narrow-scope after reviewing the scope")
    target = write_attestation()
    print(f"Private local source attestation written (0600): {target}")
    print(f"Scope: {SCOPE}")
    print("The provider approval document remains offline and was not copied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
