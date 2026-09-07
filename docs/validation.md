# Validation record for 0.1.0a5

## Completed locally

- 30 unit, randomized boundary, metadata, and fault-injection tests pass.
- Ruff lint and format checks pass.
- Bandit reports no findings after review of the fixed `lsof` subprocess call.
- Python byte-compilation passes.
- Wheel and source distribution build successfully and pass `twine check`.
- The official Codex plugin validator accepts both the source directory and an
  extracted plugin ZIP.
- A fresh virtual environment installed the 0.1.0a1 wheel, archived a completed
  real session with 9,957 image occurrences, verified it, physically restored
  it, and matched the original byte for byte. The source was not removed.
- Generated distributions were scanned for the local username, real rollout
  identifiers, and benchmark hashes; none were present.
- A fresh tool installation from the 0.1.0a2 wheel verified the existing real
  6.44 GB archive byte for byte without materializing a restored copy.
- The 0.1.0a5 title lookup surfaced a generated Codex task name from the local
  index without reading the rollout, found an older archive by that title, and
  verified its byte-exact reconstruction. `--no-titles` suppresses title output.

## Real-corpus performance

One closed 6,440,831,294-byte Codex transcript became 1,046,558,275 stored bytes
from an empty store, an 83.7512% reduction. Archive plus full logical
verification took 21.63 seconds with a 70,893,568-byte maximum resident set.
The source was not modified. See `experiments/2026-09-06-feasibility.md`.

## CI

- Version 0.1.0a4 passed GitHub Actions on Linux with Python 3.10, 3.12, and
  3.14; macOS with Python 3.12; and Windows with Python 3.12. Version 0.1.0a5
  is pending the same matrix. Local packaging, Ruff, Bandit, wheel and
  source-distribution checks, and the plugin build pass.

## Not yet complete

- Independent-user beta testing has not begun.
- Full-disk, power-loss, filesystem-corruption, and true concurrent-process
  tests remain before source removal should leave experimental status.
