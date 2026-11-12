"""Measured processing rate of a camera (frames per second of stream time)."""
from collections import deque


class RateTracker:
    """Frames/s over a sliding window of stream timestamps; None until two frames were seen."""

    def __init__(self, window_s=60.0):
        self.window_s = window_s
        self.times = deque()

    def add(self, t):
        if self.times and t < self.times[-1]:   # the source restarted
            self.times.clear()
        self.times.append(t)
        while self.times and t - self.times[0] > self.window_s:
            self.times.popleft()

    @property
    def fps(self):
        if len(self.times) < 2:
            return None
        span = self.times[-1] - self.times[0]
        return (len(self.times) - 1) / span if span > 0 else None
