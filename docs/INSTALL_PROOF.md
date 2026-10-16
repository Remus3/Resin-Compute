# Install proof - hashed lockfiles

MAIN ORDER 1925 item e (2026-10-15): keep an unhashed `requirements.in`,
generate `requirements.txt` from it with `--generate-hashes` covering every
transitive, and prove the installer in a fresh venv per interpreter before
commit.

## The installer

ResinCompute's installer is two pip commands, run from the repo root in the
environment that will run the tree. They are exactly what
`.github/workflows/ci.yml` runs:

```
python -m pip install --require-hashes -r requirements.txt
python -m pip install --require-hashes -r requirements-dev.txt
```

`requirements.txt` is the runtime lock, compiled from `requirements.in`. The
runtime is stdlib-only, so `requirements.in` declares nothing and the lock
holds only the pip-compile header; the first command installs nothing and
exits 0. It is still run, under `--require-hashes`, so that a runtime pin
added without a hash fails at once. `requirements-dev.txt` is the dev lock
(ruff, pytest, mypy, pytest-timeout and their closure), compiled from
`requirements-dev.in`. Both locks are pip-compile output from pip-tools
7.5.3 under Python 3.11; `tests/test_runtime_lock.py` grades each pair.

## Decision: no install.bat

The order's text says "prove install.bat". This tree has no `install.bat`.
Adjudicated as option B.

- **B (taken):** the installer is the pip command pair above, proven per
  interpreter. It is the one path CI already exercises on every run.
- **A (rejected): a literal `install.bat`.** It would be a dead wrapper
  around the same two commands: Windows-only, called by nothing in CI, and a
  second spelling of the install that can drift from `ci.yml`.
- **C (rejected): a partial proof** - one interpreter, or the runtime lock
  only. The order asks for every supported minor plus the embedded runtime,
  and the runtime lock alone proves nothing because it is empty.

Reversed by: a MAIN ruling, or the tree gaining an end-user install path
that is not a developer checkout.

## Proof table

Each row: a FRESH venv from that interpreter, then the runtime lock install,
then the dev lock install (both `--require-hashes`), then a smoke import of
`core.types`, `core.atomic_io`, `engines`, `ingest.enka_client` and
`agents.pity_engine` from the repo root. Exit codes as observed. Every venv
and every fetched interpreter was deleted afterwards. Lock bytes: commit
`5016724` (neither lock changed after it).

| Interpreter | Version | Runtime lock exit | Dev lock exit | Smoke | Date |
|---|---|---|---|---|---|
| CPython 3.11 (python.org) | 3.11.9 | 0 | 0 | OK | 2026-10-15 |
| CPython 3.12 (python.org) | 3.12.10 | 0 | 0 | OK | 2026-10-15 |
| CPython 3.12 (uv-managed) | 3.12.13 | 0 | 0 | OK | 2026-10-15 |
| CPython 3.13 (uv-managed, fetched for the proof) | 3.13.13 | 0 | 0 | OK | 2026-10-15 |
| CPython 3.14 (python.org) | 3.14.4 | 0 | 0 | OK | 2026-10-15 |
| Embedded runtime (Windows embeddable 3.11) | 3.11.9 | 0 | 0 | OK | 2026-10-15 |

Every dev install resolved the pinned set ruff 0.16.10, pytest 9.1.1, mypy
2.4.0 and pytest-timeout 2.4.0.

The embedded runtime is not part of this repo. The proof used a copy of a
Windows embeddable CPython 3.11 distribution present on the host, with a
fresh empty `Lib/site-packages` and pip 24.0 run from its own wheel (an
embeddable distribution ships no pip and no venv module). The original was
only read.
