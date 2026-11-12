from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.services.live_preview import MAX_FRAME_BYTES, LivePreviewStore


def test_preview_is_tenant_scoped_latest_only_and_expires():
    now = [10.0]
    store = LivePreviewStore(clock=lambda: now[0], ttl_s=2.0)
    tenant, other = uuid.uuid4(), uuid.uuid4()
    captured_at = datetime.now(UTC)

    store.publish(tenant, "cam-1", b"\xff\xd8\xfffirst", captured_at, 1)
    store.publish(tenant, "cam-1", b"\xff\xd8\xffsecond", captured_at, 2)
    assert store.get(tenant, "cam-1").jpeg.endswith(b"second")
    assert store.get(other, "cam-1") is None

    # A retried/out-of-order frame may not replace the newest view.
    store.publish(tenant, "cam-1", b"\xff\xd8\xffold", captured_at, 1)
    assert store.get(tenant, "cam-1").sequence == 2

    now[0] += 2.1
    assert store.get(tenant, "cam-1") is None


@pytest.mark.parametrize(
    "jpeg", [b"not jpeg", b"\xff\xd8\xff" + b"x" * (MAX_FRAME_BYTES + 1)]
)
def test_preview_rejects_non_jpeg_and_oversized_payload(jpeg):
    store = LivePreviewStore()
    with pytest.raises(ValueError):
        store.publish(uuid.uuid4(), "cam-1", jpeg, datetime.now(UTC), 1)


def test_snapshot_preview_uses_bounded_low_rate_ttl():
    now = [10.0]
    store = LivePreviewStore(clock=lambda: now[0])
    tenant = uuid.uuid4()
    store.publish(tenant, "ilisesti-dn17", b"\xff\xd8\xffsnapshot", datetime.now(UTC), 1, ttl_s=120)
    now[0] += 119
    assert store.get(tenant, "ilisesti-dn17") is not None
    now[0] += 2
    assert store.get(tenant, "ilisesti-dn17") is None
    with pytest.raises(ValueError, match="ttl"):
        store.publish(
            tenant,
            "ilisesti-dn17",
            b"\xff\xd8\xffsnapshot",
            datetime.now(UTC),
            2,
            ttl_s=121,
        )
