---
name: agent-coldstore
description: Audit disk usage from local Codex or Claude Code histories, identify repeated inline image payloads, and create or restore safe deduplicated archives. Use when histories, sessions, rollout JSONL, screenshots, compaction, or agent storage consume excessive disk or cause the app to slow, freeze, or fail.
---

# Agent Coldstore

Use the bundled `bin/agent-coldstore` command to inspect local agent histories.

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

1. Run `bin/agent-coldstore scan` for a fast inventory.
2. Run `bin/agent-coldstore scan --deep --top 20` on the largest files.
3. Explain total use, largest files, duplicate image bytes, and recent/open state.
4. If the user asks to archive, select completed files explicitly and run
   `bin/agent-coldstore archive <file>...` without source removal first.
5. Report the manifest path and verified status.
6. Only after explicit authorization, use `--remove-source` for explicit files.
7. Use `verify` for a disk-light integrity check and `restore` to recover to a
   new path. Never overwrite an existing path.

## Commands

```bash
bin/agent-coldstore scan [PATH ...] [--deep] [--top N] [--json]
bin/agent-coldstore archive FILE ... [--store PATH] [--min-age-minutes N] [--remove-source]
bin/agent-coldstore verify MANIFEST [--store PATH]
bin/agent-coldstore restore MANIFEST --output PATH [--store PATH]
bin/agent-coldstore list [--store PATH] [--json]
```

The default store is `~/.agent-coldstore`. Codex is discovered under
`${CODEX_HOME:-~/.codex}/sessions`; Claude Code under `~/.claude/projects`.
