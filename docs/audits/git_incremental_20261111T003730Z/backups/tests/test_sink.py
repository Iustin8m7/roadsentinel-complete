"""Wire-level ingestion signatures and explicit outbound privacy controls."""
import base64
import hashlib
import hmac
import json
from email.parser import BytesParser
from email.policy import default

import httpx
import pytest

from roadsentinel import sink, tracking, vlm


def backend_signature(secret, method, target, timestamp, nonce, body):
    # Mirrors backend/app/services/ingest_auth.py signing_message + sign.
    message = '\n'.join([method.upper(), target, timestamp, nonce,
                         hashlib.sha256(body).hexdigest()]).encode()
    return base64.urlsafe_b64encode(hmac.new(secret.encode(), message, hashlib.sha256).digest()).decode().rstrip('=')


@pytest.fixture
def remote():
    instance = sink.RemoteSink('http://test', 'rsk_test_key', 'test-secret')
    instance.http.close()
    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(200, json={'id': 17})

    instance.http = httpx.Client(base_url='http://test', transport=httpx.MockTransport(handler))
    yield instance, received
    instance.http.close()


def assert_signed(request):
    headers = request.headers
    assert 'authorization' not in headers
    assert headers['X-RS-Key-Id'] == 'rsk_test_key'
    assert headers['X-RS-Signature'] == backend_signature(
        'test-secret', request.method, request.url.raw_path.decode(),
        headers['X-RS-Timestamp'], headers['X-RS-Nonce'], request.content)


def test_signed_multipart_preserves_bytes_and_redaction(remote, tmp_path):
    client, received = remote
    keyframe, clip = tmp_path / 'private-name.jpg', tmp_path / 'private-name.mp4'
    keyframe.write_bytes(b'\xff\x00jpg')
    clip.write_bytes(b'\x00\xffmp4')
    assert client.add_event({'priority': 'high', 'redaction': 'full'}, keyframe, clip) == 17
    [request] = received
    assert_signed(request)
    parts = list(BytesParser(policy=default).parsebytes(
        b'Content-Type: ' + request.headers['content-type'].encode() + b'\r\n\r\n' + request.content).iter_parts())
    event = json.loads(parts[0].get_payload(decode=True))
    assert 'priority' not in event
    assert 'redaction' not in event
    assert event['details']['redaction'] == 'full'
    assert [part.get_filename() for part in parts[1:]] == ['keyframe.jpg', 'clip.mp4']
    assert [part.get_payload(decode=True) for part in parts[1:]] == [keyframe.read_bytes(), clip.read_bytes()]


def test_all_ingest_operations_signed_with_fresh_nonce(remote, tmp_path):
    client, received = remote
    clip = tmp_path / 'video.mp4'
    clip.write_bytes(b'video')
    client.clear_camera('cam-test')
    client.add_camera_video('cam-test', clip)
    client._send('POST', '/api/ingest/ping?camera=a%20b', content=b'known-body')
    for request in received:
        assert_signed(request)
    assert len({r.headers['X-RS-Nonce'] for r in received}) == 3
    assert received[0].content == b''


@pytest.mark.parametrize('missing', ['RS_INGEST_KEY_ID', 'RS_INGEST_SECRET'])
def test_remote_requires_both_credentials(monkeypatch, missing):
    monkeypatch.setenv('RS_API_URL', 'http://test')
    monkeypatch.setenv('RS_INGEST_KEY_ID', 'rsk_test_key')
    monkeypatch.setenv('RS_INGEST_SECRET', 'test-secret')
    monkeypatch.delenv(missing)
    with pytest.raises(SystemExit, match=missing):
        sink.from_env()


@pytest.mark.parametrize('mode', ['off', 'search_text'])
def test_no_frames_in_restricted_modes(monkeypatch, mode):
    monkeypatch.setenv('RS_EXTERNAL_AI', mode)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
    def forbidden(*args, **kwargs):
        pytest.fail('restricted mode must not read media or contact provider')
    monkeypatch.setattr(vlm, '_frames', forbidden)
    assert vlm.check({})['vlm_status'] == 'skipped'
    assert vlm.verify({}, client=object()) is None
    assert not vlm.available()


def test_tracking_optout_overrides_explicit_enable_and_uploads(monkeypatch):
    monkeypatch.setenv('RS_EXPERIMENT_TRACKING', 'off')
    monkeypatch.setenv('WANDB_API_KEY', 'test-key')
    assert tracking.start({}, 'model', 640, enabled=True) is None
    tracking.finish(object(), {}, [], [], 'missing.mp4')


def test_standalone_ping_signer_known_vector(monkeypatch):
    from pipeline import client_example
    monkeypatch.setattr(client_example.time, 'time', lambda: 1700000000)
    monkeypatch.setattr(client_example.secrets, 'token_urlsafe', lambda _: 'fixed_nonce_12345')
    request = httpx.Request('POST', 'https://example.test/api/ingest/ping?q=a%20b', content=b'{}')
    client_example.sign_request(request, 'rsk_test_key', 'test-secret')
    assert_signed(request)
    assert request.headers['X-RS-Timestamp'] == '1700000000'
    # Generated with the backend's actual sign/signing_message functions.
    assert request.headers['X-RS-Signature'] == 'Lcj6x99GoNO-3zCiON2w2dCbAjrmJlf_oARf8aEv7BI'
    assert request.headers['X-RS-Signature'] == backend_signature(
        'test-secret', 'POST', '/api/ingest/ping?q=a%20b', '1700000000', 'fixed_nonce_12345', b'{}')


def test_heartbeat_is_a_signed_post_for_the_camera(remote):
    client, received = remote
    client.heartbeat('iasi-piata-unirii')
    [request] = received
    assert request.method == 'POST'
    assert request.url.path == '/api/ingest/cameras/iasi-piata-unirii/heartbeat'
    assert_signed(request)
