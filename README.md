# Sessionfold

Sessionfold is a local-first disk safety tool for Codex histories. It finds
oversized JSONL sessions and creates lossless, content-addressed archives in
which identical inline images are stored once across every archived session.
Claude Code discovery is included, but its archive support is still
experimental because my measured Claude histories did not contain this kind of
inline-image bloat.

It does not upload telemetry or session data, display conversation content, or
modify an active transcript. Scanning is read-only. Source removal is optional
and occurs only after a full byte-exact reconstruction has been verified.

## Why I built it

I bought a 1 TB Mac, and about 20 days later it had 80 MB of free space left. I
assumed the healthcare datasets I had been working with were responsible. After
some debugging, my agent reported:

> The main culprit is not the healthcare data: `~/.codex/sessions` is about 566
> GiB, mostly individual rollout JSONL files of roughly 5 to 6 GiB each from
> September 3 to 5.

My reaction was basically, "what the shit?"

Those histories contained screenshots copied into JSONL as base64. Compaction
and related sessions had repeated many of the same images thousands of times.
I wanted the disk space back without blindly deleting my work or trusting a
lossy cleanup script. That became Sessionfold.

At 80 MB free, the machine was already too full to build a safe archive on the
same disk. I first freed some breathing room. If your internal drive is that
close to full, use `--store` to put the archive on an external volume.

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
python3 -m pip install https://github.com/shivampkumar/sessionfold/releases/download/v0.1.0a2/sessionfold-0.1.0a2-py3-none-any.whl
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

For a one-command archive and removal, after reviewing the risks below:

```bash
sessionfold archive /path/to/completed.jsonl --remove-source
```

Both removal paths perform the same second archive reconstruction and source
hash check. They refuse recent files, files open by another process, changed
sources, and platforms where open-file detection is unavailable.
Removing a vendor transcript may hide that session from the product UI until
it is restored.

## Defaults and scope

- Codex discovery: `${CODEX_HOME:-~/.codex}/sessions`
- Claude Code discovery: `~/.claude/projects`
- Archive store: `~/.sessionfold`
- Inline image candidates: 4 KiB to 64 MiB each

Creating an archive requires additional disk space before any source can be
removed. When the source disk is critically full, choose an external store:

```bash
sessionfold archive /path/to/completed.jsonl --store /Volumes/External/sessionfold
```

The initial archive format targets JSONL transcripts containing quoted
`data:image/*;base64,...` values. Unknown or small data URIs remain inline.
Transcript formats are vendor-owned and unstable, so compatibility must be
tested as they evolve. Sessionfold is archival storage; Codex and Claude Code
do not read its archive format directly. Codex is the validated target in this
alpha. Claude Code support should be treated as experimental.

If an archive store is relocated, pass its new root with `--store` to `verify`
or `restore`.

## Limits worth knowing

- Sessionfold cold-archives completed histories. It does not rewrite or shrink
  the live history that Codex is currently using.
- The first archive needs enough temporary headroom for its thin stream and any
  image blobs not already in the store. Use an external `--store` when the
  internal disk is critically full.
- Archive data is not encrypted. Protect it like the original transcript.
- Source removal depends on reliable open-file detection. It fails closed when
  that check is unavailable. In this alpha, removal is not supported by default
  on Windows, although scan, archive, verify, and restore run in Windows CI.
- The safety checks assume an ordinary single-user machine, not a malicious
  local process deliberately racing filesystem operations.
- Codex owns its transcript format and can change it. Verify compatibility on
  synthetic data after major Codex updates before reclaiming original files.

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
