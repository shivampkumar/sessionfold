# Sessionfold 0.1.0a6

This started when my 20-day-old 1 TB Mac reached 80 MB of free space. I blamed
the healthcare datasets I was working with, but the real culprit was about 566
GiB of Codex session JSONL. My honest reaction was, "what the shit?" Many of
those files contained the same screenshots repeated through compaction and
related sessions.

Sessionfold helps recover disk space from large Codex history files. It finds
repeated inline screenshots, stores each unique image once, and keeps enough
information to restore the original JSONL file byte for byte. The current alpha
supports Codex only. Claude Code commonly uses a different image-block
representation that this release does not deduplicate.

This alpha includes:

- read-only scanning and duplicate estimates;
- streaming archives with a shared SHA-256 content store;
- verification without creating a source-sized temporary file;
- byte-exact restore to a new path;
- an explicitly confirmed reclaim command that rechecks the archive and source;
- an optional Codex plugin bundle.

The tool has no telemetry or network client. Source removal is off by default.
This is an alpha because agent transcript formats can change and independent
user testing has not started yet.

The first archive needs additional free space. If a drive is already critically
full, put the archive on an external volume with `--store`. Codex is the only
supported target in this alpha. Do not reclaim Claude Code histories with this
release.

Version 0.1.0a4 made the cold-storage contract prominent: `archive` leaves the
original and its Codex usability unchanged, while `reclaim` recovers space by
removing the original JSONL. A reclaimed chat may disappear from Codex.
Sessionfold guarantees byte-exact file restoration, but automatic reintegration
into the Codex sidebar is not yet validated.

Version 0.1.0a5 makes archives recognizable. Scans and listings show Codex task
names when the local state index provides them, new manifests retain those
names, and archives can be searched or addressed by ID or exact unique title.
The lookup is local, read-only, and optional. It does not read conversation
bodies to invent missing titles. Untitled archives can be named explicitly at
archive time or relabeled later.

Version 0.1.0a6 incorporates feedback from a rescue run on a completely full
926 GiB volume. It fixes picker-title lookup for Codex builds that keep display
titles in a separate catalog, adds a conservative free-space preflight with a
configurable reserve, prints scan progress immediately, marks archives as cold
or available, and can restore a cold session directly to its original Codex
path by title. It does not truncate source files incrementally or edit Codex's
private databases.
