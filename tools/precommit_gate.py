#!/usr/bin/env python3
"""Commit-time hygiene gate: banned glyphs + NET-NEW ruff findings.

Ported from Sibling-C's tools/precommit_gate.py. Three modes, and the
split between them is forced by git's own hook ordering rather than by taste:

  1. STAGED-CONTENT mode (default). Reads a command string on stdin. If that
     command is not a `git commit`, exits 0 immediately without touching git,
     so the script is a no-op on every other invocation. On a commit it
     inspects ONLY the staged content of staged files (diff-filter ACM):
       * banned-glyph scan on ADDED (+) lines, reported as file:line
       * py_compile on staged .py - a syntax error is a silent crash later
       * `ruff check` on staged .py, keeping only findings whose row lands in
         an ADDED line range, so pre-existing debt in an untouched region
         never blocks an unattended run
     Invoked from .githooks/pre-commit as: echo "git commit" | this script.

  2. --message-file <path> mode. Scans a prepared commit MESSAGE.

     WHY THIS CANNOT LIVE IN pre-commit
     ----------------------------------
     Git's order is: pre-commit -> prepare the message -> commit-msg. When
     pre-commit runs, .git/COMMIT_EDITMSG DOES NOT EXIST YET, so there is
     nothing to scan. The message half therefore has to run from commit-msg,
     which is handed the message file as $1. Splitting the gate across the two
     hooks is required, not stylistic.

     Sibling-C measured the consequence of missing that on 2026-07-26:
     while the gate was invoked only from pre-commit, the staged-content and
     ruff halves still fired - so the gate LOOKED healthy - and a commit whose
     SUBJECT carried a U+2014 em-dash landed completely clean.

  3. --scan-files <path>... mode. Scans whole files, not just added lines.
     Used by hand for a drift sweep. This is the only mode that does not
     consult git.

  4. --scan-files-from0 <listfile> mode. Same scan, but the paths are read
     NUL-DELIMITED from a file instead of from argv.

     WHY THIS EXISTS, measured 2026-09-06
     ------------------------------------
     Both CI workflows used to hand the path list over as
     `xargs -r -a list.txt python tools/precommit_gate.py --scan-files`.
     `xargs` splits on WHITESPACE, so a tracked path carrying a space became
     TWO bogus arguments, both of which failed to open. The old code warned on
     stderr and `continue`d, so the gate printed "0 file(s) scanned, 7-bit
     ASCII clean" AND EXITED 0 over a file carrying an em-dash. Passing the
     same path directly exited 1. A single quote in a name went the other way:
     `xargs: unmatched single quote`, exit 1 on a legal filename.

     Reading a NUL-delimited list removes the shell from the handoff
     completely, so a space, a single quote, a double quote and a newline in a
     filename are all carried intact.

  5. --list-tracked {source|docs|all} and --scan-tracked {source|docs}. The
     SELECTION half of the rule, defined here rather than in YAML.

     ci.yml used to select by an extension ALLOWLIST while docs-guards.yml
     selected '*.md', and 14 tracked files matched NEITHER - among them
     ops/install_scheduled_task.ps1, which is the file class the whole
     7-bit-ASCII rule exists for, and every .githooks/ script. An allowlist
     has to be maintained; a PARTITION on the .md suffix cannot develop a hole,
     because `source` is defined as the complement of `docs`.

Any scan mode accepts a leading `--expect-count N`, which fails the run when
the number of paths SELECTED is not N. That is the anti-vacuity arm: a gate
that scanned nothing must never report clean.

EXIT CODES. Any finding exits 1 (SPEC_SCAFFOLD / build contract).
Sibling-C's copy exits 2 because it doubles as a Claude Code PreToolUse hook,
where 2 specifically means "block the tool call"; that contract does not exist
here. Both values are non-zero, so a git hook treats them identically.

FAIL-OPEN RULE, inherited verbatim. When the gate cannot run a half of itself
(ruff missing, message file unreadable) it lets the commit through - a gate
that wedges every commit in the repo is worse than the drift it guards - but
it NEVER fails silently. It says on stderr which half did not run.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

# Hooks may run under a windowless interpreter on Windows; a console-subsystem
# child (git / ruff) would otherwise get a fresh console allocated, which is an
# on-screen and taskbar flash. CREATE_NO_WINDOW suppresses it. Windows-only
# attribute, so it resolves to 0 everywhere else.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# The six glyphs named by the hard rule, kept as an explicit map so the report
# says "em-dash" rather than a bare codepoint. The catch-all in _glyph_hits
# covers everything else above 127.
_BANNED = {
    chr(0x2014): "em-dash",
    chr(0x2013): "en-dash",
    chr(0x201C): "smart-dquote-open",
    chr(0x201D): "smart-dquote-close",
    chr(0x2018): "smart-quote-open",
    chr(0x2019): "smart-quote-close",
}

_SKIP_PARTS = ("logs/", ".git/", "__pycache__/", ".pyc")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# Surfaces the 7-bit-ASCII rule does not reach.
#
# data/cache/ holds FETCHED third-party payloads. Character and item names
# arrive from upstream carrying whatever codepoints upstream authored; this
# repo did not write them and cannot fix them, so flagging them would block a
# correct cache refresh - and a gate that blocks correct work is one people
# learn to bypass with --no-verify.
#
# EVERY PREFIX HERE MUST BE GITIGNORED, and data/cache/ is (.gitignore line
# 45). An exemption for a path that CAN be committed is a pre-cut hole, not an
# exemption: `data/external/` sat in this tuple until 2026-09-06 while being
# gitignored NOWHERE and referenced by NO other file in the tree, so the one
# gate that would flag a fetched upstream payload was pre-disabled at a path
# `git add -A` would have staged without a word. The vendoring refusal in
# docs/LICENSE_NOTES.md is the single leg the publication decision rests on;
# it cannot rest on a gate that was switched off in advance. Removed.
#
# data/fixtures/ is deliberately NOT exempt. Those are hand-authored minimal
# test fixtures (SPEC_SCAFFOLD section 4), which makes them authored content.
_ASCII_EXEMPT_PARTS = ("logs/", "__pycache__/", ".git/")
_ASCII_EXEMPT_SUFFIXES = (
    ".log", ".jsonl", ".pyc", ".png", ".jpg", ".jpeg", ".ico", ".zip", ".gz",
)
_ASCII_EXEMPT_PREFIXES = ("data/cache/",)


def _is_commit(command: str) -> bool:
    """True if the command string is a `git commit`.

    Tolerates leading env assignments, `&&` / `;` chains, shell blocks, and
    global flags with quoted arguments (git -C "/some/path" commit).
    """
    return bool(
        re.search(
            r"(^|[;&|{(]\s*)git\s+(?:(?:-\S+|\"[^\"]*\"|'[^']*')\s+)*commit\b",
            command.strip(),
        )
    )


def _skippable(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(s in p for s in _SKIP_PARTS)


def _git(args: list[str], root: str | None) -> str | None:
    """stdout on success, `None` when git could not answer.

    It used to return `out.stdout` unconditionally and never look at
    `out.returncode`, so a `git diff --cached` that exited 129 - the exit code
    a non-repo directory really produces - came back as `""` and was
    indistinguishable from a repo with nothing staged. `None` is the only way a
    caller can tell "read, and empty" from "not read at all".
    """
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=root or None,
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=_NO_WINDOW,
        )
        if out.returncode != 0:
            return None
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        return None


_DASH_C = re.compile(r"git\s+-C\s+(\"([^\"]+)\"|'([^']+)'|(\S+))")


def _root_from_command(command: str) -> str | None:
    """Repo dir from `git -C <path> ... commit`.

    Prefers the segment that actually carries the commit: a worktree agent
    commits via -C into its own tree, so resolving the hook's CWD instead would
    gate the WRONG repo's staged diff.
    """
    root = None
    for m in _DASH_C.finditer(command):
        path = m.group(2) or m.group(3) or m.group(4)
        tail = command[m.end():]
        if re.match(r"\s+(?:(?:-\S+|\"[^\"]*\"|'[^']*')\s+)*commit\b", tail):
            return path
        root = root or path
    return root


def _staged_added(root: str) -> dict[str, dict] | None:
    """Return {path: {"ranges": [(start, end)...], "lines": [(lineno, text)...]}}.

    Only ADDED lines and their line ranges - the gate never judges a line this
    commit did not write.

    `None` when the staged diff could not be read at all, which is a different
    fact from an empty dict and must not be collapsed into one. An empty dict is
    a genuine no-op commit; `None` is a corpus the gate never saw.
    """
    diff = _git(["diff", "--cached", "--unified=0", "--no-color"], root)
    if diff is None:
        return None
    files: dict[str, dict] = {}
    cur: str | None = None
    lineno = 0
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            p = ln[4:].strip()
            cur = None if p == "/dev/null" else p[2:] if p.startswith("b/") else p
            if cur and not _skippable(cur):
                files.setdefault(cur, {"ranges": [], "lines": []})
            else:
                cur = None
            continue
        if ln.startswith("@@"):
            m = _HUNK.match(ln)
            if m and cur:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) else 1
                lineno = start
                if count:
                    files[cur]["ranges"].append((start, start + count - 1))
            continue
        if cur and ln.startswith("+") and not ln.startswith("+++"):
            files[cur]["lines"].append((lineno, ln[1:]))
            lineno += 1
    return files


def _ascii_exempt(path: str) -> bool:
    p = (path or "").replace("\\", "/")
    if any(part in p for part in _ASCII_EXEMPT_PARTS):
        return True
    if p.endswith(_ASCII_EXEMPT_SUFFIXES):
        return True
    return p.startswith(_ASCII_EXEMPT_PREFIXES)


def _glyph_hits(text: str, path: str = "") -> list[str]:
    """Named diagnostics for the six historical glyphs, then a CATCH-ALL.

    The catch-all is not padding. Sibling-C's gate held exactly six
    characters, so every OTHER non-ASCII codepoint passed unremarked - which is
    how a U+00D7 multiplication sign reached that repo and turned an unrelated
    ASCII-hygiene test red through a gate working exactly as written. Two rules
    enforcing the same "7-bit ASCII authored content" hard rule disagreed about
    what it meant, and the looser one ran first.

    The codepoint is reported so a hit is actionable rather than merely refused.
    """
    if _ascii_exempt(path):
        return []
    hits = {name for ch, name in _BANNED.items() if ch in text}
    hits |= {
        f"non-ascii U+{ord(c):04X} ({c.encode('unicode_escape').decode()})"
        for c in text
        if ord(c) > 127 and c not in _BANNED
    }
    return sorted(hits)


def _compile_errors(pyfiles: list[str], root: str) -> list[str]:
    """py_compile each staged .py.

    A syntax error is a silent crash at runtime under a windowless interpreter
    (the hard rule this scaffold inherits), so it is blocked at commit rather
    than discovered later.
    """
    import py_compile

    out: list[str] = []
    for rel in pyfiles:
        path = os.path.join(root, rel)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as exc:
            out.append(f"  {rel}  py_compile: {exc.msg.splitlines()[0][:160]}")
        except OSError:
            pass
    return out


def _ruff_candidates() -> list[list[str]]:
    """Ruff invocations to try, in order, until one answers `--version`.

    Resolved at CALL time on purpose. This gate runs on more than one channel -
    a git hook launched by whatever `sh` picked, a developer shell, CI - and
    those do not share an interpreter. Sibling-C hardcoded sys.executable
    to fix one channel and thereby broke the other, leaving the ruff half dead
    for three weeks on the AUTHORITATIVE channel while the gate still looked
    healthy. Probing beats guessing.
    """
    return [
        [sys.executable, "-m", "ruff"],
        ["ruff"],
        ["python3", "-m", "ruff"],
        ["python", "-m", "ruff"],
    ]


def _resolve_ruff() -> list[str] | None:
    """First candidate whose `--version` succeeds, or None if ruff is absent."""
    for cmd in _ruff_candidates():
        try:
            probe = subprocess.run(
                [*cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and (probe.stdout or "").strip().startswith("ruff"):
            return list(cmd)
    return None


def _report(violations: list[str], headline: str) -> int:
    sys.stderr.write(
        f"precommit_gate BLOCKED - {headline}\n"
        + "\n".join(violations)
        + "\n\nFix the lines above and retry:\n"
        "  glyph      the tree is 7-bit ASCII by hard rule - use a spaced\n"
        "             hyphen ' - ' for a clause break\n"
        "  ruff       ruff check --fix, or fix it by hand\n"
        "  py_compile the file does not parse; it must never enter history\n"
    )
    return 1


def _check_message_file(path: str) -> int:
    """commit-msg entry point: scan the prepared commit message for glyphs.

    FAILS OPEN on an unreadable file, loudly. See the module docstring for why
    this half cannot live in pre-commit.
    """
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        sys.stderr.write(
            f"precommit_gate WARNING: could not read {path} ({exc}) - the "
            "commit-message glyph half did NOT run on this commit.\n"
        )
        return 0
    # Drop git's own template comments. They are stripped before the commit is
    # created, so a glyph inside one is not a glyph in the message.
    violations: list[str] = []
    for i, ln in enumerate(text.splitlines(), start=1):
        if ln.lstrip().startswith("#"):
            continue
        hits = _glyph_hits(ln)
        if hits:
            violations.append(f"  <commit message>:{i}  banned glyph: {', '.join(hits)}")
    if violations:
        return _report(violations, "banned glyph in the commit message:")
    return 0


def _git_z(args: list[str], root: str | None = None) -> list[str] | None:
    """Run git and split NUL-delimited stdout into paths. None if git failed.

    NUL-delimited on purpose, and the two reasons are different. `git ls-files`
    without -z separates on NEWLINE, which a filename may legally contain on
    Linux; and it QUOTES any path it considers unusual (core.quotePath), so a
    path carrying a space or a quote cannot be recovered from that stream
    unambiguously. -z emits the raw bytes with a NUL terminator and no quoting
    at all.
    """
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=root or None,
            capture_output=True,
            timeout=30,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    raw = out.stdout.decode("utf-8", "surrogateescape")
    return [p for p in raw.split("\0") if p]


def _tracked_split(root: str | None = None) -> tuple[list[str], list[str]] | None:
    """(source, docs): every tracked path, PARTITIONED on the .md suffix.

    Complements by construction. That is the whole point: an extension
    allowlist has to be maintained and silently stops covering whatever is
    added after it was written, while a partition cannot develop a hole
    because one half is defined as the complement of the other.

    CASE-SENSITIVE on purpose, and it has to be. The partition exists to mirror
    the ci.yml / docs-guards.yml trigger complement, and GitHub's `paths` /
    `paths-ignore` globs and git's own `*.md` pathspec are both case-sensitive
    on Linux. Lower-casing here would put a `README.MD` in the docs half while
    both workflows put it in the source half, and the disagreement would be a
    file neither gate scanned.

    Returns None when git could not be consulted - callers must fail CLOSED on
    that, never report a clean sweep they did not perform.
    """
    paths = _git_z(["ls-files", "-z"], root)
    if paths is None:
        return None
    docs = [p for p in paths if p.endswith(".md")]
    source = [p for p in paths if not p.endswith(".md")]
    return source, docs


def _paths_from_nul_file(path: str) -> list[str] | None:
    """Read a NUL-delimited path list written by `git ls-files -z`."""
    try:
        raw = pathlib.Path(path).read_bytes()
    except OSError:
        return None
    return [p for p in raw.decode("utf-8", "surrogateescape").split("\0") if p]


def _check_scan_files(paths: list[str], expect_count: int | None = None) -> int:
    """--scan-files entry point: whole-file glyph scan, reported as file:line.

    Whole-file rather than added-lines-only, because CI has no staged diff to
    consult.

    FAIL-CLOSED, unlike the ruff and message halves, and the difference is not
    inconsistency. Those two fail open because the gate could not run a half of
    ITSELF. Here the caller NAMED a file: being unable to read it means the
    sweep did not cover what it was asked to cover, which is indistinguishable
    from the file being clean unless it is reported as a finding. It used to
    warn and `continue`, and that is exactly how the xargs word-splitting
    defect printed "7-bit ASCII clean" and exited 0 over an em-dash.
    """
    selected = len(paths)
    if selected == 0:
        sys.stderr.write(
            "precommit_gate BLOCKED - the sweep selected NOTHING, so a clean "
            "result would mean nothing.\n  A gate that scanned zero files must "
            "not report zero findings as a pass.\n"
        )
        return 1
    if expect_count is not None and selected != expect_count:
        sys.stderr.write(
            f"precommit_gate BLOCKED - selected {selected} path(s) but the "
            f"caller expected {expect_count}.\n  The two counts are computed "
            "independently; a mismatch means the path list was mangled in "
            "transit, which is how a sweep silently stops covering the tree.\n"
        )
        return 1

    violations: list[str] = []
    scanned = 0
    exempt = 0
    for p in paths:
        if _ascii_exempt(p):
            exempt += 1
            continue
        try:
            data = pathlib.Path(p).read_bytes()
        except OSError as exc:
            violations.append(f"  {p}  UNREADABLE: {exc}")
            continue
        if b"\x00" in data:
            # Degrade LOUDLY rather than skipping. "It is binary" must never
            # become a silent pass, or the exemption grows back the hole this
            # partition was built to close. A genuinely binary tracked file
            # gets an explicit suffix in _ASCII_EXEMPT_SUFFIXES, with a reason.
            violations.append(
                f"  {p}  BINARY (NUL byte): the 7-bit ASCII rule cannot be "
                "applied - add its suffix to _ASCII_EXEMPT_SUFFIXES with a "
                "recorded reason, or do not track it"
            )
            continue
        scanned += 1
        for i, ln in enumerate(data.decode("utf-8", "replace").splitlines(), start=1):
            hits = _glyph_hits(ln, p)
            if hits:
                violations.append(f"  {p}:{i}  banned glyph: {', '.join(hits)}")
    if violations:
        return _report(violations, f"banned glyph or unscannable file in {len(violations)} place(s):")
    # First line kept BYTE-COMPATIBLE with the pre-2026-09-06 format; anything
    # parsing it keeps working. The arithmetic below it is the new part.
    print(f"precommit_gate: {scanned} file(s) scanned, 7-bit ASCII clean")
    print(f"precommit_gate: selected={selected} scanned={scanned} exempt={exempt}")
    return 0


def _check_scan_tracked(mode: str, expect_count: int | None = None) -> int:
    """--scan-tracked entry point: select from git, then scan, in ONE process.

    No shell between the selection and the scan, so there is no handoff left to
    mangle.
    """
    if mode not in ("source", "docs"):
        sys.stderr.write(
            f"precommit_gate: --scan-tracked takes 'source' or 'docs', not {mode!r}\n"
        )
        return 1
    split = _tracked_split()
    if split is None:
        sys.stderr.write(
            "precommit_gate BLOCKED - `git ls-files -z` did not answer, so the "
            "tracked file set is unknown.\n  Fail CLOSED: a sweep that could "
            "not choose its inputs has not run.\n"
        )
        return 1
    source, docs = split
    paths = source if mode == "source" else docs
    print(f"precommit_gate: --scan-tracked {mode} selected {len(paths)} tracked path(s)")
    return _check_scan_files(paths, expect_count=expect_count)


def _list_tracked(mode: str) -> int:
    """--list-tracked entry point: NUL-delimited paths on stdout.

    Exists so the workflows and tests/test_ci_workflow_complement.py consume
    ONE definition of the partition rather than three restatements of it.
    """
    if mode not in ("source", "docs", "all"):
        sys.stderr.write(
            f"precommit_gate: --list-tracked takes 'source', 'docs' or 'all', "
            f"not {mode!r}\n"
        )
        return 1
    split = _tracked_split()
    if split is None:
        sys.stderr.write("precommit_gate: `git ls-files -z` did not answer\n")
        return 1
    source, docs = split
    paths = {"source": source, "docs": docs, "all": source + docs}[mode]
    sys.stdout.buffer.write(
        b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in paths)
    )
    sys.stdout.flush()
    return 0


def _check_staged(command: str) -> int:
    root = (
        _root_from_command(command)
        # Root RESOLUTION keeps its permissive fall-through: the designed
        # default is correct in the hook's real invocation, and a wrong root now
        # surfaces one line down as `_staged_added -> None` and blocks there, so
        # one choke point at the CORPUS read is sufficient. `_git` can answer
        # None, and `.strip()` on None is an AttributeError, hence the `or ""`.
        or (_git(["rev-parse", "--show-toplevel"], os.getcwd()) or "").strip()
        or os.getcwd()
    )
    staged = _staged_added(root)
    if staged is None:
        # FAIL CLOSED. Same rule as _check_scan_files: a gate that scanned zero
        # files must not report zero findings as a pass. The FAIL-OPEN RULE
        # covers tool provisioning (ruff missing, message file unreadable) - a
        # half the gate needs to RUN. The staged diff is not a tool; it is this
        # half's SUBJECT, and an unreadable subject wedges only the one commit
        # whose corpus cannot be read, which is the commit that must not pass.
        sys.stderr.write(
            "precommit_gate BLOCKED - the STAGED half did NOT run: `git diff "
            "--cached` could not be read.\n  Root consulted: "
            + root
            + "\n  NO scan was performed - no banned-glyph check on added "
            "lines, no py_compile, no net-new ruff. A gate that read zero "
            "staged lines must not report zero findings as a pass.\n"
        )
        return 1
    violations: list[str] = []

    # 1. Banned glyphs on ADDED lines, named as file:line.
    for path, info in staged.items():
        for lineno, text in info["lines"]:
            hits = _glyph_hits(text, path)
            if hits:
                violations.append(f"  {path}:{lineno}  banned glyph: {', '.join(hits)}")

    # 2. Glyphs in the commit message when it is inline in the command string
    #    (`git commit -m "..."`). The interactive-editor path is covered by
    #    --message-file from commit-msg instead.
    msg_hits = _glyph_hits(command, "<commit-message>")
    if msg_hits:
        violations.append(f"  commit message  banned glyph: {', '.join(msg_hits)}")

    # 3. py_compile + NET-NEW ruff on staged .py.
    pyfiles = [
        p for p in staged
        if p.endswith(".py") and os.path.isfile(os.path.join(root, p))
    ]
    violations.extend(_compile_errors(pyfiles, root))

    ruff = _resolve_ruff() if pyfiles else None
    if pyfiles and ruff is None:
        # Fail OPEN, never SILENT. Blocking every commit on a machine without
        # ruff would wedge a fresh clone; passing without a word is how a
        # net-new finding reaches CI unannounced. CI's `ruff check .` is the
        # backstop, so say the half did not run and let the commit through.
        sys.stderr.write(
            "precommit_gate WARNING: no working ruff found - the net-new ruff "
            "half did NOT run on this commit.\n  Tried: "
            + " | ".join(" ".join(c) for c in _ruff_candidates())
            + "\n  Install it (pip install -r requirements-dev.txt) or CI is "
            "your only lint gate.\n"
        )
    if pyfiles and ruff is not None:
        proc = subprocess.run(
            [*ruff, "check", "--output-format=json", *pyfiles],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=_NO_WINDOW,
        )
        try:
            findings = json.loads(proc.stdout) if proc.stdout.strip() else []
        except ValueError:
            # ruff answered --version but could not lint (bad config, crash).
            # Same rule as above: pass, but not in silence.
            findings = []
            sys.stderr.write(
                "precommit_gate WARNING: ruff produced no parseable JSON - the "
                "net-new ruff half did NOT run.\n  "
                + (proc.stderr or "").strip()[:400]
                + "\n"
            )
        root_slash = root.replace("\\", "/").rstrip("/")
        for f in findings:
            fn = (f.get("filename") or "").replace("\\", "/")
            rel = fn[len(root_slash) + 1:] if fn.startswith(root_slash) else fn
            row = ((f.get("location") or {}).get("row")) or 0
            ranges = staged.get(rel, staged.get(fn, {})).get("ranges", [])
            if any(a <= row <= b for a, b in ranges):
                violations.append(
                    f"  {rel}:{row}  ruff {f.get('code', '?')}: {f.get('message', '')}"
                )

    if violations:
        return _report(violations, "net-new violations in staged files:")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    # A leading --expect-count N modifies whichever scan mode follows. Parsed
    # first so the mode flags below keep consuming argv exactly as before.
    expect: int | None = None
    if args and args[0] == "--expect-count":
        if len(args) < 2:
            sys.stderr.write("precommit_gate: --expect-count needs an integer\n")
            return 1
        try:
            expect = int(args[1])
        except ValueError:
            sys.stderr.write(
                f"precommit_gate: --expect-count needs an integer, got {args[1]!r}\n"
            )
            return 1
        args = args[2:]

    # Explicit flags rather than sniffing argv shape, so each hook body reads
    # as a statement of what it is asking for.
    if args and args[0] == "--message-file":
        if len(args) < 2:
            sys.stderr.write("precommit_gate: --message-file needs a path\n")
            return 1
        return _check_message_file(args[1])
    if args and args[0] == "--scan-tracked":
        if len(args) < 2:
            sys.stderr.write("precommit_gate: --scan-tracked needs source|docs\n")
            return 1
        return _check_scan_tracked(args[1], expect_count=expect)
    if args and args[0] == "--list-tracked":
        if len(args) < 2:
            sys.stderr.write("precommit_gate: --list-tracked needs source|docs|all\n")
            return 1
        return _list_tracked(args[1])
    if args and args[0] == "--scan-files-from0":
        if len(args) < 2:
            sys.stderr.write("precommit_gate: --scan-files-from0 needs a list path\n")
            return 1
        paths = _paths_from_nul_file(args[1])
        if paths is None:
            sys.stderr.write(
                f"precommit_gate BLOCKED - could not read the path list "
                f"{args[1]!r}.\n  Fail CLOSED: a sweep whose input list is "
                "missing has not run.\n"
            )
            return 1
        return _check_scan_files(paths, expect_count=expect)
    if args and args[0] == "--scan-files":
        return _check_scan_files(args[1:], expect_count=expect)
    if args:
        sys.stderr.write(
            f"precommit_gate: unknown argument {args[0]!r}\n"
            "  usage: precommit_gate.py                      (staged mode, "
            "command string on stdin)\n"
            "         precommit_gate.py --message-file PATH\n"
            "         precommit_gate.py [--expect-count N] --scan-files PATH...\n"
            "         precommit_gate.py [--expect-count N] --scan-files-from0 LISTFILE\n"
            "         precommit_gate.py [--expect-count N] --scan-tracked source|docs\n"
            "         precommit_gate.py --list-tracked source|docs|all\n"
        )
        return 1

    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    # A PowerShell pipe prepends a UTF-8 BOM; json.loads rejects it and the
    # raw-string fallback then never regex-matches, which is a SILENT pass.
    raw = raw.lstrip(chr(0xFEFF)).strip()
    try:
        # Accepts a structured hook payload as well as a bare command string.
        command = (json.loads(raw).get("tool_input") or {}).get("command", "")
    except (ValueError, AttributeError):
        command = raw
    if not _is_commit(command):
        return 0
    return _check_staged(command)


if __name__ == "__main__":
    sys.exit(main())
