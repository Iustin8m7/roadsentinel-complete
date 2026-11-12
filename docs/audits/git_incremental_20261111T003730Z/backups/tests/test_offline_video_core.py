from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.api.offline_video import _inspect_media, _safe_filename
from app.core.crypto import CryptoError, TenantKeyring
from app.schemas.offline_video import AnalysisCreate, CropIn
from app.services import offline_video_storage
from app.services.offline_analysis import _segment_intersection
from app.services.offline_video_storage import decrypt_range, encrypt_file, storage_key
from fastapi import HTTPException


def test_crop_and_analysis_request_bounds_are_enforced() -> None:
    crop = CropIn(x=0.1, y=0.2, width=0.7, height=0.6, confirmed=True, expected_revision=2)
    assert crop.x + crop.width <= 1
    with pytest.raises(ValueError):
        CropIn(x=0.4, y=0.1, width=0.7, height=0.5, confirmed=True, expected_revision=0)
    with pytest.raises(ValueError):
        AnalysisCreate(sample_fps=9, crop_revision=1)
    with pytest.raises(ValueError):
        AnalysisCreate(
            crop_revision=1,
            counting_line=({"x": 0.5, "y": 0.5}, {"x": 0.505, "y": 0.505}),
        )


def test_encrypted_private_media_supports_authenticated_range_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id, recording_id = uuid.uuid4(), uuid.uuid4()
    keyring = TenantKeyring(tenant_id, {1: b"k" * 32}, 1, b"i" * 32)
    monkeypatch.setattr(
        offline_video_storage,
        "get_settings",
        lambda: SimpleNamespace(evidence_dir=tmp_path),
    )
    payload = bytes(range(256)) * 1700
    source = tmp_path / "source.webm"
    source.write_bytes(payload)
    key = storage_key(tenant_id, recording_id, "source")

    encrypt_file(keyring, recording_id, source, key)

    assert (
        b"".join(
            decrypt_range(
                keyring,
                recording_id,
                key,
                start=65_530,
                end=131_090,
                plaintext_size=len(payload),
            )
        )
        == payload[65_530:131_091]
    )
    cipher_path = offline_video_storage.storage_path(key)
    with cipher_path.open("r+b") as encrypted:
        encrypted.seek(52)
        value = encrypted.read(1)
        encrypted.seek(52)
        encrypted.write(bytes([value[0] ^ 1]))
    with pytest.raises(CryptoError):
        b"".join(
            decrypt_range(
                keyring,
                recording_id,
                key,
                start=0,
                end=10,
                plaintext_size=len(payload),
            )
        )


def test_counting_line_requires_a_real_segment_crossing() -> None:
    line = ((0.0, 0.5), (1.0, 0.5))
    assert _segment_intersection((0.3, 0.4), (0.3, 0.6), *line)
    assert not _segment_intersection((0.3, 0.4), (0.3, 0.45), *line)


def test_upload_name_and_video_content_validation(tmp_path: Path) -> None:
    assert _safe_filename("../../recording.webm") == "recording.webm"
    with pytest.raises(HTTPException) as error:
        _safe_filename("../../not-a-video.txt")
    assert error.value.status_code == 415
    fixture = tmp_path / "short.webm"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:r=5:d=2",
            "-c:v",
            "libvpx",
            "-deadline",
            "realtime",
            str(fixture),
        ],
        check=True,
        timeout=20,
    )
    assert _inspect_media(fixture) == {
        "codec": "vp8",
        "width": 320,
        "height": 240,
        "duration_ms": 2000,
        "fps_num": 5,
        "fps_den": 1,
    }
