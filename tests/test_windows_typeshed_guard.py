"""Windows-only names must sit where mypy PRUNES them on a non-Windows host.

WHY THIS TEST EXISTS. typeshed marks `ctypes.windll`, `ctypes.WinDLL` and the
whole `ctypes.wintypes` module as `sys.platform == "win32"` only. mypy resolves
`sys.platform` against its CONFIGURED platform, which defaults to the host it
runs on. Local runs here are Windows and see those names; CI runs mypy on Linux
and does not. So a file can be green on this machine and red in CI, and the
local run cannot reproduce the failure at all. Measured against CI run
34316023763:

    tools/screen_capture.py:127: error: Module has no attribute "windll"
    tools/first_run_capture.py:134: error: Name "wintypes" is not defined
    tools/first_run_capture.py:136: error: Name "wintypes" is not defined
    tools/first_run_capture.py:137: error: Name "wintypes" is not defined

Both shapes appear there, and the second is instructive: `first_run_capture.py`
already wrapped its IMPORT in `if sys.platform == "win32":`, which is why it has
no attr-defined error - but the USES stayed at module scope where the guarded
import never bound the name on Linux. Guarding the import alone converted one
error shape into another rather than removing it. The property this test grades
is therefore about the USES, not only the imports.

WHY NOT A `# type: ignore`. `mypy.ini` sets `warn_unused_ignores = True`. An
ignore that is needed on Linux is UNUSED on Windows, so it would turn the local
run red in exchange for turning CI green. There is no ignore comment that is
correct on both platforms.

WHAT COUNTS AS PRUNED. mypy narrows on `sys.platform` at statement level:

  - everything inside `if sys.platform == "win32":` is unreachable elsewhere;
  - everything after `if sys.platform != "win32": return`  (or `raise`, or
    `continue`/`break` in a loop) is likewise unreachable elsewhere, which is
    what makes a function-local import after such an early return safe.

NARROWING SUPPRESSES attr-defined BUT NOT name-defined, AND THE CI RUN PROVES
IT. In `first_run_capture.py`, `ctypes.WinDLL(...)` on line 133 and
`wintypes.HANDLE` on line 134 sit in the SAME function, both after the same
`if sys.platform != "win32": return None` on line 126. CI reported line 134 and
said nothing about line 133. So an unresolvable ATTRIBUTE on a reachable object
is a type-check-time error that narrowing removes, while an unbound NAME is a
semantic-analysis error that narrowing does not remove: the module-level
`if sys.platform == "win32": import ctypes.wintypes as wintypes` never bound the
name on Linux, and no amount of downstream narrowing invents a binding.

The checker below therefore carries TWO flags down each statement list. A
`ctypes.<win32 attr>` reference only needs to be in a pruned region. A
`wintypes` name reference additionally needs a BINDING mypy can still see on
Linux, which in practice means a function-local import in the same scope, or a
use inside the very same guarded block that holds the import.

A TERNARY IS NOT A GUARD. `ctypes.windll.user32 if sys.platform == "win32" else
None` still evaluates the attribute expression as far as the type checker is
concerned; mypy prunes STATEMENTS, not conditional expression arms. That exact
shape was the `screen_capture.py:127` failure, so the checker below must flag it
and one of the positive controls pins that it does.

GRADED AS A PROPERTY, PARSED WITH `ast`. A regex over a text window would only
ever find the shapes its author already thought of, and could not distinguish a
guarded use from an unguarded one on an adjacent line. The checker walks the
tree and carries a guarded/unguarded flag down each statement list.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The two files CI named. Both are Windows-only tools that must still be
# type-checkable on Linux because `tools/` is a `files=` root in mypy.ini.
GUARDED_FILES = [
    REPO_ROOT / "tools" / "screen_capture.py",
    REPO_ROOT / "tools" / "first_run_capture.py",
]

# `ctypes` attributes typeshed gates behind `sys.platform == "win32"`. Not the
# complete list - it is the set this tree actually touches plus the near
# neighbours a future edit is most likely to reach for.
WIN32_CTYPES_ATTRS = frozenset({
    "windll",
    "oledll",
    "WinDLL",
    "OleDLL",
    "WINFUNCTYPE",
    "WinError",
    "FormatError",
    "GetLastError",
    "get_last_error",
    "set_last_error",
    "HRESULT",
})


# ---------------------------------------------------------------------------
# Recognising a platform test
# ---------------------------------------------------------------------------


def _is_sys_platform(node: ast.AST) -> bool:
    """True for `sys.platform`, the only form mypy narrows on."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "platform"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _is_win32_str(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == "win32"


def platform_test_kind(test: ast.AST) -> str | None:
    """Classify an `if` test as a Windows platform test.

    Returns "eq" when the test is true ON Windows (`sys.platform == "win32"`,
    either operand order, or `sys.platform.startswith("win")`), "ne" when it is
    true OFF Windows (`sys.platform != "win32"`), and None otherwise.
    """
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        left, right = test.left, test.comparators[0]
        pair_matches = (
            (_is_sys_platform(left) and _is_win32_str(right))
            or (_is_win32_str(left) and _is_sys_platform(right))
        )
        if pair_matches:
            if isinstance(test.ops[0], ast.Eq):
                return "eq"
            if isinstance(test.ops[0], ast.NotEq):
                return "ne"
        return None
    if (
        isinstance(test, ast.Call)
        and isinstance(test.func, ast.Attribute)
        and test.func.attr == "startswith"
        and _is_sys_platform(test.func.value)
        and len(test.args) == 1
        and isinstance(test.args[0], ast.Constant)
        and isinstance(test.args[0].value, str)
        and test.args[0].value.startswith("win")
    ):
        return "eq"
    return None


def _terminates(body: list[ast.stmt]) -> bool:
    """True when the branch cannot fall through to the statements after it.

    That is what promotes the REST of the enclosing statement list to guarded:
    after `if sys.platform != "win32": return None`, mypy treats everything
    below as unreachable on Linux.
    """
    if not body:
        return False
    last = body[-1]
    return isinstance(last, (ast.Return, ast.Raise, ast.Continue, ast.Break))


# ---------------------------------------------------------------------------
# The checker
# ---------------------------------------------------------------------------


def binds_wintypes(stmt: ast.stmt) -> bool:
    """True when this statement binds the name `wintypes` in its own scope."""
    if isinstance(stmt, ast.Import):
        for alias in stmt.names:
            if alias.name == "ctypes.wintypes" and alias.asname == "wintypes":
                return True
    elif isinstance(stmt, ast.ImportFrom):
        module = stmt.module or ""
        for alias in stmt.names:
            bound = alias.asname or alias.name
            if bound == "wintypes" and module in {"ctypes", "ctypes.wintypes"}:
                return True
    return False


def _node_offence(node: ast.AST) -> str | None:
    """Name the Windows-only reference this single node makes, if any."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name == "ctypes.wintypes" or alias.name.startswith("ctypes.wintypes."):
                return "import " + alias.name
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module == "ctypes.wintypes" or module.startswith("ctypes.wintypes."):
            return "from " + module + " import ..."
        if module == "ctypes":
            for alias in node.names:
                if alias.name == "wintypes":
                    return "from ctypes import wintypes"
    elif isinstance(node, ast.Attribute):
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "ctypes"
            and node.attr in WIN32_CTYPES_ATTRS
        ):
            return "ctypes." + node.attr
    elif isinstance(node, ast.Name):
        if node.id == "wintypes" and isinstance(node.ctx, ast.Load):
            return "wintypes.*"
    return None


def _record(
    node: ast.AST,
    guarded: bool,
    bound: bool,
    offences: list[tuple[int, str]],
) -> None:
    what = _node_offence(node)
    if what is None:
        return
    # A `wintypes` name reference fails on Linux whenever no binding survives
    # there, whether or not the reference itself sits in a pruned region. Every
    # other shape is a type-check-time error that narrowing does suppress.
    if what == "wintypes.*":
        if not bound:
            offences.append((getattr(node, "lineno", 0), what))
        return
    if not guarded:
        offences.append((getattr(node, "lineno", 0), what))


def _scan_expr(
    node: ast.AST,
    guarded: bool,
    bound: bool,
    offences: list[tuple[int, str]],
) -> None:
    for sub in ast.walk(node):
        _record(sub, guarded, bound, offences)


def _scan_stmt(
    stmt: ast.stmt,
    guarded: bool,
    bound: bool,
    offences: list[tuple[int, str]],
) -> None:
    _record(stmt, guarded, bound, offences)
    for _field, value in ast.iter_fields(stmt):
        if isinstance(value, list):
            if value and all(isinstance(item, ast.stmt) for item in value):
                _scan_stmt_list(value, guarded, bound, offences)
                continue
            if value and all(isinstance(item, ast.excepthandler) for item in value):
                for handler in value:
                    if handler.type is not None:
                        _scan_expr(handler.type, guarded, bound, offences)
                    _scan_stmt_list(handler.body, guarded, bound, offences)
                continue
            for item in value:
                if isinstance(item, ast.AST):
                    _scan_expr(item, guarded, bound, offences)
        elif isinstance(value, ast.AST):
            _scan_expr(value, guarded, bound, offences)


def _scan_stmt_list(
    stmts: list[ast.stmt],
    guarded: bool,
    bound: bool,
    offences: list[tuple[int, str]],
) -> None:
    guarded_rest = guarded
    bound_rest = bound
    for stmt in stmts:
        if isinstance(stmt, ast.If):
            kind = platform_test_kind(stmt.test)
            if kind == "eq":
                # The binding made inside this block is visible INSIDE it and
                # nowhere after it - that is the whole first_run_capture.py bug.
                _scan_stmt_list(stmt.body, True, bound_rest, offences)
                _scan_stmt_list(stmt.orelse, guarded_rest, bound_rest, offences)
                continue
            if kind == "ne":
                _scan_stmt_list(stmt.body, guarded_rest, bound_rest, offences)
                _scan_stmt_list(stmt.orelse, True, bound_rest, offences)
                if _terminates(stmt.body):
                    guarded_rest = True
                continue
        _scan_stmt(stmt, guarded_rest, bound_rest, offences)
        if binds_wintypes(stmt):
            bound_rest = True


def unguarded_win32_refs(source: str) -> list[tuple[int, str]]:
    """Every Windows-only reference that mypy would NOT prune on Linux."""
    offences: list[tuple[int, str]] = []
    _scan_stmt_list(ast.parse(source).body, False, False, offences)
    return sorted(offences)


def all_win32_refs(source: str) -> list[tuple[int, str]]:
    """Every Windows-only reference, guarded or not.

    The survivors arm. A sweep that satisfies `unguarded_win32_refs == []` by
    deleting all the Windows code would be a false pass, so the real files are
    also asserted to still CONTAIN Windows-only references.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        what = _node_offence(node)
        if what is not None:
            found.append((getattr(node, "lineno", 0), what))
    return sorted(found)


# ---------------------------------------------------------------------------
# Positive controls - hand-typed sources that MUST be flagged
# ---------------------------------------------------------------------------

OFFENDING_SOURCES: dict[str, str] = {
    "bare-module-import-as": (
        "import ctypes\n"
        "import ctypes.wintypes as wintypes\n"
    ),
    "bare-module-import-plain": (
        "import ctypes.wintypes\n"
    ),
    "from-ctypes-import-wintypes": (
        "from ctypes import wintypes\n"
    ),
    "from-wintypes-import-name": (
        "from ctypes.wintypes import HWND\n"
    ),
    "module-level-windll-attr": (
        "import ctypes\n"
        "user32 = ctypes.windll.user32\n"
    ),
    # The exact screen_capture.py:127 shape. mypy prunes STATEMENTS; a
    # conditional expression is not a statement, so this is still checked.
    "ternary-is-not-a-guard": (
        "import ctypes\n"
        "import sys\n"
        "user32 = ctypes.windll.user32 if sys.platform == 'win32' else None\n"
    ),
    "windll-inside-unguarded-function": (
        "import ctypes\n"
        "def f():\n"
        "    return ctypes.WinDLL('kernel32')\n"
    ),
    # The first_run_capture.py shape: the import IS guarded, the uses are not.
    "guarded-import-unguarded-use": (
        "import ctypes\n"
        "import sys\n"
        "if sys.platform == 'win32':\n"
        "    import ctypes.wintypes as wintypes\n"
        "def f(k):\n"
        "    k.CreateFileW.restype = wintypes.HANDLE\n"
        "    return k\n"
    ),
    # Guard present but pointing the wrong way: the early return fires ON
    # Windows, so the tail is the branch mypy keeps on Linux.
    "inverted-early-return": (
        "import ctypes\n"
        "import sys\n"
        "def f():\n"
        "    if sys.platform == 'win32':\n"
        "        return None\n"
        "    return ctypes.windll.user32\n"
    ),
    # An early return that does not terminate cannot promote the tail.
    "non-terminating-early-guard": (
        "import ctypes\n"
        "import sys\n"
        "def f():\n"
        "    if sys.platform != 'win32':\n"
        "        pass\n"
        "    return ctypes.windll.user32\n"
    ),
    # The measured first_run_capture.py:134 shape. The use IS inside a region
    # mypy prunes, and CI reported it anyway, because the module-level guard
    # deleted the only binding. Sibling line 133 - `ctypes.WinDLL(...)`, same
    # function, same guard - drew no error, which is why only the name is
    # flagged here and not the attribute above it.
    "guarded-import-with-correctly-guarded-use": (
        "import ctypes\n"
        "import sys\n"
        "if sys.platform == 'win32':\n"
        "    import ctypes.wintypes as wintypes\n"
        "def f():\n"
        "    if sys.platform != 'win32':\n"
        "        return None\n"
        "    k = ctypes.WinDLL('kernel32')\n"
        "    k.CreateFileW.restype = wintypes.HANDLE\n"
        "    return k\n"
    ),
    "unguarded-use-in-except-handler": (
        "import ctypes\n"
        "def f():\n"
        "    try:\n"
        "        return 1\n"
        "    except OSError:\n"
        "        return ctypes.windll.user32\n"
    ),
    "unguarded-use-in-default-argument": (
        "import ctypes\n"
        "def f(lib=ctypes.windll):\n"
        "    return lib\n"
    ),
}

# ---------------------------------------------------------------------------
# Negative controls - shapes that mypy DOES prune and that must stay silent
# ---------------------------------------------------------------------------

CLEAN_SOURCES: dict[str, str] = {
    "module-level-eq-guard": (
        "import ctypes\n"
        "import sys\n"
        "if sys.platform == 'win32':\n"
        "    import ctypes.wintypes as wintypes\n"
        "    _user32 = ctypes.windll.user32\n"
        "    _user32.GetForegroundWindow.restype = wintypes.HWND\n"
    ),
    "function-local-after-early-return": (
        "import ctypes\n"
        "import sys\n"
        "def f():\n"
        "    if sys.platform != 'win32':\n"
        "        return None\n"
        "    import ctypes.wintypes as wintypes\n"
        "    k = ctypes.WinDLL('kernel32')\n"
        "    k.CreateFileW.restype = wintypes.HANDLE\n"
        "    return k\n"
    ),
    "function-local-after-early-raise": (
        "import ctypes\n"
        "import sys\n"
        "def f():\n"
        "    if sys.platform != 'win32':\n"
        "        raise RuntimeError('windows only')\n"
        "    return ctypes.windll.user32\n"
    ),
    "ne-guard-else-branch": (
        "import ctypes\n"
        "import sys\n"
        "def f():\n"
        "    if sys.platform != 'win32':\n"
        "        return None\n"
        "    else:\n"
        "        return ctypes.windll.user32\n"
    ),
    "startswith-guard": (
        "import ctypes\n"
        "import sys\n"
        "if sys.platform.startswith('win'):\n"
        "    _u = ctypes.windll.user32\n"
    ),
    "reversed-operand-order": (
        "import ctypes\n"
        "import sys\n"
        "if 'win32' == sys.platform:\n"
        "    _u = ctypes.windll.user32\n"
    ),
    "no-ctypes-at-all": (
        "import json\n"
        "def f():\n"
        "    return json.dumps({'wintypes': 1})\n"
    ),
    # `wintypes` as a string key or as somebody else's attribute is not a Load
    # of the module name and must not be flagged - this is the arm that stops
    # the checker from degrading into a substring search.
    "wintypes-as-a-string-and-a-foreign-attribute": (
        "def f(cfg):\n"
        "    return {'wintypes': cfg.wintypes, 'windll': cfg.windll}\n"
    ),
    # A ctypes attribute that typeshed does NOT gate behind win32 stays legal
    # anywhere. Flagging this would make the checker a `ctypes.` blocklist.
    "cross-platform-ctypes-attribute": (
        "import ctypes\n"
        "_INVALID = ctypes.c_void_p(-1).value\n"
        "def f():\n"
        "    return ctypes.create_unicode_buffer(8)\n"
    ),
}


# ---------------------------------------------------------------------------
# The arms
# ---------------------------------------------------------------------------


def test_positive_controls_are_flagged() -> None:
    """Non-vacuity: the detector fires on every hand-typed offending shape."""
    missed = [name for name, src in OFFENDING_SOURCES.items() if not unguarded_win32_refs(src)]
    assert missed == [], f"checker failed to flag offending shapes: {missed}"


def test_negative_controls_are_silent() -> None:
    """The survivors arm: legitimate guarded shapes must not be flagged."""
    wrong = {
        name: unguarded_win32_refs(src)
        for name, src in CLEAN_SOURCES.items()
        if unguarded_win32_refs(src)
    }
    assert wrong == {}, f"checker flagged correctly guarded shapes: {wrong}"


def test_ternary_guard_is_not_accepted_as_a_guard() -> None:
    """Pinned separately because it is the exact CI failure that was missed."""
    src = (
        "import ctypes\n"
        "import sys\n"
        "u = ctypes.windll.user32 if sys.platform == 'win32' else None\n"
    )
    refs = unguarded_win32_refs(src)
    assert [what for _line, what in refs] == ["ctypes.windll"]


def test_pruned_attribute_and_unbound_name_are_told_apart() -> None:
    """The distinction CI measured: attr-defined is narrowed away, name-defined is not.

    Same function, same early return: `ctypes.WinDLL` must NOT be flagged and
    `wintypes.HANDLE` must be, because the module-level guard left no binding.
    """
    refs = unguarded_win32_refs(OFFENDING_SOURCES["guarded-import-with-correctly-guarded-use"])
    assert [what for _line, what in refs] == ["wintypes.*"]


def test_guarded_files_exist() -> None:
    for path in GUARDED_FILES:
        assert path.is_file(), f"missing: {path}"


def test_no_unguarded_windows_only_refs() -> None:
    """The gate. Every Windows-only name in these files must be prunable."""
    report: dict[str, list[tuple[int, str]]] = {}
    for path in GUARDED_FILES:
        refs = unguarded_win32_refs(path.read_text(encoding="utf-8"))
        if refs:
            report[path.name] = refs
    assert report == {}, (
        "Windows-only names outside a sys.platform guard - mypy on Linux will "
        f"fail on these: {report}"
    )


def test_guarded_files_still_use_windows_apis() -> None:
    """The other half of the sweep: do not pass by deleting the subject."""
    for path in GUARDED_FILES:
        refs = all_win32_refs(path.read_text(encoding="utf-8"))
        assert refs, (
            f"{path.name} no longer references any Windows-only ctypes name; "
            "the guard test above would pass vacuously"
        )
