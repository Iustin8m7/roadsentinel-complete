"""Serve a licensed local recording as a loopback-only, real-time MJPEG replay."""

from __future__ import annotations

import argparse
import ipaddress
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import cv2


def make_server(video: str | Path, host: str, port: int, fps: float) -> ThreadingHTTPServer:
    try:
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("host must be a loopback IP address")
    except ValueError as exc:
        raise ValueError("replay server binds only to 127.0.0.1 or ::1") from exc
    path = Path(video).expanduser().resolve()
    if not path.is_file() or not 0.2 <= fps <= 30:
        raise ValueError("video must exist and replay fps must be between 0.2 and 30")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if urlsplit(self.path).path == "/health":
                body = json.dumps({"state": "replay", "fps": fps}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if urlsplit(self.path).path != "/stream.mjpg":
                self.send_error(404)
                return
            capture = cv2.VideoCapture(str(path))
            if not capture.isOpened():
                self.send_error(503)
                return
            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            frame_index = 0
            started = time.monotonic()
            try:
                while True:
                    ok, frame = capture.read()
                    if not ok:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
                    if not ok:
                        continue
                    payload = encoded.tobytes()
                    packet = (
                        b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                        + str(len(payload)).encode()
                        + b"\r\n\r\n"
                        + payload
                        + b"\r\n"
                    )
                    self.wfile.write(packet)
                    self.wfile.flush()
                    frame_index += 1
                    time.sleep(max(0.0, frame_index / fps - (time.monotonic() - started)))
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                capture.release()

        def log_message(self, *_: object) -> None:
            return

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    server = Server((host, port), Handler)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--fps", type=float, default=10)
    args = parser.parse_args()
    server = make_server(args.video, args.host, args.port, args.fps)
    print(f"Local replay serving on {args.host}:{args.port}/stream.mjpg at {args.fps:g} FPS")
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
