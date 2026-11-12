"""Single byte ranges over authenticated decrypted streams, without plaintext staging."""

import re
from collections.abc import Iterable, Iterator


def bounds(header: str, size: int) -> tuple[int, int]:
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not match or size <= 0 or not any(match.groups()):
        raise ValueError("Unsatisfiable byte range")
    left, right = match.groups()
    if not left:
        length = int(right)
        if length <= 0:
            raise ValueError("Unsatisfiable byte range")
        return max(0, size - length), size - 1
    start, end = int(left), min(int(right), size - 1) if right else size - 1
    if start >= size or end < start:
        raise ValueError("Unsatisfiable byte range")
    return start, end


def slice_stream(chunks: Iterable[bytes], start: int, end: int) -> Iterator[bytes]:
    offset = 0
    try:
        for chunk in chunks:
            next_offset = offset + len(chunk)
            if next_offset > start and offset <= end:
                yield chunk[max(0, start - offset) : min(len(chunk), end - offset + 1)]
            offset = next_offset
            if offset > end:
                break
    finally:
        close = getattr(chunks, "close", None)
        if close:
            close()
