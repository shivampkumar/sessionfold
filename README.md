# Sessionfold

Sessionfold is a local-first disk safety tool for Codex and Claude Code
histories. It finds oversized JSONL sessions and creates lossless,
content-addressed archives in which identical inline images are stored once
across every archived session.

It does not upload telemetry or session data, display conversation content, or
modify an active transcript. Scanning is read-only. Source removal is optional
and occurs only after a full byte-exact reconstruction has been verified.

## Why it exists

Screenshot-heavy agent sessions can embed base64 images directly in JSONL.
Compaction and forks may repeat the same image thousands of times. Ordinary
gzip cannot efficiently deduplicate copies that are far apart or in different
files.

Sessionfold provides five operations:

- `scan` inventories histories; `--deep` hashes inline images and estimates
  duplicate bytes without decoding or displaying them.
- `archive` writes non-image transcript bytes to a compressed thin stream and
  stores images in a global SHA-256 content-addressed store.
- `verify` reconstructs and hashes the full logical transcript without writing
  a source-size temporary file.
- `reclaim` verifies the archive and original again, then removes only the exact
  source named in the manifest after explicit confirmation.
- `restore` recreates the original JSONL byte-for-byte at a new path.

## Install the alpha

Requires Python 3.10 or newer and has no runtime Python dependencies.

```bash
python3 -m pip install https://github.com/shivampkumar/sessionfold/releases/download/v0.1.0a1/sessionfold-0.1.0a1-py3-none-any.whl
sessionfold scan
```

To install from a checkout:

```bash
python3 -m pip install .
./bin/sessionfold scan
```

## Usage

```bash
sessionfold scan
sessionfold scan --deep --top 20
sessionfold archive /path/to/completed.jsonl
sessionfold list
sessionfold verify ~/.sessionfold/archives/ARCHIVE/manifest.json
sessionfold reclaim ~/.sessionfold/archives/ARCHIVE/manifest.json --yes
sessionfold restore ~/.sessionfold/archives/ARCHIVE/manifest.json --output ./restored.jsonl
```

The recommended workflow separates review from removal:

```bash
sessionfold archive /path/to/completed.jsonl
sessionfold verify ~/.sessionfold/archives/ARCHIVE/manifest.json
sessionfold reclaim ~/.sessionfold/archives/ARCHIVE/manifest.json --yes
```

For a one-command archive and removal:

```bash
sessionfold archive /path/to/completed.jsonl --remove-source
```

Both removal paths refuse recent files, files open by another process, changed
sources, and platforms where open-file detection is unavailable. `reclaim`
also reconstructs the archive again before hashing and removing the source.
Removing a vendor transcript may hide that session from the product UI until
it is restored.

## Defaults and scope

- Codex discovery: `${CODEX_HOME:-~/.codex}/sessions`
- Claude Code discovery: `~/.claude/projects`
- Archive store: `~/.sessionfold`
- Inline image candidates: 4 KiB to 64 MiB each

The initial archive format targets JSONL transcripts containing quoted
`data:image/*;base64,...` values. Unknown or small data URIs remain inline.
Transcript formats are vendor-owned and unstable, so compatibility must be
tested as they evolve. Sessionfold is archival storage; Codex and Claude
Code do not read its archive format directly.

If an archive store is relocated, pass its new root with `--store` to `verify`
or `restore`.

## Safety and privacy

- no network access or telemetry;
- no prompt, image, or tool-output display;
- no implicit deletion or whole-root mutation;
- no edits to vendor databases or active transcripts;
- atomic archive directories and immutable, content-addressed blobs;
- source-size and SHA-256 validation of every logical reconstruction;
- blob size and SHA-256 checks before a restore is accepted;
- existing restore targets are never overwritten.

See [SECURITY.md](SECURITY.md) and [PRIVACY.md](PRIVACY.md).

## Optional plugins

The repository includes Codex and Claude Code plugin manifests plus a shared
skill and warning hook. The hook only stats the current transcript and emits a
warning above a configurable threshold; it never archives or deletes.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile sessionfold/cli.py scripts/hook_guard.py
python3 -m build
```

The feasibility measurements in `experiments/` are single-machine benchmarks,
not promises about every corpus.

See the [archive format](docs/archive-format.md),
[validation record](docs/validation.md), and
[competitive boundary](docs/competitive-landscape.md) for the current contract.
