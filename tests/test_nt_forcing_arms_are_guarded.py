"""A test that forces `os.name` to "nt" must say what protects it off Windows.

THE OUTAGE THIS EXISTS TO STOP REPEATING. GitHub CI (ubuntu-latest, Python
3.11.16) was red for five consecutive pushes. In Python 3.11
`pathlib.Path.__new__` selects `WindowsPath` when `os.name == "nt"` and raises
`NotImplementedError: cannot instantiate 'WindowsPath' on your system` on a
POSIX host. Three arms in `tests/test_hook_interpreter.py` forced `os.name` to
"nt" and then reached a bare `Path(...)` inside that forced window, so they
EXPLODED on Linux while passing on the operator's Windows box. Nothing in the
tree said that forcing `os.name` carries an obligation, so the next arm to do
it would have re-opened the same hole.

WHAT THIS GUARD CLAIMS, AND WHAT IT DOES NOT.

It claims: every `os.name` -> "nt" forcing site under `tests/` is either
(a) inside a test whose enclosing function or module carries a non-Windows
skip, or (b) inside a module this file's HAND-TYPED allowlist records as
measured pathlib-clean, with the measurement written beside it.

It does NOT claim the allowlisted modules are still pathlib-clean. That is a
measurement, not a derivation, and it is recorded below with its date so a
reader can re-measure it rather than trust it. The allowlist is deliberately
hand-typed and deliberately small; growing it is a decision someone has to
make on purpose.

WHY `ast` AND NOT A REGEX. A text window cannot tell a call from a docstring
that mentions one, and `tests/test_report_renderability.py` mentions the exact
call shape in its module docstring. A regex sweep would have flagged prose.

WHY THE MATCHER REFUSES TO GUESS. When a `setattr` call names `os.name` but the
value is not a plain string literal, this file reports it as UNPARSEABLE and
FAILS. Widening the matcher until the red goes away would convert an unknown
into a silent pass, which is the failure mode the guard exists to prevent.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

TESTS_DIR = Path(__file__).resolve().parent

# NON-VACUITY FLOOR. `assert not offenders` is trivially true over an empty
# scan - a broken walker, a renamed directory or a parse that silently yielded
# nothing would all read as a pass. Seven is what was standing when this guard
# was written (four in test_hook_gate.py, three in test_hook_interpreter.py),
# and the floor is a floor: adding arms is fine, losing them is not.
_MIN_FORCING_SITES = 7

# THE HAND-TYPED ALLOWLIST. Key is the module basename under tests/; the value
# is the MEASUREMENT that earned it, not a justification.
_MEASURED_PATHLIB_CLEAN: dict[str, str] = {
    "test_hook_gate.py": (
        "measured 2026-09-09: each nt-forcing arm here patches subprocess.run to "
        "return rc=3 or raise OSError, so _classify_exec_path returns at its "
        "returncode != 0 branch BEFORE it reaches root = Path(text), and its "
        "probe = Path.is_dir is class attribute access rather than construction - "
        "no pathlib.Path is instantiated inside the forced window"
    ),
}


class Site(NamedTuple):
    """One place where `os.name` is set to "nt"."""

    module: str
    lineno: int
    protected: bool
    why: str


def _windows_only_condition(node: ast.expr) -> bool:
    """Is this expression exactly `os.name != "nt"`?

    Structural, not textual. A skip whose condition says something else is not
    a non-Windows skip and must not be credited as one.
    """
    if not isinstance(node, ast.Compare):
        return False
    if len(node.ops) != 1 or not isinstance(node.ops[0], ast.NotEq):
        return False
    left = node.left
    if not (isinstance(left, ast.Attribute) and left.attr == "name"
            and isinstance(left.value, ast.Name) and left.value.id == "os"):
        return False
    right = node.comparators[0]
    return isinstance(right, ast.Constant) and right.value == "nt"


def _is_skipif_call(node: ast.expr) -> ast.Call | None:
    """A `...skipif(...)` call, whatever it is spelled on."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "skipif":
        return node
    return None


def _decorator_skips_non_windows(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in func.decorator_list:
        call = _is_skipif_call(dec)
        if call is not None and call.args and _windows_only_condition(call.args[0]):
            return True
    return False


def _calls_pytest_skip(stmts: list[ast.stmt]) -> bool:
    for stmt in stmts:
        for sub in ast.walk(stmt):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "skip"):
                return True
    return False


def _body_skips_non_windows_before(
    func: ast.FunctionDef | ast.AsyncFunctionDef, lineno: int,
) -> bool:
    """An in-body `if os.name != "nt": pytest.skip(...)` guard ahead of the site.

    Only top-level statements of the function count. A guard nested inside a
    loop or another branch is conditional, and a conditional skip does not
    protect an unconditional forcing call below it.
    """
    for stmt in func.body:
        if stmt.lineno >= lineno:
            break
        if isinstance(stmt, ast.If) and _windows_only_condition(stmt.test) and _calls_pytest_skip(stmt.body):
            return True
    return False


def _module_skips_non_windows(tree: ast.Module) -> bool:
    """A module-level `pytestmark = pytest.mark.skipif(os.name != "nt", ...)`."""
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets):
            continue
        for candidate in ([stmt.value] + list(getattr(stmt.value, "elts", []))):
            call = _is_skipif_call(candidate)
            if call is not None and call.args and _windows_only_condition(call.args[0]):
                return True
    return False


def _os_name_value_node(call: ast.Call) -> tuple[bool, ast.expr | None]:
    """Does this call set `os.name`, and to what?

    Returns (is_os_name_setattr, value_node). A value_node of None with a True
    flag means the call names os.name but carries no value argument this file
    can identify - unparseable, and the caller must fail on it.

    Both receivers in use in this tree are covered, because the receiver is not
    consulted at all: `monkeypatch.setattr(...)` and the
    `pytest.MonkeyPatch.context()` form `patch.setattr(...)` are the same shape
    once you stop caring what the object is called. The bare builtin
    `setattr(os, "name", ...)` is covered too - it does not restore, so it is
    strictly worse, and a guard that could not see it would be pointless.
    """
    func = call.func
    if isinstance(func, ast.Attribute):
        called = func.attr
    elif isinstance(func, ast.Name):
        called = func.id
    else:
        return (False, None)
    if called != "setattr":
        return (False, None)

    args = call.args
    # Two-argument target form: setattr(os, "name", value).
    if (len(args) >= 2 and isinstance(args[0], ast.Name) and args[0].id == "os"
            and isinstance(args[1], ast.Constant) and args[1].value == "name"):
        return (True, args[2] if len(args) >= 3 else None)
    # Dotted-string target form: monkeypatch.setattr("os.name", value).
    if len(args) >= 1 and isinstance(args[0], ast.Constant) and args[0].value == "os.name":
        return (True, args[1] if len(args) >= 2 else None)
    return (False, None)


def scan_source(
    module: str, source: str, allowlist: dict[str, str] | None = None,
) -> tuple[list[Site], list[str]]:
    """Find every os.name -> "nt" site in one module and say if it is protected.

    Returns (sites, unparseable). `unparseable` entries are hard failures: the
    matcher saw a call it can tell targets os.name and cannot tell what value
    it sets, and refuses to guess.
    """
    allow = _MEASURED_PATHLIB_CLEAN if allowlist is None else allowlist
    tree = ast.parse(source, filename=module)
    sites: list[Site] = []
    unparseable: list[str] = []
    module_skip = _module_skips_non_windows(tree)
    allow_reason = allow.get(module)

    def visit(node: ast.AST, enclosing: ast.FunctionDef | ast.AsyncFunctionDef | None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                visit(child, child)
                continue
            if isinstance(child, ast.Call):
                targets_os_name, value = _os_name_value_node(child)
                if targets_os_name:
                    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                        unparseable.append(
                            f"{module}:{child.lineno} sets os.name to a value this guard "
                            f"cannot read as a string literal - it will not guess"
                        )
                    elif value.value == "nt":
                        if allow_reason is not None:
                            sites.append(Site(module, child.lineno, True, f"allowlisted: {allow_reason}"))
                        elif module_skip:
                            sites.append(Site(module, child.lineno, True, "module-level non-Windows skipif"))
                        elif enclosing is not None and _decorator_skips_non_windows(enclosing):
                            sites.append(Site(module, child.lineno, True, "non-Windows skipif decorator"))
                        elif enclosing is not None and _body_skips_non_windows_before(enclosing, child.lineno):
                            sites.append(Site(module, child.lineno, True, "in-body non-Windows pytest.skip"))
                        else:
                            sites.append(Site(module, child.lineno, False, "UNPROTECTED"))
            visit(child, enclosing)

    visit(tree, None)
    return (sites, unparseable)


def scan_tests_tree() -> tuple[list[Site], list[str]]:
    sites: list[Site] = []
    unparseable: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        found, bad = scan_source(path.name, path.read_bytes().decode("utf-8"))
        sites.extend(found)
        unparseable.extend(bad)
    return (sites, unparseable)


# ---------------------------------------------------------------------------
# The guard itself.
# ---------------------------------------------------------------------------


def test_every_nt_forcing_site_under_tests_is_protected_or_measured_clean():
    """THE PRIMARY ARM, floor and judgement in the same assertion.

    A floor kept in a separate test leaves this one vacuous - `not offenders`
    over an empty scan is a pass about nothing - so the count is asserted here,
    beside the verdict it makes meaningful.
    """
    sites, unparseable = scan_tests_tree()
    assert not unparseable, (
        "the scanner met an os.name setattr it cannot read, and guessing is how a "
        "guard turns an unknown into a silent pass:\n  " + "\n  ".join(unparseable)
    )
    offenders = [s for s in sites if not s.protected]
    assert len(sites) >= _MIN_FORCING_SITES and not offenders, (
        f"scanned {len(sites)} os.name -> nt forcing sites under {TESTS_DIR} "
        f"(floor {_MIN_FORCING_SITES}), of which {len(offenders)} are unprotected.\n"
        "A site is protected by a non-Windows skip on its function or module, or by "
        "this file's hand-typed measured-pathlib-clean allowlist.\n"
        + "\n".join(f"  UNPROTECTED {s.module}:{s.lineno}" for s in offenders)
    )


def test_the_scanner_flags_bare_nt_forcing_arms_of_several_shapes():
    """POSITIVE CONTROL. Every fixture here is HAND-TYPED, never read out of the
    tree being audited - a control that consults the same source as the thing it
    grades cannot see that source be wrong.

    Three flagged shapes, three receivers/targets, so a matcher narrowed to the
    one form this tree happens to use would go red here rather than pass.
    """
    bare_monkeypatch = (
        "import os\n"
        "\n"
        "def test_bare(monkeypatch):\n"
        '    monkeypatch.setattr(os, "name", "nt")\n'
    )
    context_receiver = (
        "import os\n"
        "import pytest\n"
        "\n"
        "def test_context():\n"
        "    with pytest.MonkeyPatch.context() as patch:\n"
        '        patch.setattr(os, "name", "nt")\n'
    )
    dotted_string_target = (
        "import os\n"
        "\n"
        "def test_dotted(monkeypatch):\n"
        '    monkeypatch.setattr("os.name", "nt")\n'
    )
    for label, source in (
        ("bare monkeypatch receiver", bare_monkeypatch),
        ("MonkeyPatch.context receiver", context_receiver),
        ("dotted string target", dotted_string_target),
    ):
        sites, unparseable = scan_source("hand_typed_control.py", source, allowlist={})
        assert not unparseable, f"{label}: unexpectedly unparseable: {unparseable}"
        assert len(sites) == 1, f"{label}: expected exactly one site, got {sites}"
        assert not sites[0].protected, f"{label}: a bare nt-forcing arm was NOT flagged"


def test_the_scanner_does_not_flag_what_is_actually_protected_or_not_forcing():
    """The other half of the sweep. A guard that flags everything scores 100
    percent on the arm above by refusing to distinguish anything, so the
    legitimate neighbours are asserted to SURVIVE.
    """
    decorated = (
        "import os\n"
        "import pytest\n"
        "\n"
        '@pytest.mark.skipif(os.name != "nt", reason="windows-only branch")\n'
        "def test_decorated(monkeypatch):\n"
        '    monkeypatch.setattr(os, "name", "nt")\n'
    )
    in_body = (
        "import os\n"
        "import pytest\n"
        "\n"
        "def test_in_body(monkeypatch):\n"
        '    if os.name != "nt":\n'
        '        pytest.skip("windows-only branch")\n'
        '    monkeypatch.setattr(os, "name", "nt")\n'
    )
    module_level = (
        "import os\n"
        "import pytest\n"
        "\n"
        'pytestmark = pytest.mark.skipif(os.name != "nt", reason="windows-only file")\n'
        "\n"
        "def test_module_level(monkeypatch):\n"
        '    monkeypatch.setattr(os, "name", "nt")\n'
    )
    for label, source in (
        ("skipif decorator", decorated),
        ("in-body pytest.skip", in_body),
        ("module-level pytestmark", module_level),
    ):
        sites, unparseable = scan_source("hand_typed_control.py", source, allowlist={})
        assert not unparseable, f"{label}: unexpectedly unparseable: {unparseable}"
        assert len(sites) == 1 and sites[0].protected, f"{label}: protection not credited: {sites}"

    # NOT A FORCING SITE AT ALL. Forcing posix is the opposite direction and
    # must not be counted, or the floor above would be met by arms that are not
    # what this guard is about.
    forcing_posix = (
        "import os\n"
        "\n"
        "def test_posix(monkeypatch):\n"
        '    monkeypatch.setattr(os, "name", "posix")\n'
    )
    sites, unparseable = scan_source("hand_typed_control.py", forcing_posix, allowlist={})
    assert (sites, unparseable) == ([], []), f"a posix-forcing arm was counted: {sites} {unparseable}"

    # A SKIP CONDITION THAT SAYS SOMETHING ELSE IS NOT A NON-WINDOWS SKIP.
    wrong_condition = (
        "import os\n"
        "import sys\n"
        "import pytest\n"
        "\n"
        '@pytest.mark.skipif(sys.platform == "darwin", reason="not about os.name")\n'
        "def test_wrong(monkeypatch):\n"
        '    monkeypatch.setattr(os, "name", "nt")\n'
    )
    sites, _ = scan_source("hand_typed_control.py", wrong_condition, allowlist={})
    assert len(sites) == 1 and not sites[0].protected, (
        f"an unrelated skipif was credited as a non-Windows skip: {sites}"
    )


def test_the_scanner_refuses_to_guess_at_a_non_literal_value():
    """UNPARSEABLE IS A FAILURE, NOT A PASS. The rule this encodes: if the
    matcher cannot disambiguate a shape, the shape is unparseable and the guard
    fails on it. Widening the matcher until it returns an answer would be
    manufacturing a verdict.
    """
    non_literal = (
        "import os\n"
        "\n"
        "def test_indirect(monkeypatch, forced_name):\n"
        '    monkeypatch.setattr(os, "name", forced_name)\n'
    )
    sites, unparseable = scan_source("hand_typed_control.py", non_literal, allowlist={})
    assert sites == [], f"an unreadable value must not be classified as a site: {sites}"
    assert len(unparseable) == 1 and "will not guess" in unparseable[0], unparseable

    missing_value = (
        "import os\n"
        "\n"
        "def test_no_value(monkeypatch):\n"
        '    monkeypatch.setattr(os, "name")\n'
    )
    sites, unparseable = scan_source("hand_typed_control.py", missing_value, allowlist={})
    assert sites == [] and len(unparseable) == 1, (sites, unparseable)


def test_the_allowlist_is_load_bearing_and_not_decoration():
    """NON-VACUITY FOR THE ALLOWLIST. If test_hook_gate.py carried no nt-forcing
    sites at all, its entry would be protecting nothing and the primary arm's
    floor would be met entirely by other files. Scanning it with an EMPTY
    allowlist must therefore surface unprotected sites - that is what the entry
    is buying, and its measurement is what a reader should re-check.
    """
    target = TESTS_DIR / "test_hook_gate.py"
    assert target.is_file(), f"the allowlisted module is missing: {target}"
    source = target.read_bytes().decode("utf-8")

    without, bad_without = scan_source(target.name, source, allowlist={})
    assert not bad_without, bad_without
    assert len(without) >= 4 and all(not s.protected for s in without), (
        "test_hook_gate.py was expected to carry nt-forcing sites that only the "
        f"allowlist protects: {without}"
    )

    with_allow, bad_with = scan_source(target.name, source)
    assert not bad_with, bad_with
    assert with_allow and all(s.protected for s in with_allow), with_allow
    assert all("allowlisted" in s.why for s in with_allow), with_allow


def test_the_three_interpreter_arms_carry_a_reason_that_leads_with_the_branch():
    """THE SKIP REASON IS PART OF THE RULING. A reason saying only that pathlib
    raises would be false-implying: the primary truth is that the arm grades a
    Windows-only branch and off Windows was never exercising real behaviour.
    This pins the ORDER, not merely the presence of both halves.
    """
    from tests.test_hook_interpreter import _ORACLE_WINDOWS_ONLY_SKIP as reason

    lowered = reason.lower()
    branch_at = lowered.find("windows-only branch")
    pathlib_at = lowered.find("pathlib")
    assert branch_at != -1, f"the reason does not name the Windows-only branch: {reason}"
    assert pathlib_at != -1, f"the reason does not name pathlib: {reason}"
    assert branch_at < pathlib_at, (
        "the reason must LEAD with the Windows-only branch and name pathlib second: "
        f"{reason}"
    )
    assert "search_git_install" in reason, (
        f"the reason must name the mechanism that makes the branch Windows-only: {reason}"
    )
