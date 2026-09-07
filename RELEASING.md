# Release checklist

No step below should be skipped for a public release.

## 1. Preflight

1. Confirm `agent-coldstore` remains available on PyPI, npm, and GitHub.
2. Choose the GitHub owner and add the exact repository URLs to `pyproject.toml`.
3. Review every README benchmark claim against `experiments/`.
4. Run the unit, compile, plugin, package, and clean-install checks.
5. Confirm generated artifacts contain no transcripts, manifests, hashes from
   private sessions, credentials, build caches, or local absolute paths.

## 2. Private beta

1. Create the repository as private.
2. Ask 3–5 users with independently generated, completed agent histories to
   run `scan`; collect only aggregate sizes and errors unless they opt in.
3. Have at least two users archive, verify, and physically restore a synthetic
   or non-sensitive fixture.
4. Exercise interrupted writes, a full disk, read-only directories, concurrent
   runs, missing blobs, and corrupted blobs on macOS and Linux.
5. Do not ask beta users to use `--remove-source` until restore tests pass.

## 3. Distribution validation

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile agent_coldstore/cli.py scripts/hook_guard.py
python3 -m build
python3 -m twine check dist/*
python3 scripts/build_plugin.py
```

Install the wheel into a fresh virtual environment and run `scan`, `archive`,
`verify`, and `restore` on a generated fixture. Validate the plugin with the
current official Codex validator and install the ZIP in a disposable profile.

## 4. Ship

1. Publish `0.1.0rc1` to TestPyPI and install it from TestPyPI on a clean host.
2. Make the repository public with security and privacy guidance visible.
3. Tag the exact validated commit and build artifacts from that tag.
4. Publish to PyPI using a project-scoped trusted publisher; do not store a
   reusable API token in the repository.
5. Attach the validated plugin ZIP and SHA-256 checksums to the GitHub release.
6. Keep source removal opt-in and prominently labelled experimental for 0.1.x.

## 5. Announce and observe

Post only after the PyPI install and GitHub release work from a clean machine.
Use the drafts under `launch/` as factual outlines. Hacker News prohibits
generated or AI-edited submission text, so rewrite that outline personally and
respect current Show HN account restrictions. Answer limitations directly and
avoid claiming that one measured corpus represents typical users. Triage
data-loss or privacy reports before feature requests.
