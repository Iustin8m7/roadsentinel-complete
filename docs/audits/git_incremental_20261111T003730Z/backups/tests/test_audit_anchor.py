import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.audit_anchor import (
    AnchorError,
    LocalFileAnchor,
    public_key_fingerprint,
    verify_anchor_file,
)


def test_local_anchor_signs_and_verifies_a_checkpoint(tmp_path):
    tenant = uuid.uuid4()
    anchor = LocalFileAnchor(tmp_path / "anchors.jsonl", tmp_path / "signing.key")
    checkpoint = anchor.publish(tenant, 4, "a" * 64)
    verified = verify_anchor_file(anchor.anchor_file, anchor.public_key_file)
    assert verified == [checkpoint]
    assert anchor.latest(tenant) == checkpoint
    assert len(public_key_fingerprint(anchor.public_key_file)) == 64
    assert (tmp_path / "signing.key").stat().st_mode & 0o777 == 0o600


def test_local_anchor_rejects_older_or_conflicting_sequence(tmp_path):
    anchor = LocalFileAnchor(tmp_path / "anchors.jsonl", tmp_path / "signing.key")
    tenant = uuid.uuid4()
    anchor.publish(tenant, 2, "a" * 64)
    with pytest.raises(AnchorError, match="older or conflicts"):
        anchor.publish(tenant, 1, "b" * 64)
    with pytest.raises(AnchorError, match="older or conflicts"):
        anchor.publish(tenant, 2, "c" * 64)
    # An idempotent request for the same signed head returns the existing checkpoint.
    assert anchor.publish(tenant, 2, "a" * 64).sequence == 2


def test_local_anchor_maintains_independent_tenant_sequences(tmp_path):
    anchor = LocalFileAnchor(tmp_path / "anchors.jsonl", tmp_path / "signing.key")
    left, right = uuid.uuid4(), uuid.uuid4()
    anchor.publish(left, 1, "a" * 64)
    anchor.publish(right, 1, "b" * 64)
    anchor.publish(left, 2, "c" * 64)
    records = verify_anchor_file(anchor.anchor_file, anchor.public_key_file)
    assert [item.sequence for item in records if item.tenant_id == str(left)] == [1, 2]


def test_tampered_checkpoint_fails_signature_verification(tmp_path):
    anchor = LocalFileAnchor(tmp_path / "anchors.jsonl", tmp_path / "signing.key")
    anchor.publish(uuid.uuid4(), 1, "a" * 64)
    text = anchor.anchor_file.read_text()
    anchor.anchor_file.write_text(text.replace("a" * 64, "b" * 64))
    with pytest.raises(AnchorError, match="signature"):
        verify_anchor_file(anchor.anchor_file, anchor.public_key_file)


def test_anchor_verification_needs_the_separately_custodied_public_key(tmp_path):
    anchor = LocalFileAnchor(tmp_path / "anchors.jsonl", tmp_path / "signing.key")
    anchor.publish(uuid.uuid4(), 1, "a" * 64)
    with pytest.raises(FileNotFoundError):
        verify_anchor_file(anchor.anchor_file, tmp_path / "wrong.pub")
