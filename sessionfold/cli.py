"""Lossless, local-first cold storage for AI agent session transcripts."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
import stat

# This module invokes only a resolved lsof executable with shell=False.
import subprocess  # nosec B404
import sys
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO

CHUNK_SIZE = 1024 * 1024
DATA_URI_START = b"data:image/"
BASE64_SEPARATOR = b";base64,"
BASE64_BYTES = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n"
MIN_IMAGE_URI_BYTES = 4096
MAX_IMAGE_URI_BYTES = 64 * 1024 * 1024
DEFAULT_STORE = Path.home() / ".sessionfold"


@dataclass(frozen=True)
class SessionPart:
    data: bytes
    is_image: bool = False
    mime: str | None = None


@dataclass
class FileReport:
    path: str
    tool: str
    size: int
    modified_at: str
    recent: bool
    open_by_process: bool | None
    image_occurrences: int | None = None
    image_bytes: int | None = None
    unique_image_bytes: int | None = None
    duplicate_image_bytes: int | None = None
    replacement_history_records: int | None = None
    largest_image_bytes: int | None = None


class StreamingMarkerCounter:
    """Count a byte marker exactly once across arbitrary chunk boundaries."""

    def __init__(self, marker: bytes) -> None:
        self.marker = marker
        self.carry = b""
        self.count = 0

    def update(self, data: bytes, *, final: bool = False) -> None:
        combined = self.carry + data
        safe_end = (
            len(combined) if final else max(0, len(combined) - len(self.marker) + 1)
        )
        cursor = 0
        while True:
            found = combined.find(self.marker, cursor)
            if found < 0 or found >= safe_end:
                break
            self.count += 1
            cursor = found + len(self.marker)
        self.carry = b"" if final else combined[safe_end:]

    def finish(self) -> int:
        self.update(b"", final=True)
        return self.count


class NullWriter:
    """A binary sink used to verify reconstruction without source-size disk."""

    def write(self, data: bytes) -> int:
        return len(data)


def iso_time(timestamp: float) -> str:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat()


def human_bytes(value: int | None) -> str:
    if value is None:
        return "-"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"


def default_roots() -> list[Path]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    candidates = [codex_home / "sessions", Path.home() / ".claude" / "projects"]
    return [path for path in candidates if path.exists()]


def detect_tool(path: Path) -> str:
    text = str(path)
    if "/.codex/" in text or "\\.codex\\" in text:
        return "codex"
    if "/.claude/" in text or "\\.claude\\" in text:
        return "claude-code"
    return "unknown"


def collect_jsonl(paths: Sequence[Path]) -> list[Path]:
    found: dict[str, Path] = {}
    for path in paths:
        expanded = path.expanduser()
        if expanded.is_file() and expanded.suffix == ".jsonl":
            found[str(expanded.resolve())] = expanded.resolve()
            continue
        if not expanded.is_dir():
            continue
        for root, dirs, files in os.walk(expanded, followlinks=False):
            dirs[:] = [name for name in dirs if not Path(root, name).is_symlink()]
            for name in files:
                candidate = Path(root, name)
                if candidate.suffix == ".jsonl" and not candidate.is_symlink():
                    found[str(candidate.resolve())] = candidate.resolve()
    return list(found.values())


def _read_more(source: BinaryIO, buffer: bytearray) -> bool:
    chunk = source.read(CHUNK_SIZE)
    if not chunk:
        return False
    buffer.extend(chunk)
    return True


def iter_session_parts(
    source: BinaryIO,
    *,
    min_image_bytes: int = MIN_IMAGE_URI_BYTES,
    max_image_bytes: int = MAX_IMAGE_URI_BYTES,
) -> Iterator[SessionPart]:
    """Yield normal bytes and bounded inline images without parsing JSON records."""

    buffer = bytearray()
    eof = not _read_more(source, buffer)
    while buffer or not eof:
        start = buffer.find(DATA_URI_START)
        if start < 0:
            if eof:
                if buffer:
                    yield SessionPart(bytes(buffer))
                return
            keep = min(len(buffer), len(DATA_URI_START) - 1)
            emit_end = len(buffer) - keep
            if emit_end:
                yield SessionPart(bytes(buffer[:emit_end]))
                del buffer[:emit_end]
            eof = not _read_more(source, buffer)
            continue

        if start > 0:
            yield SessionPart(bytes(buffer[:start]))
            del buffer[:start]
            continue

        separator = buffer.find(BASE64_SEPARATOR, 0, min(len(buffer), 160))
        while separator < 0 and len(buffer) < 160 and not eof:
            eof = not _read_more(source, buffer)
            separator = buffer.find(BASE64_SEPARATOR, 0, min(len(buffer), 160))
        if separator < 0:
            yield SessionPart(bytes(buffer[:1]))
            del buffer[:1]
            continue

        payload_start = separator + len(BASE64_SEPARATOR)
        end = buffer.find(b'"', payload_start)
        while end < 0 and not eof and len(buffer) <= max_image_bytes:
            eof = not _read_more(source, buffer)
            end = buffer.find(b'"', payload_start)

        if end < 0:
            if len(buffer) > max_image_bytes:
                raise RuntimeError(
                    f"Inline image candidate exceeds safety limit of {max_image_bytes} bytes"
                )
            yield SessionPart(bytes(buffer))
            return
        if end > max_image_bytes:
            raise RuntimeError(
                f"Inline image candidate exceeds safety limit of {max_image_bytes} bytes"
            )

        candidate = bytes(buffer[:end])
        encoded = candidate[payload_start:]
        mime_bytes = candidate[len("data:") : separator]
        valid = (
            len(candidate) >= min_image_bytes
            and bool(encoded)
            and not encoded.translate(None, BASE64_BYTES)
            and mime_bytes.startswith(b"image/")
        )
        if not valid:
            yield SessionPart(bytes(buffer[:1]))
            del buffer[:1]
            continue

        yield SessionPart(
            candidate,
            is_image=True,
            mime=mime_bytes.decode("ascii", errors="replace"),
        )
        del buffer[:end]


def open_by_process(path: Path) -> bool | None:
    executable = shutil.which("lsof")
    if not executable:
        return None
    try:
        # The executable is fixed by shutil.which and the path is one argv item.
        result = subprocess.run(  # nosec B603
            [executable, "-F", "n", "--", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode == 0


def analyze_file(
    path: Path,
    *,
    deep: bool,
    recent_minutes: int,
    check_open: bool = True,
) -> tuple[FileReport, dict[str, int]]:
    info = path.stat()
    age_seconds = max(0.0, dt.datetime.now(dt.timezone.utc).timestamp() - info.st_mtime)
    report = FileReport(
        path=str(path),
        tool=detect_tool(path),
        size=info.st_size,
        modified_at=iso_time(info.st_mtime),
        recent=age_seconds < recent_minutes * 60,
        open_by_process=open_by_process(path) if check_open else None,
    )
    digests: dict[str, int] = {}
    if not deep or info.st_size == 0:
        return report, digests

    total = 0
    largest = 0
    occurrences = 0
    replacement_history = StreamingMarkerCounter(b'"replacement_history"')
    with path.open("rb") as source:
        for part in iter_session_parts(source):
            replacement_history.update(part.data)
            if not part.is_image:
                continue
            occurrences += 1
            total += len(part.data)
            largest = max(largest, len(part.data))
            digest = hashlib.sha256(part.data).hexdigest()
            digests.setdefault(digest, len(part.data))

    unique = sum(digests.values())
    report.image_occurrences = occurrences
    report.image_bytes = total
    report.unique_image_bytes = unique
    report.duplicate_image_bytes = total - unique
    report.largest_image_bytes = largest
    report.replacement_history_records = replacement_history.finish()
    return report, digests


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            os.chmod(temporary, 0o600)
            output.write((json.dumps(payload, indent=2) + "\n").encode())
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_blob(data: bytes, digest: str, store: Path) -> tuple[Path, bool]:
    destination = store / "blobs" / digest[:2] / digest
    if destination.exists():
        if destination.stat().st_size != len(data):
            raise RuntimeError(f"Blob size mismatch for {digest}")
        return destination, False

    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            os.chmod(temporary, 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if hash_file(temporary) != digest:
            raise RuntimeError(f"Blob hash mismatch for {digest}")
        created = True
        try:
            os.link(temporary, destination)
        except FileExistsError:
            created = False
            if destination.stat().st_size != len(data):
                raise RuntimeError(f"Concurrent blob size mismatch for {digest}")
    finally:
        temporary.unlink(missing_ok=True)
    return destination, created


def manifest_path_from_input(path: Path) -> Path:
    expanded = path.expanduser().resolve()
    if expanded.is_dir():
        expanded = expanded / "manifest.json"
    if not expanded.is_file():
        raise FileNotFoundError(f"Archive manifest not found: {expanded}")
    return expanded


def _copy_exact(source: BinaryIO, output: BinaryIO, count: int, digest: object) -> None:
    remaining = count
    while remaining:
        block = source.read(min(CHUNK_SIZE, remaining))
        if not block:
            raise RuntimeError("Thin transcript ended before the next insertion offset")
        output.write(block)
        digest.update(block)
        remaining -= len(block)


def _emit_blob(
    blob: Path,
    output: BinaryIO,
    source_digest: object,
    expected_digest: str,
    expected_size: int,
    verified_blobs: set[str],
) -> None:
    blob_digest = hashlib.sha256() if expected_digest not in verified_blobs else None
    emitted = 0
    with blob.open("rb") as blob_source:
        while block := blob_source.read(CHUNK_SIZE):
            output.write(block)
            source_digest.update(block)
            if blob_digest is not None:
                blob_digest.update(block)
            emitted += len(block)
    if emitted != expected_size:
        raise RuntimeError(f"Blob size mismatch for {expected_digest}")
    if blob_digest is not None:
        actual = blob_digest.hexdigest()
        if actual != expected_digest:
            raise RuntimeError(
                f"Blob hash mismatch: expected {expected_digest}, got {actual}"
            )
        verified_blobs.add(expected_digest)


def _reconstruct(
    manifest_path: Path, output: BinaryIO, *, store: Path | None = None
) -> dict:
    manifest_path = manifest_path_from_input(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 2:
        raise RuntimeError("Unsupported archive schema")
    archive_dir = manifest_path.parent
    archive_store = store or Path(manifest["store_root"])
    thin_name = manifest["thin"]["path"]
    if not isinstance(thin_name, str) or Path(thin_name).name != thin_name:
        raise RuntimeError("Invalid thin transcript path in manifest")
    thin_path = archive_dir / thin_name
    source_digest = hashlib.sha256()
    verified_blobs: set[str] = set()
    source_size = 0
    thin_position = 0

    sequence = manifest["images"]["sequence"]
    previous_offset = 0
    for item in sequence:
        offset = item.get("offset")
        if not isinstance(offset, int) or offset < previous_offset:
            raise RuntimeError("Invalid or non-monotonic image insertion offset")
        previous_offset = offset

    with gzip.open(thin_path, "rb") as thin_source:
        for item in sequence:
            offset = item["offset"]
            _copy_exact(thin_source, output, offset - thin_position, source_digest)
            source_size += offset - thin_position
            thin_position = offset

            digest = item["sha256"]
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise RuntimeError("Invalid blob digest in manifest")
            blob = archive_store / "blobs" / digest[:2] / digest
            if not blob.is_file():
                raise FileNotFoundError(f"Missing archive blob: {blob}")
            size = item["size"]
            if not isinstance(size, int) or size < 0:
                raise RuntimeError("Invalid blob size in manifest")
            _emit_blob(blob, output, source_digest, digest, size, verified_blobs)
            source_size += size

        while block := thin_source.read(CHUNK_SIZE):
            output.write(block)
            source_digest.update(block)
            thin_position += len(block)
            source_size += len(block)

    if thin_position != manifest["thin"]["size"]:
        raise RuntimeError("Thin transcript size mismatch")
    expected_size = manifest["source"]["size"]
    if source_size != expected_size:
        raise RuntimeError(
            f"Restored size mismatch: expected {expected_size}, got {source_size}"
        )
    actual = source_digest.hexdigest()
    expected = manifest["source"]["sha256"]
    if actual != expected:
        raise RuntimeError(f"Restored hash mismatch: expected {expected}, got {actual}")
    return manifest


def verify_archive(manifest_path: Path, *, store: Path | None = None) -> dict:
    """Verify a full byte-exact reconstruction while discarding reconstructed bytes."""

    return _reconstruct(manifest_path, NullWriter(), store=store)


def restore_stream(
    manifest_path: Path, output_path: Path, *, store: Path | None = None
) -> dict:
    output_path = output_path.expanduser().resolve()
    if output_path.exists():
        raise FileExistsError(f"Restore target already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            os.chmod(temporary, 0o600)
            manifest = _reconstruct(manifest_path, output, store=store)
            output.flush()
            os.fsync(output.fileno())
            mode = manifest["source"].get("mode", 0o600)
            if not isinstance(mode, int) or mode < 0 or mode > 0o7777:
                raise RuntimeError("Invalid source mode in manifest")
            os.chmod(temporary, mode)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def archive_file(
    path: Path, store: Path, min_age_minutes: int, remove_source: bool
) -> dict:
    requested_path = path.expanduser()
    if requested_path.is_symlink():
        raise ValueError(
            f"Expected a regular, non-symlink JSONL file: {requested_path}"
        )
    path = requested_path.resolve()
    if not path.is_file() or path.suffix != ".jsonl":
        raise ValueError(f"Expected a regular, non-symlink JSONL file: {path}")
    before = path.stat()
    age_seconds = max(
        0.0, dt.datetime.now(dt.timezone.utc).timestamp() - before.st_mtime
    )
    if age_seconds < min_age_minutes * 60:
        raise RuntimeError(
            f"Refusing recent file {path}; age is {age_seconds / 60:.1f} minutes "
            f"but minimum is {min_age_minutes}."
        )
    opened = open_by_process(path)
    if opened is True:
        raise RuntimeError(f"Refusing file open by another process: {path}")
    if remove_source and opened is None:
        raise RuntimeError(
            "Cannot safely remove source because open-file detection is unavailable"
        )

    store = store.expanduser().resolve()
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_dir = store / ".tmp" / uuid.uuid4().hex
    temporary_dir.mkdir(parents=True)
    thin_path = temporary_dir / "transcript.thin.jsonl.gz"
    source_digest = hashlib.sha256()
    image_sequence: list[dict[str, object]] = []
    image_digests: dict[str, int] = {}
    image_bytes = 0
    new_blob_bytes = 0
    thin_size = 0
    final_dir: Path | None = None
    archive_verified = False

    try:
        with path.open("rb") as source, thin_path.open("wb") as thin_raw:
            os.chmod(thin_path, 0o600)
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=thin_raw, mtime=0
            ) as thin:
                for part in iter_session_parts(source):
                    source_digest.update(part.data)
                    if not part.is_image:
                        thin.write(part.data)
                        thin_size += len(part.data)
                        continue

                    digest = hashlib.sha256(part.data).hexdigest()
                    _, created = write_blob(part.data, digest, store)
                    if created:
                        new_blob_bytes += len(part.data)
                    image_sequence.append(
                        {
                            "offset": thin_size,
                            "sha256": digest,
                            "size": len(part.data),
                            "mime": part.mime,
                        }
                    )
                    image_bytes += len(part.data)
                    image_digests.setdefault(digest, len(part.data))

        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError(f"Source changed while archiving: {path}")

        source_hash = source_digest.hexdigest()
        archive_id = f"{path.stem[:48]}-{source_hash[:12]}-{uuid.uuid4().hex[:6]}"
        final_dir = store / "archives" / archive_id
        manifest = {
            "schema_version": 2,
            "archive_id": archive_id,
            "created_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            "store_root": str(store),
            "source": {
                "path": str(path),
                "tool": detect_tool(path),
                "size": before.st_size,
                "sha256": source_hash,
                "mtime_ns": before.st_mtime_ns,
                "mode": stat.S_IMODE(before.st_mode),
            },
            "thin": {"path": thin_path.name, "size": thin_size},
            "images": {
                "occurrences": len(image_sequence),
                "total_bytes": image_bytes,
                "unique_blobs": len(image_digests),
                "unique_bytes": sum(image_digests.values()),
                "duplicate_bytes": image_bytes - sum(image_digests.values()),
                "new_blob_bytes": new_blob_bytes,
                "sequence": image_sequence,
            },
        }
        manifest_file = temporary_dir / "manifest.json"
        write_json_atomic(manifest_file, manifest)
        verify_archive(manifest_file, store=store)
        manifest["verified"] = True
        manifest["archive_path"] = str(final_dir / "manifest.json")
        manifest["source_removed"] = False
        manifest["source_removal_pending"] = False
        write_json_atomic(manifest_file, manifest)
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary_dir, final_dir)
        archive_verified = True

        if remove_source:
            return reclaim_source(
                final_dir / "manifest.json",
                store=store,
                min_age_minutes=min_age_minutes,
            )
        return manifest
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        if final_dir is not None and not archive_verified:
            shutil.rmtree(final_dir, ignore_errors=True)
        raise


def reclaim_source(
    manifest_path: Path,
    *,
    store: Path | None = None,
    min_age_minutes: int = 60,
) -> dict:
    """Remove one exact archived source after independently re-verifying it."""

    manifest_path = manifest_path_from_input(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("verified") is not True:
        raise RuntimeError("Archive is not marked verified; refusing source removal")

    # Reconstruct and validate the logical source before considering deletion.
    verify_archive(manifest_path, store=store)
    if manifest.get("source_removed") is True:
        return manifest

    source_record = manifest.get("source")
    if not isinstance(source_record, dict):
        raise TypeError("Manifest has no valid source record")
    source_value = source_record.get("path")
    if not isinstance(source_value, str) or not source_value:
        raise RuntimeError("Manifest has no valid source path")
    source = Path(source_value).expanduser()

    # A pending marker is written before unlink. If a process died after unlink,
    # this branch safely finishes the manifest update without guessing.
    if not source.exists():
        if manifest.get("source_removal_pending") is True:
            manifest["source_removal_pending"] = False
            manifest["source_removed"] = True
            manifest["source_removed_at"] = dt.datetime.now(
                tz=dt.timezone.utc
            ).isoformat()
            write_json_atomic(manifest_path, manifest)
            return manifest
        raise FileNotFoundError(f"Archived source is missing: {source}")

    if source.is_symlink() or not source.is_file():
        raise RuntimeError(
            f"Archived source is not a regular non-symlink file: {source}"
        )

    expected = source_record
    before = source.stat()
    expected_identity = (expected.get("size"), expected.get("mtime_ns"))
    if (before.st_size, before.st_mtime_ns) != expected_identity:
        raise RuntimeError("Archived source size or modification time has changed")
    age_seconds = max(
        0.0, dt.datetime.now(dt.timezone.utc).timestamp() - before.st_mtime
    )
    if age_seconds < min_age_minutes * 60:
        raise RuntimeError(
            f"Refusing recent file {source}; age is {age_seconds / 60:.1f} minutes "
            f"but minimum is {min_age_minutes}."
        )
    if open_by_process(source) is not False:
        raise RuntimeError(
            "Cannot safely remove source because it may be open or open-file "
            "detection is unavailable"
        )

    expected_hash = expected.get("sha256")
    if not isinstance(expected_hash, str) or hash_file(source) != expected_hash:
        raise RuntimeError("Archived source SHA-256 has changed")

    after = source.stat()
    if (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ):
        raise RuntimeError("Archived source changed during final verification")
    if open_by_process(source) is not False:
        raise RuntimeError("Archived source became open; refusing removal")

    manifest["source_removal_pending"] = True
    manifest["source_removal_requested_at"] = dt.datetime.now(
        tz=dt.timezone.utc
    ).isoformat()
    write_json_atomic(manifest_path, manifest)
    try:
        final = source.stat()
        if (
            final.st_dev,
            final.st_ino,
            final.st_size,
            final.st_mtime_ns,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ):
            raise RuntimeError("Archived source changed before removal")
        source.unlink()
    except Exception:
        manifest["source_removal_pending"] = False
        write_json_atomic(manifest_path, manifest)
        raise

    manifest["source_removal_pending"] = False
    manifest["source_removed"] = True
    manifest["source_removed_at"] = dt.datetime.now(tz=dt.timezone.utc).isoformat()
    write_json_atomic(manifest_path, manifest)
    return manifest


def command_scan(args: argparse.Namespace) -> int:
    roots = [Path(value) for value in args.paths] if args.paths else default_roots()
    files = collect_jsonl(roots)
    metadata = sorted(((path.stat().st_size, path) for path in files), reverse=True)
    selected = {path for _, path in metadata[: args.top]} if args.deep else set()
    displayed = {path for _, path in metadata[: args.top]}
    reports: list[FileReport] = []
    global_digests: dict[str, int] = {}
    deep_image_bytes = 0

    for _, path in metadata:
        report, digests = analyze_file(
            path,
            deep=path in selected,
            recent_minutes=args.recent_minutes,
            check_open=path in displayed,
        )
        reports.append(report)
        if report.image_bytes is not None:
            deep_image_bytes += report.image_bytes
        for digest, size in digests.items():
            global_digests.setdefault(digest, size)

    payload = {
        "roots": [str(path.expanduser()) for path in roots],
        "file_count": len(reports),
        "total_bytes": sum(report.size for report in reports),
        "recent_files": sum(report.recent for report in reports),
        "open_files": sum(report.open_by_process is True for report in reports),
        "deep_analyzed_files": len(selected),
        "deep_image_bytes": deep_image_bytes if args.deep else None,
        "deep_unique_image_bytes_across_files": sum(global_digests.values())
        if args.deep
        else None,
        "deep_duplicate_image_bytes_across_files": (
            deep_image_bytes - sum(global_digests.values()) if args.deep else None
        ),
        "files": [asdict(report) for report in reports[: args.top]],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Session files: {payload['file_count']}")
    print(f"Total size:    {human_bytes(payload['total_bytes'])}")
    print(f"Recent/open:   {payload['recent_files']} / {payload['open_files']}")
    if args.deep:
        print(f"Deep scanned:  {payload['deep_analyzed_files']} largest files")
        print(f"Inline images: {human_bytes(payload['deep_image_bytes'])}")
        print(
            f"Duplicate:     {human_bytes(payload['deep_duplicate_image_bytes_across_files'])}"
        )
    print("\nLargest files:")
    for report in reports[: args.top]:
        flags = []
        if report.recent:
            flags.append("recent")
        if report.open_by_process:
            flags.append("open")
        suffix = f" ({', '.join(flags)})" if flags else ""
        detail = ""
        if report.image_bytes is not None:
            detail = (
                f" | images {human_bytes(report.image_bytes)}, "
                f"duplicate {human_bytes(report.duplicate_image_bytes)}"
            )
        print(f"  {human_bytes(report.size):>10}  {report.path}{suffix}{detail}")
    return 0


def command_archive(args: argparse.Namespace) -> int:
    store = Path(args.store)
    manifests = []
    for value in args.files:
        manifest = archive_file(
            Path(value),
            store,
            min_age_minutes=args.min_age_minutes,
            remove_source=args.remove_source,
        )
        manifests.append(manifest)
        if not args.json:
            print(f"Verified archive: {manifest['archive_path']}")
            print(
                "  images: "
                f"{manifest['images']['occurrences']} occurrences, "
                f"{human_bytes(manifest['images']['duplicate_bytes'])} duplicate"
            )
            print(f"  source removed: {manifest.get('source_removed', False)}")
    if args.json:
        print(json.dumps(manifests, indent=2))
    return 0


def command_restore(args: argparse.Namespace) -> int:
    store = Path(args.store) if args.store else None
    manifest = restore_stream(Path(args.manifest), Path(args.output), store=store)
    print(f"Restored and verified: {Path(args.output).expanduser().resolve()}")
    print(f"Source SHA-256: {manifest['source']['sha256']}")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    store = Path(args.store) if args.store else None
    manifest = verify_archive(Path(args.manifest), store=store)
    print(f"Archive is byte-exact: {manifest_path_from_input(Path(args.manifest))}")
    print(f"Source SHA-256: {manifest['source']['sha256']}")
    return 0


def command_reclaim(args: argparse.Namespace) -> int:
    if not args.yes:
        raise RuntimeError(
            "Reclaim requires --yes after you review the exact manifest and source path"
        )
    store = Path(args.store) if args.store else None
    manifest = reclaim_source(
        Path(args.manifest),
        store=store,
        min_age_minutes=args.min_age_minutes,
    )
    print(f"Removed archived source: {manifest['source']['path']}")
    print(f"Verified archive remains: {manifest_path_from_input(Path(args.manifest))}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    store = Path(args.store).expanduser().resolve()
    manifests = []
    for manifest_path in sorted((store / "archives").glob("*/manifest.json")):
        try:
            payload = json.loads(manifest_path.read_text())
            payload["manifest_path"] = str(manifest_path)
            manifests.append(payload)
        except (OSError, json.JSONDecodeError):
            continue
    if args.json:
        print(json.dumps(manifests, indent=2))
        return 0
    print(f"Archives: {len(manifests)}")
    for payload in manifests:
        print(
            f"  {payload['archive_id']} | {human_bytes(payload['source']['size'])} | "
            f"{payload['source']['path']}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sessionfold",
        description="Audit and losslessly archive local AI agent session histories.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser(
        "scan", aliases=["doctor"], help="Read-only session inventory"
    )
    scan.add_argument(
        "paths", nargs="*", help="Files or roots; defaults to Codex and Claude roots"
    )
    scan.add_argument(
        "--deep", action="store_true", help="Hash inline images in the largest files"
    )
    scan.add_argument(
        "--top", type=int, default=20, help="Largest files to report/deep-scan"
    )
    scan.add_argument("--recent-minutes", type=int, default=30)
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(func=command_scan)

    archive = subparsers.add_parser(
        "archive", help="Create verified deduplicated archives"
    )
    archive.add_argument("files", nargs="+", help="Explicit completed JSONL files")
    archive.add_argument("--store", default=str(DEFAULT_STORE))
    archive.add_argument("--min-age-minutes", type=int, default=60)
    archive.add_argument("--remove-source", action="store_true")
    archive.add_argument("--json", action="store_true")
    archive.set_defaults(func=command_archive)

    restore = subparsers.add_parser("restore", help="Restore one archive byte-for-byte")
    restore.add_argument("manifest")
    restore.add_argument("--output", required=True)
    restore.add_argument(
        "--store", help="Override the blob store recorded in the manifest"
    )
    restore.set_defaults(func=command_restore)

    verify = subparsers.add_parser(
        "verify",
        help="Verify byte-exact reconstruction without writing the restored file",
    )
    verify.add_argument("manifest")
    verify.add_argument(
        "--store", help="Override the blob store recorded in the manifest"
    )
    verify.set_defaults(func=command_verify)

    reclaim = subparsers.add_parser(
        "reclaim",
        help="Re-verify one archive, then remove its exact original source",
    )
    reclaim.add_argument("manifest")
    reclaim.add_argument(
        "--store", help="Override the blob store recorded in the manifest"
    )
    reclaim.add_argument("--min-age-minutes", type=int, default=60)
    reclaim.add_argument(
        "--yes",
        action="store_true",
        help="Confirm removal of the exact source path recorded in the manifest",
    )
    reclaim.set_defaults(func=command_reclaim)

    listing = subparsers.add_parser("list", help="List local archives")
    listing.add_argument("--store", default=str(DEFAULT_STORE))
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=command_list)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "top", 1) < 1:
        parser.error("--top must be positive")
    try:
        return int(args.func(args))
    except (
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        print(f"sessionfold: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
