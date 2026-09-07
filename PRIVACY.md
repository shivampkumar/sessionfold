# Privacy

Sessionfold is offline software. It has no telemetry, analytics, crash
reporting, update checker, or network client. It reads local transcript bytes
only to count, hash, archive, verify, or restore them as explicitly requested.

Human-readable output contains paths, sizes, timestamps, counts, hashes,
status, and Codex's generated task names. Title lookup reads only Codex's local
rollout index and picker catalog and can be disabled with `--no-titles` on
`scan` and `list`.
Sessionfold does not intentionally print prompts, messages, images, or tool
output. Archive blobs, manifests, and thin transcripts remain sensitive because
they can be combined to reconstruct or identify the original session. Protect
the archive store as you would the original histories.
