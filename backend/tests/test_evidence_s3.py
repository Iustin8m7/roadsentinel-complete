"""Evidence stored in an S3-compatible bucket: only ciphertext leaves the API, under the same
relative keys as on disk, and decryption/tamper detection work the same way."""

from __future__ import annotations

import io
from typing import Any

import pytest

from app.config import get_settings
from app.services import evidence as evidence_service
from tests.conftest import World
from tests.test_contract_ingest import MP4, add_camera, post_event
from tests.test_ingest_auth import make_pipeline


class FakeS3:
    """The two boto3 calls the evidence service uses (boto3 passes Bucket/Key by keyword)."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def upload_fileobj(self, fh: Any, bucket: str, key: str, **_: Any) -> None:
        self.objects[(bucket, key)] = fh.read()

    def get_object(self, **kw: str) -> dict[str, Any]:
        if (kw["Bucket"], kw["Key"]) not in self.objects:
            raise KeyError(kw["Key"])
        return {"Body": io.BytesIO(self.objects[(kw["Bucket"], kw["Key"])])}


@pytest.fixture
def s3(monkeypatch: pytest.MonkeyPatch) -> FakeS3:
    fake = FakeS3()
    monkeypatch.setattr(get_settings(), "evidence_s3_bucket", "evidence-test")
    monkeypatch.setattr(evidence_service, "_s3_client", lambda: fake)
    return fake


def test_ingested_media_goes_to_the_bucket_as_ciphertext(
    world: World, login: Any, s3: FakeS3
) -> None:
    add_camera(world.a.id, "demo-highway")
    pipe, _ = make_pipeline(world.a.id)
    number = post_event(pipe).json()["id"]
    assert s3.objects, "nothing uploaded"
    keys = [k for _, k in s3.objects]
    assert all(k.startswith(f"{world.a.id}/") and k.endswith(".enc") for k in keys)
    assert all(MP4 not in blob for blob in s3.objects.values())  # never plaintext
    api = login(world.a.operator)
    clip_url = api.get(f"/api/events/{number}").json()["clip_url"]
    assert api.get(clip_url).content == MP4  # decrypted from the bucket on the fly


def test_tampered_object_is_not_served(world: World, login: Any, s3: FakeS3) -> None:
    add_camera(world.a.id, "demo-highway")
    pipe, _ = make_pipeline(world.a.id)
    number = post_event(pipe).json()["id"]
    for key, blob in list(s3.objects.items()):
        tampered = bytearray(blob)
        tampered[60] ^= 0xFF
        s3.objects[key] = bytes(tampered)
    api = login(world.a.operator)
    clip_url = api.get(f"/api/events/{number}").json()["clip_url"]
    assert api.get(clip_url).status_code == 500


def test_missing_object_is_a_clean_error(world: World, login: Any, s3: FakeS3) -> None:
    add_camera(world.a.id, "demo-highway")
    pipe, _ = make_pipeline(world.a.id)
    number = post_event(pipe).json()["id"]
    s3.objects.clear()
    api = login(world.a.operator)
    clip_url = api.get(f"/api/events/{number}").json()["clip_url"]
    assert api.get(clip_url).status_code == 500
