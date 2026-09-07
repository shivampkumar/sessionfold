#!/usr/bin/env python3
"""Build a minimal deterministic Agent Coldstore plugin ZIP."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUTPUT = DIST / "agent-coldstore-plugin-0.1.0.zip"
INCLUDE = (
    ROOT / ".codex-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "plugin.json",
    ROOT / "agent_coldstore" / "__init__.py",
    ROOT / "agent_coldstore" / "__main__.py",
    ROOT / "agent_coldstore" / "cli.py",
    ROOT / "bin" / "agent-coldstore",
    ROOT / "hooks" / "hooks.json",
    ROOT / "scripts" / "hook_guard.py",
    ROOT / "skills" / "agent-coldstore" / "SKILL.md",
    ROOT / "README.md",
    ROOT / "SECURITY.md",
    ROOT / "PRIVACY.md",
    ROOT / "LICENSE",
)


def main() -> int:
    DIST.mkdir(exist_ok=True)
    with zipfile.ZipFile(
        OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        for source in INCLUDE:
            if not source.is_file():
                raise FileNotFoundError(source)
            archive_name = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(archive_name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (
                (0o755 if source.name == "agent-coldstore" else 0o644) & 0xFFFF
            ) << 16
            bundle.writestr(info, source.read_bytes(), compresslevel=9)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"{OUTPUT}  sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
