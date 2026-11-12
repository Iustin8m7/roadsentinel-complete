"""Minimal ISO-BMFF reader: the presentation duration from ``moov/mvhd``.

Used to validate bookmark/note timestamps against the real clip length. Returns ``None`` when
the header is missing or malformed (the caller then refuses timestamps it cannot check)."""

from __future__ import annotations

import struct

_MAX_BOXES = 10_000


def _boxes(data: bytes, start: int, end: int) -> list[tuple[bytes, int, int]]:
    """(type, payload start, payload end) of the boxes in data[start:end]."""
    out: list[tuple[bytes, int, int]] = []
    pos = start
    while pos + 8 <= end and len(out) < _MAX_BOXES:
        size, kind = struct.unpack(">I4s", data[pos : pos + 8])
        header = 8
        if size == 1:
            if pos + 16 > end:
                break
            size = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            break
        out.append((kind, pos + header, pos + size))
        pos += size
    return out


def duration_seconds(data: bytes) -> float | None:
    for kind, start, end in _boxes(data, 0, len(data)):
        if kind != b"moov":
            continue
        for inner, s, e in _boxes(data, start, end):
            if inner != b"mvhd" or e - s < 20:
                continue
            version = data[s]
            if version == 1:
                if e - s < 32:
                    return None
                timescale, duration = struct.unpack(">IQ", data[s + 20 : s + 32])
            else:
                timescale, duration = struct.unpack(">II", data[s + 12 : s + 20])
            if timescale == 0 or duration in (0, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
                return None
            return round(duration / timescale, 3)
    return None
