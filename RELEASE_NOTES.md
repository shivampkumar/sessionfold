# Sessionfold 0.1.0a3

This started when my 20-day-old 1 TB Mac reached 80 MB of free space. I blamed
the healthcare datasets I was working with, but the real culprit was about 566
GiB of Codex session JSONL. My honest reaction was, "what the shit?" Many of
those files contained the same screenshots repeated through compaction and
related sessions.

Sessionfold helps recover disk space from large Codex history files. It finds
repeated inline screenshots, stores each unique image once, and keeps enough
information to restore the original JSONL file byte for byte. Claude Code
discovery is included for experimentation, but it is not a validated launch
claim yet.

This alpha includes:

- read-only scanning and duplicate estimates;
- streaming archives with a shared SHA-256 content store;
- verification without creating a source-sized temporary file;
- byte-exact restore to a new path;
- an explicitly confirmed reclaim command that rechecks the archive and source;
- optional Codex and Claude Code plugin bundles.

The tool has no telemetry or network client. Source removal is off by default.
This is an alpha because agent transcript formats can change and independent
user testing has not started yet.

The first archive needs additional free space. If a drive is already critically
full, put the archive on an external volume with `--store`. Codex is the
validated target. Claude Code support is experimental in this alpha.

Version 0.1.0a3 makes the cold-storage contract prominent: `archive` leaves the
original and its Codex usability unchanged, while `reclaim` recovers space by
removing the original JSONL. A reclaimed chat may disappear from Codex.
Sessionfold guarantees byte-exact file restoration, but automatic reintegration
into the Codex sidebar is not yet validated.
