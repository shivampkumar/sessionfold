#!/usr/bin/env python3
"""Constant-time transcript size warning for Codex and Claude Code hooks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0

    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript:
        return 0

    try:
        size = Path(transcript).stat().st_size
        threshold_gib = float(os.environ.get("AGENT_COLDSTORE_WARN_GIB", "2"))
    except (OSError, ValueError):
        return 0

    threshold = int(threshold_gib * 1024**3)
    if size < threshold:
        return 0

    size_gib = size / 1024**3
    warning = (
        f"Agent Coldstore: this local transcript is {size_gib:.1f} GiB. "
        "Run `agent-coldstore scan --deep` before disk pressure becomes critical. "
        "Do not manually rewrite an active transcript."
    )
    json.dump({"systemMessage": warning}, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
