#!/usr/bin/env python3
"""Copy local ciphertext from an ephemeral path to a workspace path with checksums.

Run while the integration API and workers are stopped. Never removes source bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    env_file, target = args.env_file.resolve(), args.target.resolve()
    if not env_file.is_relative_to(ROOT) or not target.is_relative_to(ROOT):
        raise RuntimeError("Source configuration and target must remain in integration workspace")
    config = dotenv_values(env_file)
    source = Path(str(config["RS_EVIDENCE_DIR"])).resolve()
    if not source.is_dir() or source == target or target.is_symlink():
        raise RuntimeError("Invalid evidence source or target")
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("Target must be empty; refusing to merge ciphertext trees")
    os.umask(0o077)
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    hashes = {}
    for path in source.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("Symlink in ciphertext tree; manual preservation required")
        if path.is_file():
            relative = path.relative_to(source)
            copied = target / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copied)
            if digest(path) != digest(copied):
                raise RuntimeError("Ciphertext checksum mismatch; old configuration retained")
            hashes[str(relative)] = digest(path)
    # Update only the storage setting, preserve every other secret and its file mode.
    raw = env_file.read_text()
    lines = raw.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.startswith("RS_EVIDENCE_DIR=")]
    if len(matches) != 1:
        raise RuntimeError("Expected one RS_EVIDENCE_DIR setting")
    lines[matches[0]] = f"RS_EVIDENCE_DIR={target}\n"
    temporary = env_file.with_name(env_file.name + ".relocating")
    temporary.write_text("".join(lines))
    temporary.chmod(env_file.stat().st_mode & 0o777)
    temporary.replace(env_file)
    manifest = ROOT / "backend/.integration-runtime/evidence-relocation-sha256"
    manifest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest.write_text("\n".join(f"{value}  {name}" for name, value in sorted(hashes.items())) + "\n")
    print(f"Copied and verified {len(hashes)} ciphertext files; previous source retained")


if __name__ == "__main__":
    main()
