#!/bin/sh
# ResinCompute - interpreter selection for the .githooks/ shims.
#
# SOURCED, never executed:
#
#     . "$ROOT/scripts/hook_python.sh"
#     if TEST_PY="$(resin_pick_python pytest)"; then ...
#
# WHY THIS FILE EXISTS
# --------------------
# All three shims carried an identical private copy of:
#
#     PY="${PYTHON:-python3}"
#     if ! command -v "$PY" >/dev/null 2>&1; then
#         PY=python
#     fi
#
# `command -v` answers "does a file by that name exist on PATH", which is not
# the question a hook needs answered. MEASURED on the operator's Windows box,
# 2026-09-06: `python3` resolves to the Microsoft Store app-execution alias
# under AppData/Local/Microsoft/WindowsApps, which redirects to
# AppData/Local/Python/pythoncore-3.14-64/python.exe - an interpreter carrying
# NEITHER ruff NOR pytest. The lookup SUCCEEDED, so the fallback never fired,
# and the plain `python` on the same PATH
# (AppData/Local/Programs/Python/Python314/python.exe), which carries both, was
# never reached. Every push printed
#
#     pre-push WARNING: ruff not importable - the lint half did NOT run.
#     pre-push WARNING: pytest not importable - the suites did NOT run.
#     pre-push: OK
#
# and exited 0. The hook fails OPEN by design and it did say so, so nothing was
# silent - but the pre-push gate had never once actually run on that machine.
#
# EXISTENCE IS NOT CAPABILITY. Probe for what the caller is about to use.
#
# ONE COPY, SHARED. Three private copies of a selector is the shape that let a
# sibling repo's tracked and active hooks drift until three guards silently
# stopped running. The hooks source this file instead of restating it.
#
# CONSTRAINTS. This is read by a POSIX `sh`: function definitions only, no side
# effects at source time, 7-bit ASCII, and LF endings - a single CR byte here
# breaks all three hooks at once, which is why `.gitattributes` pins `*.sh` to
# eol=lf and tests/test_line_endings.py grades it.


# The candidate interpreters, in probe order, space separated on one line.
# An explicit $PYTHON leads. Callers print this when they fail open, so the
# reader is told what was tried rather than only what did not work.
resin_python_candidates() {
    printf '%s' "${PYTHON:+$PYTHON }python3 python py"
}


# resin_pick_python [module...]
#
# Echo the first candidate that can IMPORT every named module, and return 0.
#
# With no module named, the first candidate that merely RUNS qualifies. That is
# what pre-commit and commit-msg need: the scripts they drive are stdlib-only,
# so a clone without dev deps must still get its glyph and py_compile gates.
#
# Echo nothing and return 1 when no candidate qualifies. The caller decides what
# that means - pre-push fails OPEN on it (and says which half did not run),
# while the commit-time gates fall back to a literal so they fail CLOSED rather
# than passing a commit they never scanned.
resin_pick_python() {
    # Build one probe expression for the whole list, so a candidate has to
    # satisfy every requirement at once rather than one of them.
    _rp_code=''
    for _rp_mod in "$@"; do
        if [ -z "$_rp_code" ]; then
            _rp_code="import $_rp_mod"
        else
            _rp_code="$_rp_code;import $_rp_mod"
        fi
    done
    [ -n "$_rp_code" ] || _rp_code='pass'

    for _rp_py in ${PYTHON:+"$PYTHON"} python3 python py; do
        # Existence first, purely to keep the probe quiet for a name that is
        # not installed at all. It decides nothing on its own - that was the
        # whole defect.
        command -v "$_rp_py" >/dev/null 2>&1 || continue
        "$_rp_py" -c "$_rp_code" >/dev/null 2>&1 || continue

        if [ -n "${PYTHON:-}" ] && [ "$_rp_py" != "$PYTHON" ]; then
            # Passing over an explicit override is the operator not getting
            # what they asked for. Fail open on it, never silently.
            echo "hooks: PYTHON=$PYTHON cannot run '$_rp_code'" >&2
            echo "  using $_rp_py instead." >&2
        fi
        printf '%s\n' "$_rp_py"
        return 0
    done
    return 1
}
