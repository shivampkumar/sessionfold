# Changelog

## 0.1.0a6 : 2026-09-07

- Resolve picker titles by joining Codex's rollout index with its local thread
  catalog, fixing missing titles on builds that do not populate `threads.name`.
- Add a conservative archive headroom check and `--keep-free SIZE`, defaulting
  to a 1 GiB reserve in the CLI.
- Print immediate discovery and inspection progress during human-readable scans.
- Mark listed archives as `available` or `cold` based on source presence.
- Add `restore --original` so a cold session can be restored to its recorded
  Codex path by archive ID or exact unique title.

## 0.1.0a5 : 2026-09-07

- Show Codex task names in scan and archive listings through a read-only,
  best-effort lookup of the local Codex state index.
- Record available task names and thread IDs in new archive manifests.
- Add archive search and accept a manifest path, archive ID, or exact unique
  title for verify, reclaim, and restore.
- Add `--no-titles` to suppress task-name lookup and display.
- Add explicit titles with `archive --title` and relabel existing archives with
  `sessionfold label`.

## 0.1.0a4 : 2026-09-07

- State prominently that the current alpha supports Codex only.
- Remove Claude Code from automatic discovery and the plugin bundle because its
  usual base64 image-block representation is not yet supported.
- Keep explicit-path archival generic, but do not claim compatibility with
  unvalidated transcript formats.

## 0.1.0a3 : 2026-09-07

- Put the cold-storage and Codex usability contract at the top of the README.
- Clarify that archiving alone leaves chats usable but does not reclaim their
  original bytes.
- Clarify that reclaiming an original can hide the chat from Codex and that
  automatic Codex UI reintegration after restore is not yet validated.

## 0.1.0a2 : 2026-09-06

- Route one-command source removal through the same second reconstruction,
  source-hash check, open-file check, and removal journal as `reclaim`.
- Clarify that Codex is the validated alpha target and Claude Code support is
  experimental.
- Document first-archive headroom and external-store requirements.
- Add randomized parser, no-image archive, interrupted restore, and interrupted
  source-removal recovery tests.

## 0.1.0a1 : 2026-09-06

- Add read-only Codex and Claude Code JSONL inventory.
- Add bounded streaming detection of large inline image data URIs.
- Add global SHA-256 content-addressed archive storage.
- Add byte-exact logical verification without a source-size temporary copy.
- Add physical restore with source-size and SHA-256 validation.
- Add a separate, explicitly confirmed reclaim step for reviewed archives.
- Refuse active, recent, symlinked, mutated, corrupt, or ambiguous deletion cases.
- Add optional Codex and Claude Code warning plugins.
