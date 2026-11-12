"""Live-stream robustness: reconnect with backoff, stall detection, bounded work queues and a
supervisor that restarts failing pipelines and records why. No torch/ultralytics needed.

Everything takes its clock / sleep / capture factory as arguments so it is tested with fakes
(tests/test_live.py) instead of a real stream."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path


def backoff_delays(base=1.0, factor=2.0, cap=60.0):
    """1, 2, 4, ... capped. A fresh generator restarts the sequence (call it after a success)."""
    d = base
    while True:
        yield min(d, cap)
        d *= factor


class LiveReader:
    """Reads a network stream on its own thread and keeps only the newest frame, so slow processing
    drops frames instead of falling behind. Reconnects with backoff when the stream ends and
    treats `stall_timeout_s` without a new frame as a lost stream (a blocked read cannot be
    interrupted, so that read thread is abandoned and a new one starts)."""

    def __init__(
        self, open_capture, fps, stall_timeout_s=30.0, sleep=time.sleep, clock=time.time, backoff=None, log=print
    ):
        self.open_capture, self.fps = open_capture, fps
        self.stall_timeout_s, self.sleep, self.clock, self.log = stall_timeout_s, sleep, clock, log
        self.backoff = backoff or (lambda: backoff_delays(1.0, 2.0, 30.0))
        self.cond = threading.Condition()
        self.frame, self.count, self.taken = None, 0, 0
        self.source_timestamp = None
        self.reconnects, self.last_reason = 0, None
        self.last_source_error = None
        self.last_frame_at = self.clock()
        self.last_check_at = self.last_frame_at
        self.snapshot_source = False
        self.started_at = self.last_frame_at
        self._gen = 0
        self._closed = False
        self._start_thread()
        threading.Thread(target=self._watchdog, daemon=True).start()

    # -- internals
    def _start_thread(self):
        self._gen += 1
        self._reader_thread = threading.Thread(target=self._run, args=(self._gen,), daemon=True)
        self._reader_thread.start()

    def _current(self, gen):
        return gen == self._gen and not self._closed

    def _run(self, gen):
        delays = self.backoff()
        while self._current(gen):
            try:
                cap = self.open_capture()
            except Exception as err:  # noqa: BLE001
                if not self._current(gen):
                    break
                self._note_reconnect(f"open failed ({type(err).__name__})")
                self.sleep(next(delays))
                continue

            self.snapshot_source = bool(getattr(cap, "is_snapshot", False))

            t0, n0 = self.clock(), self.count
            while self._current(gen):
                try:
                    ok, frame = cap.read()
                    self.last_check_at = self.clock()
                except Exception as err:  # noqa: BLE001
                    ok, frame = False, None
                    reason = f"read failed ({type(err).__name__})"
                else:
                    reason = "stream ended"
                if not self._current(gen):
                    self._release_capture(cap)
                    break
                if ok is None:  # unchanged conditional response or a deliberately rejected stale image
                    source_error = getattr(cap, "last_error", None)
                    if source_error != self.last_source_error:
                        self.last_source_error = source_error
                        if source_error:
                            self.log(f"  snapshot not processed: {source_error}")
                    continue
                if not ok:
                    self._note_reconnect(reason)
                    self._release_capture(cap)
                    self.sleep(next(delays))
                    break
                delays = self.backoff()  # healthy again: restart the backoff sequence
                self.last_source_error = None
                with self.cond:
                    self.frame, self.count = frame, self.count + 1
                    self.source_timestamp = getattr(cap, "last_modified_at", None)
                    self.last_frame_at = self.clock()
                    self.cond.notify_all()
                # Segments arrive in bursts: pace decoding at the stream's own frame rate.
                if not getattr(cap, "is_snapshot", False):
                    self.sleep(max(0.0, (self.count - n0) / self.fps - (self.clock() - t0)))
            else:
                self._release_capture(cap)

    def _release_capture(self, cap):
        try:
            cap.release()
        except Exception as err:  # noqa: BLE001
            self.log(f"  capture release failed ({type(err).__name__})")

    def _note_reconnect(self, reason):
        self.reconnects += 1
        self.last_reason = reason
        self.log(f"  stream lost ({reason}), reconnecting (#{self.reconnects})")

    def _watchdog(self):
        while not self._closed:
            time.sleep(min(1.0, max(0.05, self.stall_timeout_s / 4)))
            last_activity = self.last_check_at if self.snapshot_source else self.last_frame_at
            if self.clock() - last_activity > self.stall_timeout_s and not self._closed:
                self._note_reconnect(f"no frame for {self.stall_timeout_s:g} s")
                self.last_frame_at = self.clock()
                self._start_thread()  # abandons the blocked reader (its generation is stale)

    # -- API
    def read(self, timeout=None):
        """Newest frame and its stream time; (None, None) if `timeout` passes without a new frame."""
        with self.cond:
            if not self.cond.wait_for(lambda: self.count > self.taken, timeout):
                return None, None
            self.taken = self.count
            if getattr(self, "source_timestamp", None) is not None:
                # The inference timestamps use monotonic observation time for rate calculations;
                # the source timestamp is carried separately for display/evidence headers.
                return self.frame, self.last_frame_at - self.started_at
            return self.frame, self.count / self.fps

    def seconds_since_frame(self):
        return self.clock() - self.last_frame_at

    def close(self):
        self._closed = True
        with self.cond:
            self.cond.notify_all()
        # Let the active capture release its native decoder before interpreter teardown.
        thread = getattr(self, "_reader_thread", None)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)


class BoundedWorker:
    """One worker thread with a bounded queue and retries. When the queue is full the OLDEST
    job that is not critical is dropped and counted: memory stays bounded, nothing blocks the
    frame loop, and the loss is visible in `stats()`."""

    def __init__(self, maxsize=8, retries=3, sleep=time.sleep, backoff=None, log=print):
        self.jobs = deque()
        self.maxsize, self.retries, self.sleep, self.log = maxsize, retries, sleep, log
        self.backoff = backoff or (lambda: backoff_delays(1.0, 2.0, 30.0))
        self.cond = threading.Condition()
        self.done = self.failed = self.dropped = 0
        self.errors = deque(maxlen=20)
        self._stop = False
        self.cancelled = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def submit(self, fn, critical=False):
        with self.cond:
            if self._stop:
                return False
            if len(self.jobs) >= self.maxsize:
                victim = next((j for j in self.jobs if not j[1]), None)
                if victim is None:
                    self.dropped += 1
                    return False
                if victim is not None:
                    self.jobs.remove(victim)
                    self.dropped += 1
            self.jobs.append((fn, critical))
            self.cond.notify()
            return True

    def _run(self):
        while True:
            with self.cond:
                self.cond.wait_for(lambda: self.jobs or self._stop)
                if not self.jobs and self._stop:
                    return
                fn, _ = self.jobs.popleft()
            delays = self.backoff()
            for attempt in range(self.retries + 1):
                try:
                    fn()
                    self.done += 1
                    break
                except Exception as err:  # noqa: BLE001
                    if self.cancelled.is_set():
                        self.dropped += 1
                        break
                    if attempt == self.retries:
                        self.failed += 1
                        self.errors.append(f"{type(err).__name__}: {err}"[:200])
                        self.log(f"  giving up on a job after {attempt + 1} attempts: {err}")
                    else:
                        delay = next(delays)
                        if self.sleep is time.sleep:
                            if self.cancelled.wait(delay):
                                self.dropped += 1
                                break
                        else:
                            self.sleep(delay)

    def pending(self):
        with self.cond:
            return len(self.jobs)

    def shutdown(self, wait=True, timeout=None, *, cancel_pending=False):
        with self.cond:
            self._stop = True
            if cancel_pending:
                self.cancelled.set()
                self.dropped += len(self.jobs)
                self.jobs.clear()
            self.cond.notify_all()
        if wait:
            self.thread.join(timeout)

    def stats(self):
        return {
            "done": self.done,
            "failed": self.failed,
            "dropped": self.dropped,
            "pending": self.pending(),
            "last_errors": list(self.errors),
        }


class Supervisor:
    """Runs one subprocess per camera, restarts a failed one with exponential backoff and records
    the reason (exit code / signal / stall) in a JSON status file. SIGINT/SIGTERM stop everything
    gracefully. Per-camera resource limit: `max_memory_mb` (RLIMIT_AS, Linux only)."""

    def __init__(
        self,
        commands,
        status_path=None,
        max_memory_mb=None,
        sleep=time.sleep,
        clock=time.time,
        backoff=None,
        healthy_after_s=60.0,
        popen=subprocess.Popen,
        log=print,
    ):
        self.commands = commands  # name -> argv list
        self.status_path = Path(status_path) if status_path else None
        self.max_memory_mb, self.sleep, self.clock, self.popen, self.log = max_memory_mb, sleep, clock, popen, log
        self.backoff = backoff or (lambda: backoff_delays(2.0, 2.0, 120.0))
        self.healthy_after_s = healthy_after_s
        self.stop_event = threading.Event()
        self.state = {
            n: {"restarts": 0, "last_exit": None, "last_reason": None, "running": False, "started_at": None}
            for n in commands
        }
        self.procs = {}
        self.lock = threading.Lock()

    def _limits(self):
        if not self.max_memory_mb or sys.platform != "linux":
            return None
        import resource

        limit = int(self.max_memory_mb) * 1024 * 1024
        return lambda: resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    def _write_status(self):
        if not self.status_path:
            return
        with self.lock:
            self.status_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.status_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"updated_at": self.clock(), "cameras": self.state}, indent=2))
            os.replace(tmp, self.status_path)

    @staticmethod
    def reason_for(code):
        if code is None:
            return "running"
        if code == 0:
            return "exited normally"
        if code < 0:
            try:
                return f"killed by {signal.Signals(-code).name}"
            except ValueError:
                return f"killed by signal {-code}"
        return f"exit code {code}"

    def _supervise(self, name):
        delays = self.backoff()
        while not self.stop_event.is_set():
            started = self.clock()
            proc = self.popen(self.commands[name], preexec_fn=self._limits())
            self.procs[name] = proc
            self.state[name].update(running=True, started_at=started)
            self._write_status()
            while proc.poll() is None and not self.stop_event.is_set():
                self.sleep(0.2)
            if self.stop_event.is_set():
                self._terminate(proc)
            code = proc.poll()
            reason = self.reason_for(code)
            self.state[name].update(running=False, last_exit=code, last_reason=reason)
            if self.stop_event.is_set():
                break
            if self.clock() - started >= self.healthy_after_s:
                delays = self.backoff()  # it ran for a while: not a crash loop
            delay = next(delays)
            self.state[name]["restarts"] += 1
            self.log(f"[{name}] {reason}; restarting in {delay:g} s")
            self._write_status()
            self.stop_event.wait(delay) if self.sleep is time.sleep else self.sleep(delay)
        self._write_status()

    @staticmethod
    def _terminate(proc, grace_s=10.0):
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(grace_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def run(self):
        """Blocks until stop(); returns the final state."""
        threads = [threading.Thread(target=self._supervise, args=(n,), daemon=True) for n in self.commands]
        for t in threads:
            t.start()
        try:
            for t in threads:
                while t.is_alive():
                    t.join(0.5)
        except KeyboardInterrupt:
            self.stop()
            for t in threads:
                t.join(15)
        return self.state

    def stop(self):
        self.stop_event.set()


def main(argv=None):
    """python -m roadsentinel.live <camera.yaml>...   (environment as for roadsentinel.pipeline)"""
    import argparse

    ap = argparse.ArgumentParser(description="Supervise one live pipeline per camera")
    ap.add_argument("cameras", nargs="+")
    ap.add_argument("--status", default=str(Path.home() / ".roadsentinel" / "live-status.json"))
    ap.add_argument("--max-memory-mb", type=int, default=None)
    args = ap.parse_args(argv)
    cmds = {
        Path(c).stem: [sys.executable, "-m", "roadsentinel.pipeline", c, "--live", "--no-wandb"] for c in args.cameras
    }
    sup = Supervisor(cmds, args.status, args.max_memory_mb)
    signal.signal(signal.SIGTERM, lambda *_: sup.stop())
    signal.signal(signal.SIGINT, lambda *_: sup.stop())
    sup.run()


if __name__ == "__main__":
    main()
