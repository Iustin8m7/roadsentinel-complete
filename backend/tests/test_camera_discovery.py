from app.services.camera_discovery import load_camera_discovery
from tests.conftest import ApiClient, World


def test_registry_has_unique_disabled_source_profiles_and_explicit_transport_limits():
    entries = load_camera_discovery()
    by_id = {entry.id: entry for entry in entries}
    assert len(entries) == 35
    assert len(by_id) == len(entries)
    assert all(not entry.ingestion_enabled for entry in entries)
    assert all(entry.processing_authorization == "not-established" for entry in entries)
    assert by_id["RO-IS-WCR-001"].transport == "hls"
    assert by_id["RO-IS-WCR-001"].adapter == "opencv_ffmpeg_hls"
    assert by_id["RO-IS-WCR-001"].source_config_ref == "cameras/iasi-piata-unirii.yaml"
    assert by_id["RO-CJ-MUNI-001"].transport == "browser_embed"
    assert by_id["RO-DN17-TL-001"].status == "replay-only"
    assert not by_id["RO-BV-LINX-001"].counting_lines
    assert not by_id["RO-BV-LINX-001"].zones


def test_registry_endpoint_enforces_camera_read_permission_and_returns_canonical_rows(
    world: World, client: ApiClient, login
):
    assert client.get("/api/cameras/discovery").status_code == 401
    assert login(world.a.auditor).get("/api/cameras/discovery").status_code == 403

    response = login(world.a.operator).get("/api/cameras/discovery")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 35
    assert len({row["id"] for row in rows}) == 35
    assert all(row["ingestionEnabled"] is False for row in rows)
    assert all(row["processingAuthorization"] == "not-established" for row in rows)
    assert next(row for row in rows if row["id"] == "RO-DN17-TL-001")["status"] == "replay-only"
