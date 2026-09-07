# Competitive boundary

The project is intentionally narrower than context-management tools.

- [Cross-Code Organizer](https://github.com/mcpware/cross-code-organizer) and
  [Cozempic](https://github.com/Ruya-AI/cozempic) focus on pruning, organizing,
  or reducing active context.
- [Codex Session Cleanup](https://github.com/Liu-Bot24/codex-session-handoff-skill)
  removes duplicate image occurrences from live history.
- [Codex JSON I/O Guard](https://github.com/Howard0401/codex-session-json-io-guard)
  externalizes image data while rewriting live JSONL.

Sessionfold's distinct contract is global content-addressed cold storage for
completed histories with a byte-exact restore path, no live-transcript rewrite,
and deletion disabled by default. If the project drifts into a generic viewer,
summarizer, or in-place context trimmer, that differentiation disappears.
