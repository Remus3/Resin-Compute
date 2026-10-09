# Session default - shared by every agent in `.claude/agents/`

Every agent file in `.claude/agents/` tells its agent to Read this file FIRST.
Subagent context does NOT inherit the main thread's, so this file is how
`CLAUDE.md`'s "Session default - the shape, not an escalation" section reaches
a subagent. It lives OUTSIDE `.claude/agents/` because every `.md` there
registers an agent. Source: MAIN 2246 ORDER section 2 PERF-AUDIT item 6, which
replaced seven inline copies (about 72 KB) with this one file.
`tests/test_agent_roster.py` Guard 9 pins it.

## The shape

- **Orchestrated.** One merger holds the plan and the merge. Work decomposes
  into DISJOINT slices BEFORE any of it starts. The merger's context holds the
  plan and the seams, not the implementations.
- **Multi-agent.** Slices run in parallel on non-overlapping files, worktree
  isolated wherever they write. Disjointness is a PRECONDITION checked before
  dispatch. An undeclared write-list is a merge conflict already.
- **Self-adjudicating.** A distinct agent decides between competing outputs
  against stated criteria. THE AGENT THAT PRODUCED A THING NEVER GRADES IT. If
  you authored any part of what you are asked to grade, say so and recuse.
  Freeze the candidate (a SHA or a worktree) before it is graded; if the tree
  moves under you, say so and re-measure.
- **Self-adversarial.** Findings and done-claims get an independent pass whose
  job is to REFUTE them, defaulting to refuted when uncertain.
- Agreement between two agents is NOT evidence. Two agents can share one wrong
  premise. If two agree, find their SHARED INPUT and test THAT.
- NEVER trust a subagent's claim about test counts, green CI or file
  existence. Probe it independently. Report only counts observed THIS run.
- **Subagent-first** (operator directive 2026-09-09). The main session is the
  operator's surface: it plans, dispatches, merges and reports. Long work runs
  in agents and reports through a progress file, not through chat.
- Independence is a PROMPT-LEVEL property, not a vendor-level one. Do not add
  a second vendor for "independent review".

Choosing this shape needs no justification. Departing from it does, and the
departure is recorded.

## Risk scaling - scale the adversarial pass by what the diff touches

- **The full lens set** - distinct-lens adversaries (correctness, licence,
  does-it-reproduce, resource lifetime, scope-and-siblings), never N
  identical skeptics - runs ONLY when the diff touches `agents/pity_engine/`, `engines/`,
  `ingest/` or `core/`.
- **Plumbing** - `tools/`, `headless/`, `scripts/`, `ops/`, `tests/`, docs,
  `.claude/`, `.github/`, `.githooks/` - gets
  one adversary lens or a verifier only. Pick the lens the change most plausibly breaks.
- A diff touching both is graded at the higher tier.
- **Refute rounds: at most 2 refute rounds per finding or done-claim,
  then the adjudicator decides.** A third adversary on the same claim is not dispatched;
  the adjudicator rules on the record of the two rounds, and the ruling is
  recorded.

## Hard rules on every byte

- **7-bit ASCII only** in every authored byte - code, docs, reports, commit
  messages, chat. No em-dash, no en-dash, no smart quotes; use ` - `. Not
  style: PowerShell 5.1 ANSI-decodes a no-BOM `.ps1` and a UTF-8 em-dash
  becomes a string terminator. `tools/precommit_gate.py` is the gate.
- **Never add a `Co-Authored-By: Claude` trailer**, and never file its
  absence as a defect. `.githooks/commit-msg` strips it per operator policy.
- **Atomic writes only** for anything a reader polls, through
  `core/atomic_io.py`.
- **`py_compile` before any restart**; restart with
  `echo restart > restart_trigger.txt`, verify by a NEW `pid` and `alive=true`
  in `ops/runtime/health.json`, never by looking at a window.
- **Two suites, run SEPARATELY:** `python -m pytest tests` and
  `python -m pytest agents/pity_engine`. NEVER `pytest .` from the root. Never
  pass `-q`. Plus `python -m ruff check .`. Run suites to a FILE and read the
  file back, with an `EXIT=` sentinel.
- `python -m mypy` covers only `core/`, `engines/`, `ingest/`,
  `agents/pity_engine/` and `tools/`. Its Success says nothing about any other
  root.
- **Never `Stop-Process`.** `taskkill /F /PID <pid>`; under Git Bash
  `taskkill //F //PID <pid>` (MSYS rewrites a lone `/F` into `F:/`).
- **Vendor no game data.** `data/fixtures/` is hand-authored only. See
  `docs/LICENSE_NOTES.md` before any new source.
- **Never surface a raw API or error string** on a user-facing surface.
- **Do not re-derive gacha constants.** They are in `docs/SPEC_SCAFFOLD.md`
  section 3, corrected by `docs/adr/ADR-003-forecaster-model.md`: the 50/50 is
  55.000 percent consolidated since 5.0; the weapon soft-pity ramp saturates
  at pull 77; 1.600 percent is `1 / E[wishes per 5-star]`, never a per-wish
  Bernoulli parameter.

## Read-only agents

An agent whose `tools:` list omits Edit and Write never edits, creates, moves,
deletes, stages, commits or pushes. Bash, where granted, is for read-only
probes and test runs. **Adjudicated ruling: a gitignored progress file under
`ops/loop/control/progress/` is NOT a repo edit and is allowed** - the one
write such an agent makes. `.gitignore` excludes `ops/loop/control/`, and
`tests/test_agent_roster.py` reds if it stops doing so, at which point the
permission is void.

## Progress file - FLEET-COMMON item 12

Work expected to take over 5 minutes writes a progress file after EACH step.
The dispatch prompt names the file; if not, use
`ops/loop/control/progress/<task>.json`. Exactly these six keys:

    {"task": "<task>", "pct": <0-100>, "step": "<what just finished>",
     "eta_s": <seconds left>, "status": "running|done|failed", "updated": "<UTC ISO-8601>"}

`"status"` is one of running|done|failed. Write it through
`core/atomic_io.py` from your working-tree root:

    python -c "import datetime as d; from core.atomic_io import atomic_write_json as w; w('ops/loop/control/progress/sliceA.json', {'task': 'sliceA', 'pct': 40, 'step': 'tests written', 'eta_s': 300, 'status': 'running', 'updated': d.datetime.now(d.timezone.utc).isoformat(timespec='seconds')})"

In a worktree it lands under that worktree, and the main thread reads
`.claude/worktrees/*/ops/loop/control/progress/` too. Finish on `done` or
`failed`; a file that stops updating for 2x its own ETA step is treated as a
failure. The file carries status, never findings.

## Verdict lines

Each agent's own file states its byte-exact verdict vocabulary. The
orchestrator string-matches it: never invent a variant, never round a weaker
verdict up, and a caveat stated in chat is not a caveat in the artifact.
