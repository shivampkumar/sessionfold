# Show HN human-rewrite outline

Hacker News currently says not to post generated or AI-edited text. Do not paste
this file into HN. Rewrite the facts and story in your own voice, and post only
from an account eligible under the current Show HN restrictions.

**Title:** Show HN: Sessionfold – lossless dedup for huge Codex histories

I found a pathological local Codex history corpus using 565.62 GiB. In its ten
largest JSONL sessions, 98.17% of inline image bytes were duplicate payloads,
mostly repeated through compaction and related histories.

I built Sessionfold, an offline Python CLI that moves large inline images
into a global SHA-256 content-addressed store while retaining a compressed thin
transcript. It never rewrites an active session, deletion is disabled by
default, and every archive is verified by reconstructing the logical original
and matching its complete SHA-256. A separate restore command recreates the
original JSONL byte-for-byte.

On one closed 6.44 GB real session, an empty cold store used 1.047 GB (83.75%
less) and completed archival plus full logical verification in 21.63 seconds at
about 71 MB peak RSS. Across three related sessions, the shared archive was
92.11% smaller than the originals. These are single-machine measurements, not
a claim about typical histories.

It has no telemetry or network client and intentionally does not summarize,
redact, or optimize live context. The narrow goal is recoverable cold storage.
The alpha supports quoted `data:image/*;base64,...` values in Codex and Claude
Code JSONL; vendor formats are unstable, so format drift is an explicit risk.

I would particularly value adversarial feedback about crash consistency,
cross-platform open-file detection, and cases where a transcript restores
correctly but a vendor no longer recognizes it.

GitHub: [ADD RELEASE URL]

PyPI: [ADD PYPI URL]
