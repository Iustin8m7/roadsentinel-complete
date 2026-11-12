"""Offline verifier for RoadSentinel evidence packages (standard library only: no database,
no keys, no network). Usable as ``python -m app.cli verify-package <zip>`` or by copying this
single file next to the package.

What it proves: every file listed in ``manifest.json`` is present with exactly the recorded
size and SHA-256, nothing else was added, and the manifest bytes are canonical. If you pass the
manifest digest shown by the server (and recorded in the audit log entry ``export.generated``),
it also proves the manifest itself is the one the server produced. Without that external digest
an attacker who rewrites both files and manifest would not be detected: the package is
unsigned, and same-host records are not independent legal custody.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

SCHEMA = "roadsentinel.evidence-package"
SCHEMA_VERSION = 1
FIXED_ENTRIES = {"manifest.json", "VERIFY.txt"}
CHUNK = 1024 * 1024
MAX_MANIFEST = 8 * 1024 * 1024


def canonical_json(doc: object) -> bytes:
    """The one serialization used for manifests: sorted keys, no whitespace, UTF-8."""
    return (
        json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()


@dataclass
class Report:
    ok: bool = True
    manifest_sha256: str | None = None
    files_checked: int = 0
    errors: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _safe(name: str) -> bool:
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts and "\\" not in name


def verify_package(
    path: str | Path,
    expected_manifest_sha256: str | None = None,
    *,
    max_uncompressed: int | None = None,
    max_entries: int = 10_000,
) -> Report:
    """``max_uncompressed`` bounds the work on untrusted uploads: the declared uncompressed
    sizes (which zipfile enforces while reading) must not exceed it."""
    report = Report()
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        report.fail(f"not a readable zip file: {exc.__class__.__name__}")
        return report
    with zf:
        infos = zf.infolist()
        if len(infos) > max_entries:
            report.fail("too many entries")
            return report
        if max_uncompressed is not None and (
            sum(i.file_size for i in infos) > max_uncompressed
            or any(i.filename == "manifest.json" and i.file_size > MAX_MANIFEST for i in infos)
        ):
            report.fail("declared uncompressed size exceeds the verification limit")
            return report
        try:
            _check_entries(zf, infos, report, expected_manifest_sha256)
        except (
            zipfile.BadZipFile,
            zlib.error,
            EOFError,
            OSError,
            NotImplementedError,
            RuntimeError,
        ) as exc:
            # Corrupt data, bad CRC, unsupported compression or an encrypted entry.
            report.fail(f"unreadable zip content: {exc.__class__.__name__}")
    return report


def _check_entries(
    zf: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    report: Report,
    expected_manifest_sha256: str | None,
) -> None:
    names = [i.filename for i in infos if not i.is_dir()]
    if len(names) != len(set(names)):
        report.fail("duplicate entry names")
    for name in names:
        if not _safe(name):
            report.fail(f"unsafe entry name: {name!r}")
    if "manifest.json" not in names:
        report.fail("manifest.json missing")
        return
    raw = zf.read("manifest.json")
    report.manifest_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 and report.manifest_sha256 != expected_manifest_sha256.lower():
        report.fail("manifest digest differs from the expected (server/audit) digest")
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        report.fail("manifest.json is not valid JSON")
        return
    if not isinstance(manifest, dict):
        report.fail("manifest.json is not an object")
        return
    if canonical_json(manifest) != raw:
        report.fail("manifest.json is not in canonical form")
    if manifest.get("schema") != SCHEMA or manifest.get("schema_version") != SCHEMA_VERSION:
        report.fail("unknown manifest schema")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        report.fail("manifest lists no files")
        return
    listed: set[str] = set()
    for entry in files:
        entry_name = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(entry_name, str) or not _safe(entry_name):
            report.fail("manifest has an invalid file path")
            continue
        if entry_name in listed:  # reading a file once per repeated row would be unbounded work
            report.fail(f"file listed more than once: {entry_name}")
            continue
        listed.add(entry_name)
        if entry_name not in names:
            report.fail(f"listed file missing: {entry_name}")
            continue
        digest, size = hashlib.sha256(), 0
        with zf.open(entry_name) as fh:
            while chunk := fh.read(CHUNK):
                digest.update(chunk)
                size += len(chunk)
        if size != entry.get("size_bytes"):
            report.fail(f"size mismatch: {entry_name}")
        if digest.hexdigest() != entry.get("sha256"):
            report.fail(f"sha256 mismatch: {entry_name}")
        report.files_checked += 1
    for extra in sorted(set(names) - listed - FIXED_ENTRIES):
        report.fail(f"file not listed in manifest: {extra}")
