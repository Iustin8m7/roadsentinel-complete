"""Live network streams require source-specific permission evidence.

A camera yaml whose `video` is a URL must carry:

    source_consent:
      granted: true
      by: "WebcamRomania.ro / Grand Hotel Traian (name of the person or role)"
      date: "2026-11-10"
      scope: "demo and training, internal"      # what was allowed
      evidence: "email 2026-11-10, stored in <where>"   # where the written permission is kept
      licence: "..."                             # terms, if any

Without it the live pipeline refuses to start. A narrowly scoped, ignored local owner-attestation
file is supported for the owner-attested Ilișești source; no document contents are stored. Local
video files are not affected (their licences are listed in docs/DATA_LICENSES.md).
"""

import hashlib
import json
import os
import stat
from pathlib import Path


class ConsentError(Exception):
    pass


FIELDS = ("by", "date", "scope", "evidence")
CAMERA_DIR = Path(__file__).resolve().parents[1] / "cameras"


def _check_local_attestation(cfg, consent):
    """Validate only the one explicitly owner-attested camera against a private local record."""
    if cfg.get("id") != "ilisesti-dn17":
        return False
    reference = consent.get("local_attestation_file")
    if reference != ".local/ilisesti-dn17-attestation.json":
        return False
    path = CAMERA_DIR / reference
    private_dir = CAMERA_DIR / ".local"
    try:
        if private_dir.is_symlink() or path.is_symlink():
            raise ConsentError("local source attestation must not use symlinks")
        resolved = path.resolve(strict=True)
        if resolved.parent != private_dir.resolve(strict=True) or not resolved.is_file():
            raise ConsentError("local source attestation path is not allowed")
        if private_dir.stat().st_uid != os.geteuid() or stat.S_IMODE(private_dir.stat().st_mode) != 0o700:
            raise ConsentError("local source attestation directory must be owner-only (0700)")
        if resolved.stat().st_uid != os.geteuid() or stat.S_IMODE(resolved.stat().st_mode) != 0o600:
            raise ConsentError("local source attestation file must be owner-only (0600)")
        attestation = json.loads(resolved.read_text(encoding="utf-8"))
    except ConsentError:
        raise
    except (OSError, ValueError) as exc:
        raise ConsentError(f"local source attestation is unavailable or invalid ({type(exc).__name__})") from None
    source_digest = hashlib.sha256(str(cfg.get("video", "")).encode()).hexdigest()
    required = {
        "schema_version": 1,
        "camera_id": "ilisesti-dn17",
        "source_url_sha256": source_digest,
        "authorization_kind": "owner_attested_written_provider_approval",
        "processing_allowed": True,
        "recording_allowed": False,
        "redistribution_allowed": False,
        "attested_by": "project owner",
        "evidence": "written provider approval, held offline by project owner; scope details not copied into repository",
    }
    if not isinstance(attestation, dict) or any(attestation.get(key) != value for key, value in required.items()):
        raise ConsentError("local source attestation does not match this camera/source and transient scope")
    if not isinstance(attestation.get("attested_at"), str) or not attestation["attested_at"].strip():
        raise ConsentError("local source attestation has no attestation date")
    if not isinstance(attestation.get("scope"), str) or not attestation["scope"].strip():
        raise ConsentError("local source attestation has no processing scope")
    return True


def check_source_consent(cfg):
    video = str(cfg.get("video", ""))
    if "://" not in video:
        return True
    c = cfg.get("source_consent") or {}
    if c.get("granted") is not True and _check_local_attestation(cfg, c):
        return True
    if c.get("granted") is not True:
        raise ConsentError(
            f"{cfg.get('id', video)}: live source {video} has no documented permission (source_consent.granted). "
            "The stream belongs to its owner; get written permission and record it in the camera yaml.")
    missing = [f for f in FIELDS if not str(c.get(f, "")).strip()]
    if missing:
        raise ConsentError(f"{cfg.get('id', video)}: source_consent is missing {missing}")
    return True
