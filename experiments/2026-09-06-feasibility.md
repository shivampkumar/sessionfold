# Sessionfold feasibility benchmark : 2026-09-06

## Decision

Proceed with a Codex-first, standalone lossless archive core and keep the
plugin as an optional warning/discovery adapter. Do not position this as a
generic session viewer, context pruner, or Claude Code optimizer.

The differentiated capability is global, content-addressed deduplication of
completed session payloads with byte-exact restoration. It must never rewrite
an active vendor transcript or claim that a vendor can read an archive format
it does not support.

## Real-data observations

- Codex root: 209 JSONL files, 565.62 GiB.
- 100 largest Codex files: 554.32 GiB.
- Claude Code root: 245 JSONL files, 134.44 MiB.
- The 20 largest Claude Code files contained no inline `data:image` payloads.
- The 10 largest Codex files contained 58,531,208,039 bytes of inline image
  payloads but only 1,072,793,468 bytes of globally unique payload content.
  Therefore 98.17% of those image bytes were duplicates across occurrences.

## Lossless archive experiment

Three closed Codex transcripts were archived into one shared store. Every
archive was restored internally and verified against the full source SHA-256.
The original source files were not changed or removed.

| Metric | Value |
| --- | ---: |
| Original bytes, three transcripts | 19,379,673,605 |
| Shared archive bytes | 1,528,157,524 |
| Bytes avoided | 17,851,516,081 |
| Reduction | 92.11% |
| New blob bytes introduced by transcript 1 | 809,509,455 |
| New blob bytes introduced by transcript 2 | 541,825 |
| New blob bytes introduced by transcript 3 | 59,138 |
| Thin transcript sizes | 238–240 MB each |

The second and third sessions contributed almost no new image content, which
validates the value of deduplicating across sessions rather than only within
each JSONL file.

## Compression control

The same 6,496,083,517-byte source used for the first archive was compressed
with ordinary `gzip -6`.

| Method | Stored bytes | Reduction | Wall time |
| --- | ---: | ---: | ---: |
| Plain gzip | 4,177,965,899 | 35.68% | 122.43 s |
| Shared archive, first file | about 1,047,982,148 | 83.87% | about 20 s |

Plain compression is not an adequate substitute. Compressed image payloads are
repeated too far apart for gzip's local dictionary to exploit the global
duplication.

## Streaming v2 validation

The hardened v2 implementation replaced memory mapping with a bounded stream,
uses collision-proof ordered offsets, validates blobs and the reconstructed
source hash, and verifies without materializing a source-size temporary file.
One closed real Codex transcript was archived again from an empty store; the
source was not changed or removed.

| Metric | Value |
| --- | ---: |
| Source bytes | 6,440,831,294 |
| Archive file bytes | 1,046,558,275 |
| Reduction | 83.7512% |
| Image occurrences | 9,957 |
| Unique image blobs | 2,233 |
| Duplicate image bytes | 4,996,363,463 |
| End-to-end archive + logical restore verification | 21.63 s |
| Maximum resident set | 70,893,568 bytes |

An independent `verify` invocation reconstructed and matched the full source
SHA-256 while discarding the reconstructed bytes. Unit tests also exercise a
physical restore and assert byte-for-byte equality.

## Competitive boundary

- Cross-Code Organizer and Cozempic prune or redact live context and focus on
  usability/token reduction.
- Codex Session Cleanup removes later duplicate image occurrences while
  retaining one copy in the live JSONL.
- Codex Session JSON I/O Guard externalizes images but rewrites the live file,
  stores the original as a full backup, and does not provide a byte-exact
  content-addressed archive/rehydration contract.

The project is only worth continuing if it preserves the stricter boundary:
lossless archive storage, global savings, explicit restoration, and no implicit
mutation. A viewer, summarizer, or another in-place trimmer would not be novel.

## Required engineering gates

1. ~~Replace the experimental memory-mapped parser with a bounded streaming
   parser.~~ Completed in schema v2.
2. ~~Make archive references collision-proof for arbitrary transcript text.~~
   Completed with ordered insertion offsets.
3. Continue fault-injection coverage beyond corrupt blobs, source mutation,
   verification interruption, path traversal, and existing restore targets.
4. Test multiple Codex format fixtures and treat format compatibility as an
   adapter contract.
5. Keep deletion disabled by default and require successful independent restore
   verification before any source-removal option is offered.
6. Ship Codex first. Add Claude mutation/archive support only when a measured
   Claude-specific storage problem justifies it.
