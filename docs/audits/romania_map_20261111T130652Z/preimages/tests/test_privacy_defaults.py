"""Integration review: nothing leaves the machine unless explicitly enabled, and batch runs
against the secure backend survive its production refusal to reset cameras."""
import httpx
import pytest

from roadsentinel import sink, tracking, vlm


def test_vlm_is_off_by_default_even_with_an_api_key(monkeypatch):
    monkeypatch.delenv("RS_EXTERNAL_AI", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    assert vlm.available() is False
    assert vlm.check({"keyframe": "never-read.jpg", "clip": "never-read.mp4"})["vlm_status"] == "skipped"


def test_vlm_can_be_enabled_explicitly(monkeypatch):
    monkeypatch.setenv("RS_EXTERNAL_AI", "frames")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    assert vlm.available() is True


def test_experiment_tracking_is_off_by_default(monkeypatch):
    monkeypatch.delenv("RS_EXPERIMENT_TRACKING", raising=False)
    monkeypatch.setattr(tracking, "_has_key", lambda: True)
    assert tracking.start({"id": "cam"}, "yolo11s.pt", 1280) is None


@pytest.mark.parametrize("status", [403])
def test_camera_reset_refused_in_production_is_not_fatal(monkeypatch, status):
    remote = sink.RemoteSink("https://example.invalid", "rsk_testkey123", "secret")

    def refused(method, path, **kwargs):
        request = httpx.Request(method, f"https://example.invalid{path}")
        raise httpx.HTTPStatusError("refused", request=request,
                                    response=httpx.Response(status, request=request))

    monkeypatch.setattr(remote, "_send", refused)
    remote.clear_camera("demo-highway")  # must not raise


def test_other_reset_errors_still_fail(monkeypatch):
    remote = sink.RemoteSink("https://example.invalid", "rsk_testkey123", "secret")

    def broken(method, path, **kwargs):
        request = httpx.Request(method, f"https://example.invalid{path}")
        raise httpx.HTTPStatusError("boom", request=request,
                                    response=httpx.Response(500, request=request))

    monkeypatch.setattr(remote, "_send", broken)
    with pytest.raises(httpx.HTTPStatusError):
        remote.clear_camera("demo-highway")
