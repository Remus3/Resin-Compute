"""Tests for the desktop shortcut installer.

NOTHING HERE WRITES A SHORTCUT. Every decision the script makes is a pure
function of its inputs - what the desired state is, whether the observed state
already matches it, what PowerShell text renders, what argv is built - and those
are what is graded. The one impure step is handing an argv to PowerShell, and
that is deliberately the only thing left untested.

TWO ARMS ARE ABOUT SAFETY RATHER THAN BEHAVIOUR:

- **No message may name a directory.** The Desktop sits under the user profile,
  so its path CONTAINS THE WINDOWS ACCOUNT NAME. Every refusal is fixed text
  naming a remedy, and the arm below reads the module's own parse tree rather
  than a hand-written list of message sites, because a hand-written list is what
  lets two of them drift apart.
- **PowerShell is never invoked through a shell.** Through Git Bash, MSYS path
  conversion rewrites arguments before the tool sees them. The absence of that
  spelling is pinned twice, once against the built argv and once against the raw
  source text.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts import make_shortcut

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "scripts" / "make_shortcut.py"


# ---------------------------------------------------------------------------
# Idempotence - the behaviour that was explicitly asked for
# ---------------------------------------------------------------------------


def test_an_absent_shortcut_is_created():
    action = make_shortcut.decide(observed=None, desired=_desired())
    assert action is make_shortcut.Action.CREATE


def test_a_matching_shortcut_is_left_alone():
    """The idempotent case. Running twice changes nothing and is not an error."""
    desired = _desired()
    observed = make_shortcut.ShortcutState(
        target=desired.target, arguments=desired.arguments, working_dir=desired.working_dir
    )
    assert make_shortcut.decide(observed=observed, desired=desired) is make_shortcut.Action.UNCHANGED


def test_a_differing_shortcut_is_updated_rather_than_refused():
    """Convergence, which is what idempotent means for an installer.

    Clockspeed's equivalent REFUSES here and requires --force. That is a
    defensible default and it is not the one that was asked for, so the divergence
    is deliberate and `--no-clobber` restores the stricter behaviour.
    """
    desired = _desired()
    observed = make_shortcut.ShortcutState(
        target="C:\\elsewhere\\electron.exe", arguments=desired.arguments, working_dir=desired.working_dir
    )
    assert make_shortcut.decide(observed=observed, desired=desired) is make_shortcut.Action.UPDATE


@pytest.mark.parametrize("field", ["target", "arguments", "working_dir"])
def test_any_differing_field_triggers_an_update(field):
    desired = _desired()
    observed = make_shortcut.ShortcutState(
        target=desired.target, arguments=desired.arguments, working_dir=desired.working_dir
    )
    observed = observed._replace(**{field: "something else"})
    assert make_shortcut.decide(observed=observed, desired=desired) is make_shortcut.Action.UPDATE


def test_comparison_ignores_case_and_trailing_separators_on_paths():
    """Windows paths are case-insensitive, and the COM object may hand back a
    trailing separator it was not given. Treating either as a difference would
    make the script rewrite a correct shortcut on every single run, which is the
    opposite of idempotent.
    """
    desired = _desired()
    observed = make_shortcut.ShortcutState(
        target=desired.target.upper(),
        arguments=desired.arguments,
        working_dir=desired.working_dir + "\\",
    )
    assert make_shortcut.decide(observed=observed, desired=desired) is make_shortcut.Action.UNCHANGED


def test_no_clobber_refuses_instead_of_updating():
    desired = _desired()
    observed = make_shortcut.ShortcutState(target="C:\\elsewhere.exe", arguments="", working_dir="")
    assert make_shortcut.decide(observed=observed, desired=desired, no_clobber=True) is make_shortcut.Action.REFUSE


# ---------------------------------------------------------------------------
# PowerShell rendering
# ---------------------------------------------------------------------------


def test_the_rendered_script_uses_single_quotes_throughout():
    """Load bearing at two layers.

    Inside a PowerShell single-quoted string nothing is special except the quote
    itself, so a Windows path's backslashes are literal and there is no variable
    expansion. And because the rendered text then contains no double quote, the
    Windows argument joining subprocess performs on the way to CreateProcess has
    nothing to escape and cannot mangle it.
    """
    script = make_shortcut.create_script(_desired(), "C:\\Users\\x\\Desktop\\ResinCompute.lnk")
    assert '"' not in script


def test_an_embedded_quote_is_doubled_not_escaped():
    # A backslash escape is a shell habit and is wrong here: PowerShell doubles.
    assert make_shortcut.ps_quote("it's") == "'it''s'"
    assert make_shortcut.ps_quote("plain") == "'plain'"


def test_the_argv_never_asks_for_a_shell():
    argv = make_shortcut.powershell_argv("powershell.exe", "Write-Output 1")
    assert argv[0] == "powershell.exe"
    assert "-NoProfile" in argv
    assert "-NonInteractive" in argv
    # MSYS path conversion in Git Bash rewrites arguments before the tool sees
    # them. A list argv with shell=False is immune; a command string is not.
    assert all(isinstance(part, str) for part in argv)


def test_the_source_never_spells_a_shell_invoking_call():
    """Pinned against the raw text as well as the built argv.

    A future reader hitting a quoting problem must not reach for this spelling,
    and a test that only checked the argv would not notice a new call site.
    """
    text = SOURCE.read_text(encoding="utf-8")
    assert "shell=True" not in text


def test_every_subprocess_call_passes_shell_false():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None)
        if name not in {"run", "check_output", "Popen", "call"}:
            continue
        calls += 1
        keywords = {kw.arg: kw.value for kw in node.keywords}
        assert "shell" in keywords, "a subprocess call did not state shell="
        value = keywords["shell"]
        assert isinstance(value, ast.Constant) and value.value is False
    assert calls >= 1, "the sweep found no subprocess call and is vacuous"


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------


def test_no_declared_message_names_a_directory_or_a_drive():
    """The Desktop path carries the Windows account name.

    Reads the module's own constants rather than a remembered list of sites.
    """
    for name, value in vars(make_shortcut).items():
        if not name.isupper() or not isinstance(value, str):
            continue
        assert "\\Users" not in value, f"{name} names a user directory"
        assert not any(f"{letter}:\\" in value for letter in "CDEF"), f"{name} names a drive"


def test_refusals_name_a_remedy_rather_than_a_path():
    assert "npm install" in make_shortcut.RUNTIME_MISSING
    assert make_shortcut.RUNTIME_MISSING.isascii()


def test_every_module_constant_is_seven_bit_ascii():
    for name, value in vars(make_shortcut).items():
        if name.isupper() and isinstance(value, str):
            assert value.isascii(), f"{name} carries a non-ASCII character"


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


def test_the_shortcut_file_name_defaults_and_keeps_its_suffix():
    assert make_shortcut.shortcut_file_name(None) == "ResinCompute.lnk"
    assert make_shortcut.shortcut_file_name("Custom") == "Custom.lnk"
    assert make_shortcut.shortcut_file_name("Custom.lnk") == "Custom.lnk"


def test_a_name_carrying_a_path_separator_is_refused():
    """`--name` is operator input and it names a file, never a location.

    Without this, `--name ..\\..\\startup\\x` writes outside the desktop.
    """
    for bad in ["a/b", "a\\b", "..", ".", "", "   "]:
        with pytest.raises(ValueError):
            make_shortcut.shortcut_file_name(bad)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _desired() -> make_shortcut.ShortcutState:
    return make_shortcut.ShortcutState(
        target="C:\\repo\\shell\\node_modules\\electron\\dist\\electron.exe",
        arguments=".",
        working_dir="C:\\repo\\shell",
    )
