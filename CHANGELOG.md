# Changelog

## 0.1.0 : unreleased

- Add read-only Codex and Claude Code JSONL inventory.
- Add bounded streaming detection of large inline image data URIs.
- Add global SHA-256 content-addressed archive storage.
- Add byte-exact logical verification without a source-size temporary copy.
- Add physical restore with source-size and SHA-256 validation.
- Add a separate, explicitly confirmed reclaim step for reviewed archives.
- Refuse active, recent, symlinked, mutated, corrupt, or ambiguous deletion cases.
- Add optional Codex and Claude Code warning plugins.
