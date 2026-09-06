# ADR-001: Python, not TypeScript, for true Riot Commander inheritance

**Status:** Accepted, 2026-09-06
**Decider:** operator

## Context

The originating brief asked for two things at once:

1. "Inherits the complete design system, automation, testing pipelines, configs,
   and architectural patterns of an existing project called riot commander."
2. "Maintain the exact configuration style, linting, code quality hooks, and test
   runners from riot commander (e.g. Biome/ESLint/Prettier, TypeScript strict
   mode, Vitest/Jest)" plus a `Dockerfile` and `docker-compose.yml`.

These are mutually exclusive. Measured against the live Riot Commander tree on
2026-09-06:

- 2869 `.py` files against 1 `.ts` file, and that one is a generated
  `daemon_slayer_bundle.d.ts` inside a handoff mirror.
- No `package.json`, `tsconfig.json`, `biome.json`, `.eslintrc*`, `.prettierrc`,
  `vitest.config.*` or `jest.config.*` anywhere in the tree.
- No `Dockerfile` and no `docker-compose.yml` anywhere in the tree.
- The actual inherited config surface is `ruff.toml` (target py39, line length
  120, an `E,F,I,UP,B,BLE` select list with a BLE ratchet), `pytest.ini`,
  `mypy.ini`, six hooks under `.githooks/`, and three GitHub Actions workflows
  with a deliberate docs-only path-filter split.
- Even the Riot Commander web dashboard is plain vanilla JavaScript with no build
  step, no bundler and no type layer.

So the parenthetical list of tools in the brief did not describe Riot Commander.
Adopting it would have produced a repo that inherits nothing but a vibe.

## Decision

Build in **Python 3.11**, porting Riot Commander's real config surface.

The TypeScript interfaces the brief names by hand - `AccountState`,
`CurrencyLedger`, `PityState`, `ObjectiveNode`, `ResolutionPath`,
`EnkaMappedProfile` - are delivered as Python dataclasses in `core/types.py`,
preserving the contract while dropping the language.

## Consequences

- Everything in Riot Commander's operating manual transfers unchanged: the
  `py_compile`-before-restart rule, the atomic-write rule, the banned-glyph gate,
  the supervisor and `restart_trigger.txt` model, the `ops/runtime/health.json`
  contract, the dual-suite pytest convention, and the hooks story including the
  fact that a fresh clone runs none of them.
- One toolchain on the operator's workstation instead of two.
- No Docker in this scaffold, because there is nothing to inherit. Containers
  would be a new decision and would get their own ADR.

## Deliberate divergences from the parent

Recorded so they are not mistaken for drift:

- **`target-version = "py311"`, not `py39`.** Riot Commander pins py39 because it
  has a deployed py39 surface. This tree has none, so the `UP007` / `UP035` /
  `UP045` / `UP006` suppressions the parent needs for py39 compatibility are not
  inherited, and modern union and builtin-generic syntax is allowed.
- **`F401` and `F841` are not globally ignored.** The parent suppresses both as
  too noisy against a large existing tree. A greenfield tree has no such debt and
  both catch real defects, so they stay enabled, scoped off only for
  `__init__.py` re-exports.

## Rejected alternatives

- **TypeScript as literally briefed.** Rejected because it makes the stated
  inheritance impossible and doubles the toolchain burden on a solo-operator repo.
- **Python engine plus a TypeScript frontend.** Rejected for the initial scaffold
  as premature: it commits to two CI lanes before there is a single user-facing
  surface to justify the second. Revisit when a UI is actually specified.
