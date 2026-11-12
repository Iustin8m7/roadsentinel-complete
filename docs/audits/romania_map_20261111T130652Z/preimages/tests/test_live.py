import json
import subprocess
import sys
import threading
import time

from roadsentinel.live import BoundedWorker, LiveReader, Supervisor, backoff_delays


class FakeCapture:
    def __init__(self, script):
        self.script = list(script)
        self.released = False

    def read(self):
        if not self.script:
            time.sleep(0.01)
            return False, None
        item = self.script.pop(0)
        if item == "block":
            threading.Event().wait(5)       # a read that hangs
            return False, None
        return (True, item) if item is not None else (False, None)

    def release(self):
        self.released = True


def test_backoff_doubles_and_is_capped():
    d = backoff_delays(1, 2, 8)
    assert [next(d) for _ in range(6)] == [1, 2, 4, 8, 8, 8]


def wait_for(cond, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_reader_reconnects_after_a_lost_stream_and_keeps_only_the_newest_frame():
    opens = []

    def open_capture():
        opens.append(1)
        return FakeCapture(["a", "b", None] if len(opens) == 1 else ["c", "d", "e"])

    r = LiveReader(open_capture, fps=1000, stall_timeout_s=10, sleep=lambda s: None, log=lambda *_: None)
    assert wait_for(lambda: r.count >= 5)
    frame, _ = r.read(timeout=1)
    assert frame == "e" and r.reconnects >= 1 and len(opens) >= 2   # old frames were dropped
    assert r.last_reason == "stream ended"
    r.close()


def test_reader_recovers_from_capture_open_and_read_exceptions():
    opens = []

    class BrokenCapture:
        def read(self):
            raise OSError("temporary transport failure")

        def release(self):
            pass

    class StableCapture:
        def read(self):
            return True, "recovered"

        def release(self):
            pass

    def open_capture():
        opens.append(True)
        if len(opens) == 1:
            raise ConnectionError("endpoint unavailable")
        if len(opens) == 2:
            return BrokenCapture()
        return StableCapture()

    reader = LiveReader(open_capture, fps=1000, stall_timeout_s=10, sleep=lambda _: None, log=lambda *_: None)
    assert wait_for(lambda: reader.count >= 1)
    assert reader.read(timeout=1)[0] == "recovered"
    assert reader.reconnects >= 2 and len(opens) >= 3
    reader.close()


def test_reader_detects_a_stalled_stream_and_starts_a_new_reader():
    opens = []

    def open_capture():
        opens.append(1)
        return FakeCapture(["x", "block"] if len(opens) == 1 else ["y", "z"])

    r = LiveReader(open_capture, fps=1000, stall_timeout_s=0.2, sleep=lambda s: None, log=lambda *_: None)
    assert wait_for(lambda: r.reconnects >= 1, 3)
    assert "no frame" in r.last_reason
    assert wait_for(lambda: r.count >= 3, 3)               # frames flow again from the new reader
    assert r.read(timeout=1)[0] == "z"
    r.close()


def test_read_times_out_instead_of_blocking_forever():
    r = LiveReader(lambda: FakeCapture([]), fps=10, stall_timeout_s=100, sleep=lambda s: None, log=lambda *_: None)
    assert r.read(timeout=0.1) == (None, None)
    r.close()


def test_worker_retries_then_succeeds_and_counts_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("network down")

    w = BoundedWorker(retries=3, sleep=lambda s: None, log=lambda *_: None)
    w.submit(flaky)
    w.submit(lambda: (_ for _ in ()).throw(RuntimeError("always")))
    w.shutdown(wait=True, timeout=5)
    s = w.stats()
    assert calls["n"] == 3 and s["done"] == 1 and s["failed"] == 1
    assert "RuntimeError" in s["last_errors"][0]


def test_worker_queue_is_bounded_and_drops_oldest_non_critical():
    gate = threading.Event()
    w = BoundedWorker(maxsize=2, sleep=lambda s: None, log=lambda *_: None)
    w.submit(gate.wait)                       # occupies the worker
    assert wait_for(lambda: w.pending() == 0)
    for _ in range(5):
        w.submit(lambda: None)
    assert w.pending() == 2 and w.stats()["dropped"] == 3
    w.submit(lambda: None, critical=True)     # a critical job displaces a normal one
    assert w.pending() == 2 and w.stats()["dropped"] == 4
    gate.set()
    w.shutdown(wait=True, timeout=5)


def test_supervisor_restarts_a_failing_process_and_records_the_reason(tmp_path):
    status = tmp_path / "status.json"
    sleeps = []
    sup = Supervisor({"cam": [sys.executable, "-c", "import sys; sys.exit(3)"]}, status,
                     sleep=lambda s: sleeps.append(s) or time.sleep(0.01), healthy_after_s=1e9,
                     backoff=lambda: backoff_delays(2, 2, 8), log=lambda *_: None)
    t = threading.Thread(target=sup.run, daemon=True)
    t.start()
    assert wait_for(lambda: sup.state["cam"]["restarts"] >= 3, 10)
    sup.stop()
    t.join(10)
    st = json.loads(status.read_text())["cameras"]["cam"]
    assert st["last_reason"] == "exit code 3" and st["restarts"] >= 3
    delays = [s for s in sleeps if s >= 2]
    assert delays[:3] == [2, 4, 8]


def test_supervisor_stops_a_healthy_process_gracefully(tmp_path):
    sup = Supervisor({"cam": [sys.executable, "-c", "import time; time.sleep(60)"]}, tmp_path / "s.json",
                     log=lambda *_: None)
    t = threading.Thread(target=sup.run, daemon=True)
    t.start()
    assert wait_for(lambda: sup.state["cam"]["running"], 5)
    sup.stop()
    t.join(15)
    assert not t.is_alive() and sup.state["cam"]["running"] is False
    assert sup.procs["cam"].poll() is not None


def test_reason_names_signals():
    assert Supervisor.reason_for(-9) == "killed by SIGKILL"
    assert Supervisor.reason_for(0) == "exited normally"
    assert subprocess  # imported for clarity of the subprocess based tests


def test_revoked_worker_cancels_queued_critical_jobs_and_interrupts_retry_backoff():
    attempted = threading.Event()
    release = threading.Event()
    calls = []

    def unavailable():
        calls.append('attempt')
        attempted.set()
        release.wait(2)
        raise ConnectionError('authorization or source unavailable')

    worker = BoundedWorker(retries=5, backoff=lambda: iter([30.0] * 5), log=lambda _: None)
    assert worker.submit(unavailable, critical=True)
    assert attempted.wait(2)
    assert worker.submit(lambda: calls.append('queued-critical'), critical=True)
    release.set()
    worker.shutdown(wait=True, timeout=1, cancel_pending=True)
    assert not worker.thread.is_alive()
    assert calls == ['attempt']
    assert worker.pending() == 0 and worker.stats()['dropped'] == 2
    assert worker.submit(lambda: calls.append('after-stop')) is False
