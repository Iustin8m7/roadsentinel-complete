import hashlib
import json
from pathlib import Path

import pytest
import yaml

from roadsentinel import consent
from roadsentinel.consent import ConsentError, check_source_consent

FULL = {"granted": True, "by": "Owner", "date": "2026-11-10", "scope": "demo", "evidence": "email, shared drive"}


def test_local_files_need_no_consent_entry():
    check_source_consent({"id": "c", "video": "data/videos/x.mp4"})


def test_network_stream_without_permission_is_refused():
    with pytest.raises(ConsentError, match="no documented permission"):
        check_source_consent({"id": "c", "video": "https://example.org/live.m3u8"})
    with pytest.raises(ConsentError, match="no documented"):
        check_source_consent({"id": "c", "video": "rtsp://cam/1", "source_consent": {**FULL, "granted": False}})


def test_permission_must_say_who_when_scope_and_where_the_proof_is():
    with pytest.raises(ConsentError, match="evidence"):
        check_source_consent({"id": "c", "video": "https://x/y.m3u8", "source_consent": {**FULL, "evidence": ""}})
    check_source_consent({"id": "c", "video": "https://x/y.m3u8", "source_consent": FULL})


def test_the_shipped_iasi_camera_is_off_until_someone_records_the_permission():
    cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "cameras" / "iasi-piata-unirii.yaml").read_text())
    with pytest.raises(ConsentError):
        check_source_consent(cfg)


def test_the_shipped_iasi_config_reports_what_it_can_do_at_its_measured_rate():
    from roadsentinel.rules import rule_capabilities

    cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "cameras" / "iasi-piata-unirii.yaml").read_text())
    caps = rule_capabilities(cfg["thresholds"], 0.45, cfg["rules"])
    assert caps["very_high_speed"]["supported"] is True        # low-fps time-window mode
    assert caps["probable_crash"]["supported"] is False        # needs ~7 fps; the UI says so


def test_ilisesti_local_attestation_is_private_source_bound_and_transient(tmp_path, monkeypatch):
    camera_dir = tmp_path / "cameras"
    private_dir = camera_dir / ".local"
    private_dir.mkdir(parents=True, mode=0o700)
    private_dir.chmod(0o700)
    monkeypatch.setattr(consent, "CAMERA_DIR", camera_dir)
    source_url = "https://webcamromania.ro/media/snapshots/id/latest.jpg"
    payload = {
        "schema_version": 1,
        "camera_id": "ilisesti-dn17",
        "source_url_sha256": hashlib.sha256(source_url.encode()).hexdigest(),
        "authorization_kind": "owner_attested_written_provider_approval",
        "processing_allowed": True,
        "recording_allowed": False,
        "redistribution_allowed": False,
        "attested_by": "project owner",
        "attested_at": "2026-11-07T20:00:00+00:00",
        "scope": "local transient inference only",
        "evidence": "written provider approval, held offline by project owner; scope details not copied into repository",
    }
    record = private_dir / "ilisesti-dn17-attestation.json"
    record.write_text(json.dumps(payload), encoding="utf-8")
    record.chmod(0o600)
    cfg = {
        "id": "ilisesti-dn17",
        "video": source_url,
        "source_consent": {"local_attestation_file": ".local/ilisesti-dn17-attestation.json"},
    }
    assert check_source_consent(cfg) is True
    with pytest.raises(ConsentError, match="does not match"):
        check_source_consent({**cfg, "video": source_url + "?other=source"})
    with pytest.raises(ConsentError, match="no documented permission"):
        check_source_consent({**cfg, "id": "another-camera"})
