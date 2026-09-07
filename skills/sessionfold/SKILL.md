---
name: sessionfold
description: Audit disk usage from local Codex histories, identify repeated inline image payloads, and create or restore safe deduplicated archives. Use when Codex histories, sessions, rollout JSONL, screenshots, compaction, or agent storage consume excessive disk or cause the app to slow, freeze, or fail.
---

# Sessionfold

Use the bundled `bin/sessionfold` command to inspect local agent histories.

## Safety requirements

- Start with `scan`; it is read-only.
- Never print, decode, display, or upload session payloads. Report sizes, counts,
  timestamps, and hashes only.
- Treat transcript schemas as unstable. Do not manually rewrite JSONL or agent
  index databases.
- Do not archive or remove a file that is open by another process.
- Do not use `--remove-source` unless the user explicitly asks to reclaim disk
  and understands that archived sessions may disappear from product UI.
- Never remove a source unless the archive's byte-exact verification passes.
- Use explicit file paths for mutations. Never mutate an entire home directory
  or session root in one command.

## Workflow

1. Run `bin/sessionfold scan` for a fast inventory.
2. Run `bin/sessionfold scan --deep --top 20` on the largest files.
3. Explain total use, largest files, duplicate image bytes, and recent/open state.
4. If the user asks to archive, select completed files explicitly and run
   `bin/sessionfold archive <file>...` without source removal first.
5. Report the Codex task name when available, the manifest path, and verified
   status. Title lookup is read-only and must never be substituted with parsing
   transcript content. If no name is available, offer `archive --title` or
   `label` instead of inventing one from transcript content.
6. Only after explicit authorization, use `reclaim MANIFEST --yes` so the
   already-reviewed archive and exact source are verified again before removal.
7. Use `verify` for a disk-light integrity check and `restore` to recover to a
   new path. Never overwrite an existing path.

## Commands

```bash
bin/sessionfold scan [PATH ...] [--deep] [--top N] [--no-titles] [--json]
bin/sessionfold archive FILE ... [--title TEXT] [--store PATH] [--min-age-minutes N] [--remove-source]
bin/sessionfold verify MANIFEST [--store PATH]
bin/sessionfold reclaim MANIFEST --yes [--store PATH] [--min-age-minutes N]
bin/sessionfold restore MANIFEST --output PATH [--store PATH]
bin/sessionfold label MANIFEST --title TEXT [--store PATH]
bin/sessionfold list [--store PATH] [--search TEXT] [--no-titles] [--json]
```

The default store is `~/.sessionfold`. Codex is discovered under
`${CODEX_HOME:-~/.codex}/sessions`. The current alpha does not support Claude
Code. Do not reclaim Claude Code histories with it.
