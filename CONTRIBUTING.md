# Contributing to ResinCompute

Thank you for wanting to help. This project has a small number of rules that are
enforced by tests and by git hooks rather than by review, so reading this first
saves you a rejected push.

Everything below was checked against this tree rather than assumed. Where a rule
has a guard, the guard is named so you can read it yourself.

## Before anything else: install the hooks

`core.hooksPath` is LOCAL git config. It is not cloned. A fresh clone therefore
runs **zero** hooks, and the tracked `.githooks/` directory sits inert until
somebody points git at it. The hooks are the authoritative gate in this project,
so a hookless clone is a clone with no gate at all.

First action in a new clone:

```
git clone https://github.com/Remus3/Resin-Compute.git
cd Resin-Compute
python scripts/install_hooks.py
```

That sets `core.hooksPath` for you. Never treat a hook's presence on disk as
proof that it fires - the only honest test is end to end.

## Setting up

Python 3.11 or newer. The runtime is stdlib-only on purpose, so `requirements.txt`
is deliberately empty and only the development toolchain needs installing:

```
python -m pip install -r requirements-dev.txt
```

## The gates

Run all four before you open a pull request. They are what CI runs.

```
python -m pytest tests
python -m pytest agents/pity_engine
python -m ruff check .
python -m mypy
```

**Two suites, run SEPARATELY. Never `pytest .` from the repository root.** The
engine package under `agents/pity_engine/` is self-validating and is mirrored as
a standalone unit; collecting it under a root-wide run is how the sibling project
this configuration came from earned an import-file-mismatch incident. The reason
is recorded in `pytest.ini`.

**`ruff` and `mypy` are not peers.** `ruff check .` traverses every tracked `.py`.
`mypy` traverses only the roots named in the `files=` list in `mypy.ini`, and it
prints a success line naming a file count that is a fraction of the tree. That
success says nothing at all about the roots outside the list. Treat mypy as
advisory over the tree as a whole and authoritative only inside its own roots;
`mypy.ini` records what bringing each remaining root in would cost, and
`tests/test_mypy_scope.py` goes red if a root silently leaves the list.

**Do not restate a suite count in any document.** Counts are not guarded, a
document is not a source of truth, and a number baked into a committed file goes
stale within the hour. Name the command instead.

## Test-driven development is required

Feature work and bug fixes follow the same loop:

1. Confirm every method, field and data shape your test will use actually exists
   before you write the test. Do not scaffold against an assumed API.
2. Write the failing characterization or regression test FIRST.
3. Run it and watch it fail for the RIGHT reason. A test that passes before the
   fix is a test about nothing.
4. Implement the minimum that makes it pass.
5. Root-cause, then siblings: grep for every other case sharing the same cause
   and fix them together. A data fix is not finished until already-corrupted
   records are backfilled, not merely prevented in future.

Pair every new guard with a non-vacuity arm proving the detector actually fires.
`tests/test_docs_consistency.py` and `tests/test_line_endings.py` both do this
and are worth reading as examples.

## Seven-bit ASCII, everywhere

No em-dashes, no en-dashes, no smart quotes, in any authored byte: code,
comments, docstrings, Markdown, commit messages. Use a spaced hyphen ` - ` for a
clause break.

This is not a style preference. Windows PowerShell 5.1 ANSI-decodes a `.ps1` file
that carries no BOM, so a UTF-8 em-dash inside a double-quoted string becomes a
smart quote that the tokenizer treats as a string terminator, and the file
cascades into a parse failure. `tools/precommit_gate.py` is the gate, and it runs
from the pre-commit hook over staged content and from the commit-msg hook over
your commit message. Do not make it find something.

Line endings are LF. `.gitattributes` pins `eol=lf` and
`tests/test_line_endings.py` guards it. A CRLF shebang in a hook makes the kernel
look for an interpreter that does not exist, and the gate then fails silently.

## Commit messages

The subject line must match Conventional Commits:
`<type>(<scope>)?: <description>`. The accepted types are `feat`, `fix`, `docs`,
`style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` and `revert`. The
validator is `scripts/precommit_msg_check.py`; auto-generated subjects such as
merges, reverts and fixups are skipped. Subjects over 100 characters get a
warning, not a rejection.

**Do not add agent trailers.** `Co-Authored-By: Claude` and `Claude-Session:`
lines are STRIPPED by the commit-msg hook per project policy, so a commit that
carries one still lands cleanly - it simply lands without the trailer. Their
absence is policy, not an omission, and it is not a defect to report.
`tests/test_commit_trailers.py` guards this.

If your message needs characters that a shell will mangle, write it to an
ASCII-only temporary file and use `git commit -F <file>`.

## Data: you may not vendor game data

This is the rule most likely to be broken by a well-meaning pull request, so it
is stated plainly.

**No Genshin Impact data is vendored into this repository, and none may be
added.** Not one row. That includes character tables, weapon tables, material
costs, ascension curves, text maps, icons and anything derived from a datamined
dump or from a wiki.

- `data/fixtures/` is HAND-AUTHORED. Nothing upstream is vendored into it. Two of
  its three files are records of publicly known game fact - real ids, verified
  independently and typed in one row at a time - and carry `_hand_authored: true`
  with `_vendored: false`. Only the sample profile is invented, and it is
  labelled `_synthetic: true`. Do not describe the directory as synthetic;
  hand-authored is both the accurate word and the stronger claim.
- `data/costs/` is empty on purpose. Cost tables must come from first-hand
  observation. Figures with no first-hand provenance stay in prose where they can
  be argued with, and `tests/test_goal_spec.py` fails if they are copied into
  `data/`.
- A permissive licence on an upstream wrapper does not clear its payload. Every
  candidate surveyed wraps HoYoverse-copyright assets, and no licence on a
  wrapper can grant rights to those.

**Read `docs/LICENSE_NOTES.md` before adding any data source, dataset or
dependency.** It records what was surveyed, what was refused and why, and
`tests/test_licence_posture.py` pins the posture. A pull request that adds an
ingest target without that verdict will not be merged.

The always-available path is the one this project already uses: re-implement from
observed behaviour and published protocol. Protocol facts are not copyrightable;
source is.

## Other rules with teeth

- **Atomic writes only.** Any file another process may read is written through
  `core/atomic_io.py`, which is the only sanctioned state-write path. Readers
  poll mid-write, so a partial file is a real failure rather than a theoretical
  one.
- **Never surface a raw API or error string** in a user-facing surface. Catch it,
  render a friendly degraded state, and log the raw error.
- **Ports.** `core/ports.py` is the single owner of this project's port block in
  code. No other tracked module restates the numbers, and `tests/test_ports.py`
  pins each against the module that really binds it.
- **Do not re-derive the gacha constants** from memory or from a search. They are
  recorded in `docs/SPEC_SCAFFOLD.md` section 3 with the corrections in
  `docs/adr/ADR-003-forecaster-model.md`, and the three that are easy to get
  wrong are regression-tested.
- **Adding a required field to a dataclass?** Append it at the END with a
  default. A mid-class required field breaks every existing positional
  construction and its tests.
- **Windows.** Never use `Stop-Process`. Use `taskkill /F /PID <pid>`, and under
  Git Bash write it with doubled slashes, because MSYS path conversion rewrites a
  lone flag into a path and the call then fails silently.
- **No per-file licence headers and no SPDX identifiers.** The outbound licence
  attaches at the repository level through `LICENSE` and `NOTICE`. The reasoning,
  including the line numbers in `LICENSE` that settle it, is in
  `docs/adr/ADR-009-per-file-licence-headers.md`. Please do not add them back.

## Before re-litigating a past decision

Read `docs/adr/README.md` first. The architectural decisions are indexed there,
each with its status and its reasoning, and several of them record options that
were considered and refused. If you still disagree, open an issue proposing a new
ADR rather than changing the behaviour and leaving the record behind.

## Pull requests

Fill in `.github/PULL_REQUEST_TEMPLATE.md` - GitHub loads it for you. In short:

- One coherent change per pull request.
- All four gates run, with the commands and their results stated.
- New behaviour has a test that failed before the change.
- No vendored game data, and any new dependency or data source carries a licence
  verdict.
- Documents you touched still point at paths that exist AND that git stores. An
  empty directory resolves on your machine and reaches nobody else's clone;
  `tests/test_docs_consistency.py` and `tests/test_readme_tree.py` check this.

## Licensing of your contribution

This project is **GPL-3.0-or-later**. By contributing you agree that your
contribution is licensed under those terms. See `LICENSE` for the full text,
`NOTICE` for the copyright line and the game-data disclaimer, and
`docs/adr/ADR-006-outbound-licence.md` for why.

That is an outbound licence covering this project's own code. It grants nothing
over Genshin Impact's data, names, statistics or assets.

## Conduct and security

Participation is governed by `CODE_OF_CONDUCT.md`. Please do not report a
security issue in a public issue or pull request - `SECURITY.md` has the private
route.
