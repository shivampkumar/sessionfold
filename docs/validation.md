# Validation record for 0.1.0

## Completed locally

- 23 unit and fault-injection tests pass.
- Ruff lint and format checks pass.
- Bandit reports no findings after review of the fixed `lsof` subprocess call.
- Python byte-compilation passes.
- Wheel and source distribution build successfully and pass `twine check`.
- The official Codex plugin validator accepts both the source directory and an
  extracted plugin ZIP.
- A fresh virtual environment installed the wheel, archived a completed real
  session with 94 image occurrences, verified it, physically restored it, and
  matched the original with `cmp`.
- Generated distributions were scanned for the local username, real rollout
  identifiers, and benchmark hashes; none were present.

## Real-corpus performance

One closed 6,440,831,294-byte Codex transcript became 1,046,558,275 stored bytes
from an empty store, an 83.7512% reduction. Archive plus full logical
verification took 21.63 seconds with a 70,893,568-byte maximum resident set.
The source was not modified. See `experiments/2026-09-06-feasibility.md`.

## Not yet complete

- CI has not run because the repository has not been pushed.
- Python 3.10–3.13, Linux, and Windows are represented in CI but not yet observed.
- Independent-user beta testing has not begun.
- Full-disk, power-loss, filesystem-corruption, and true concurrent-process
  tests remain before source removal should leave experimental status.
