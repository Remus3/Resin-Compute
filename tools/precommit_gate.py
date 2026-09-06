#!/usr/bin/env python3
"""Commit-time hygiene gate: banned glyphs + NET-NEW ruff findings.

Ported from Riot Commander's tools/precommit_gate.py. Three modes, and the
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

     Riot Commander measured the consequence of missing that on 2026-07-26:
     while the gate was invoked only from pre-commit, the staged-content and
     ruff halves still fired - so the gate LOOKED healthy - and a commit whose
     SUBJECT carried a U+2014 em-dash landed completely clean.

  3. --scan-files <path>... mode. Scans whole files, not just added lines.
     Used by .github/workflows/docs-guards.yml over tracked .md, and by hand
     for a drift sweep. This is the only mode that does not consult git.

EXIT CODES. Any finding exits 1 (SPEC_SCAFFOLD / build contract). Riot
Commander's copy exits 2 because it doubles as a Claude Code PreToolUse hook,
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
# data/cache/ and data/external/ hold FETCHED third-party payloads. Character
# and item names arrive from upstream carrying whatever codepoints upstream
# authored; this repo did not write them and cannot fix them, so flagging them
# would block a correct cache refresh - and a gate that blocks correct work is
# one people learn to bypass with --no-verify.
#
# data/fixtures/ is deliberately NOT exempt. Those are hand-authored minimal
# test fixtures (SPEC_SCAFFOLD section 4), which makes them authored content.
_ASCII_EXEMPT_PARTS = ("logs/", "__pycache__/", ".git/")
_ASCII_EXEMPT_SUFFIXES = (
    ".log", ".jsonl", ".pyc", ".png", ".jpg", ".jpeg", ".ico", ".zip", ".gz",
)
_ASCII_EXEMPT_PREFIXES = ("data/cache/", "data/external/")


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


def _git(args: list[str], root: str | None) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=root or None,
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=_NO_WINDOW,
        )
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


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


def _staged_added(root: str) -> dict[str, dict]:
    """Return {path: {"ranges": [(start, end)...], "lines": [(lineno, text)...]}}.

    Only ADDED lines and their line ranges - the gate never judges a line this
    commit did not write.
    """
    diff = _git(["diff", "--cached", "--unified=0", "--no-color"], root)
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

    The catch-all is not padding. Riot Commander's gate held exactly six
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
    those do not share an interpreter. Riot Commander hardcoded sys.executable
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


def _check_scan_files(paths: list[str]) -> int:
    """--scan-files entry point: whole-file glyph scan, reported as file:line.

    Whole-file rather than added-lines-only, because CI has no staged diff to
    consult. Used by docs-guards.yml over tracked .md.
    """
    violations: list[str] = []
    scanned = 0
    for p in paths:
        fp = pathlib.Path(p)
        if _ascii_exempt(p):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            sys.stderr.write(f"precommit_gate WARNING: skipped {p} ({exc})\n")
            continue
        scanned += 1
        for i, ln in enumerate(text.splitlines(), start=1):
            hits = _glyph_hits(ln, p)
            if hits:
                violations.append(f"  {p}:{i}  banned glyph: {', '.join(hits)}")
    if violations:
        return _report(violations, f"banned glyph in {len(violations)} scanned line(s):")
    print(f"precommit_gate: {scanned} file(s) scanned, 7-bit ASCII clean")
    return 0


def _check_staged(command: str) -> int:
    root = (
        _root_from_command(command)
        or _git(["rev-parse", "--show-toplevel"], os.getcwd()).strip()
        or os.getcwd()
    )
    staged = _staged_added(root)
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

    # Explicit flags rather than sniffing argv shape, so each hook body reads
    # as a statement of what it is asking for.
    if args and args[0] == "--message-file":
        if len(args) < 2:
            sys.stderr.write("precommit_gate: --message-file needs a path\n")
            return 1
        return _check_message_file(args[1])
    if args and args[0] == "--scan-files":
        return _check_scan_files(args[1:])
    if args:
        sys.stderr.write(
            f"precommit_gate: unknown argument {args[0]!r}\n"
            "  usage: precommit_gate.py                      (staged mode, "
            "command string on stdin)\n"
            "         precommit_gate.py --message-file PATH\n"
            "         precommit_gate.py --scan-files PATH...\n"
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
