# Changelog

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
