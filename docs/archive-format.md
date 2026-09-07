# Archive format v2

An Sessionfold root contains two independent namespaces:

```text
blobs/ab/abcdef...             # full SHA-256 as filename
archives/ARCHIVE_ID/
  manifest.json
  transcript.thin.jsonl.gz
```

The thin stream is the original transcript with eligible inline image data URIs
omitted, then deterministically gzip-compressed. The manifest's `thin.size` is
the uncompressed byte count.

`images.sequence` stores every omitted occurrence in original order:

```json
{
  "offset": 1234,
  "sha256": "...",
  "size": 5678,
  "mime": "image/png"
}
```

`offset` is the number of uncompressed thin-stream bytes that precede the
occurrence. Adjacent images can have the same offset and remain ordered by the
sequence. This avoids embedding replacement tokens that might collide with
arbitrary transcript text.

Verification streams the thin bytes and blobs in sequence into a SHA-256
digest, validates each unique blob, and compares both reconstructed size and
hash with `source`. `verify` discards reconstructed bytes; `restore` writes to a
temporary file, fsyncs it, and atomically renames it without overwriting an
existing target.

`reclaim` first performs that same logical reconstruction, then confirms the
original path is a regular non-symlink file with the recorded size,
modification time, and SHA-256. It also refuses recent or open files. The
manifest records a pending removal marker before unlinking the source so an
interrupted manifest update can be completed safely on the next run.

The `store_root` field is advisory and can be overridden after relocation with
`--store`. Schema v2 is not encrypted and has no garbage collector. Interrupted
archives can leave unreferenced blobs; deleting blobs manually is unsafe.
