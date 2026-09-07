# Sessionfold 0.1.0a1

Sessionfold helps recover disk space from large Codex and Claude Code history
files. It finds repeated inline screenshots, stores each unique image once, and
keeps enough information to restore the original JSONL file byte for byte.

This first alpha includes:

- read-only scanning and duplicate estimates;
- streaming archives with a shared SHA-256 content store;
- verification without creating a source-sized temporary file;
- byte-exact restore to a new path;
- an explicitly confirmed reclaim command that rechecks the archive and source;
- optional Codex and Claude Code plugin bundles.

The tool has no telemetry or network client. Source removal is off by default.
This is an alpha because agent transcript formats can change and independent
user testing has not started yet.
