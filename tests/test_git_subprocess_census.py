"""Arms for `tools/git_subprocess_census.py`, the AST enumeration of git shell-outs.

WHY THIS FILE EXISTS, and what defect it is pinning.

Two false-red figures were quoted in this tree - "8 red arms over 7 modules" and
a "5-module candidate list" - and both came from NAME-BASED ONE-TERM FILTERS
over the test corpus. The 5-module list was then measured and OVER-REPORTED:
only three of the five shell git at all. `tests/test_ci_history_depth.py`
executes none - its only `subprocess.run` text is a STRING LITERAL fed to a
regex - and `tests/test_guard_worktree_blindness.py` has no subprocess call at
all. A skip added to either would have been a FALSE SKIP with no defect behind
it.

The census is therefore graded on FIXTURE SOURCE STRINGS parsed in memory, so
each arm pins an INPUT rather than a shape. A gate that cannot fail passes on
both sides of a real defect, so every arm below names the source text it feeds
and the bucket that text must land in.

A DROPPED SITE IS THE WORST OUTCOME AND THE HARDEST TO SEE. A call in a
decorator expression or a default argument is not in any statement body, and a
walk that recurses into a scope node's `body` alone produces NO ROW for it. A
wrong row is arguable; a missing row is invisible. So there are arms for the
decorator and default positions on functions, nested functions, methods and
classes, and a CONSERVATION arm over a fixture with a hand-counted number of
launches asserting the three bucket counts SUM TO THAT NUMBER - the only shape
that catches a future drop rather than a future misbucketing.

THE UNRESOLVED BUCKET IS THE HONEST PART. An enumeration that silently drops
argv[0] expressions it cannot resolve has reproduced the very defect this file
exists to kill, so there are arms for a bare Name, an f-string, a `**kwargs`
splat, a rebound name and an empty sequence - each of which must land
UNRESOLVED and must NOT be quietly dropped or quietly called NOT-GIT.
"""

from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository
from tools import git_subprocess_census as census

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# FIXTURE SOURCES. Every one of these is parsed from a string, never read from
# disk, so an arm cannot pass by accident because the tree happens to look a
# certain way today.
# ---------------------------------------------------------------------------

GIT_LIST_LITERAL = "import subprocess\nsubprocess.run(['git', 'ls-files'])\n"

NON_GIT_LIST_LITERAL = "import subprocess\nsubprocess.run(['python', '-c', 'pass'])\n"

BARE_NAME_ARGV = (
    "import subprocess\n"
    "def probe(args):\n"
    "    return subprocess.run(args, check=False)\n"
)

FSTRING_ARGV = (
    "import subprocess\n"
    "def probe(exe):\n"
    "    return subprocess.run([f'{exe}', 'status'])\n"
)

MODULE_CONSTANT_ARGV = (
    "import subprocess\n"
    "GIT_LS = ['git', 'ls-files']\n"
    "def probe():\n"
    "    return subprocess.run(GIT_LS, check=True)\n"
)

LOCAL_CONSTANT_ARGV = (
    "import subprocess\n"
    "def probe():\n"
    "    argv = ['git', 'rev-parse', '--git-dir']\n"
    "    return subprocess.run(argv, check=False)\n"
)

REBOUND_NAME_ARGV = (
    "import subprocess\n"
    "def probe(flag):\n"
    "    argv = ['git', 'status']\n"
    "    if flag:\n"
    "        argv = ['hg', 'status']\n"
    "    return subprocess.run(argv)\n"
)

PARAMETER_SHADOWS_MODULE = (
    "import subprocess\n"
    "GIT_ARGV = ['git', 'log']\n"
    "def probe(GIT_ARGV):\n"
    "    return subprocess.run(GIT_ARGV)\n"
)

# The exact `tests/test_ci_history_depth.py` shape: the only `subprocess.run`
# text in the module sits INSIDE a string literal handed to a regex, and no
# process is ever launched. A name-based filter matches this file; an AST walk
# must find nothing here at all.
REGEX_STRING_SHAPE = (
    "import re\n"
    "import subprocess\n"
    "_GIT_LOG_CALL = re.compile(r'git log')\n"
    "def test_depth():\n"
    "    assert _GIT_LOG_CALL.search('subprocess.run([\"git\", \"log\", \"-n\", \"1\"])')\n"
)

NOT_SUBPROCESS_RUN = "import subprocess\nother.run(['git', 'status'])\n"

LITERAL_HEAD_CONCATENATION = (
    "import subprocess\n"
    "def probe(extra):\n"
    "    return subprocess.run(['git', 'log'] + extra)\n"
)

EVERY_LAUNCHER = (
    "import subprocess\n"
    "subprocess.run(['git', 'a'])\n"
    "subprocess.check_output(['git', 'b'])\n"
    "subprocess.check_call(['git', 'c'])\n"
    "subprocess.call(['git', 'd'])\n"
    "subprocess.Popen(['git', 'e'])\n"
)

FROM_IMPORT_ALIAS = (
    "from subprocess import check_output as grab\nout = grab(['git', 'ls-files'])\n"
)

MODULE_ALIAS = "import subprocess as sp\nsp.run(['git', 'status'])\n"

SYS_EXECUTABLE_HEAD = (
    "import subprocess\nimport sys\nsubprocess.run([sys.executable, '-m', 'pytest'])\n"
)

ABSOLUTE_GIT_EXE = (
    "import subprocess\nsubprocess.run(['C:\\\\Program Files\\\\Git\\\\bin\\\\git.exe', 'status'])\n"
)

# A WHOLE-COMMAND STRING, as passed under `shell=True`. Only the first shell
# word is the executable here - and that is the ONLY place a whitespace split is
# correct. Splitting a LIST element on whitespace turns an absolute path with a
# space in it into a false NOT-GIT, which is how the arm below was earned.
SHELL_STRING_GIT = "import subprocess\nsubprocess.run('git log -n 1', shell=True)\n"

SHELL_STRING_NOT_GIT = (
    "import subprocess\nsubprocess.run('python -c pass', shell=True)\n"
)

SHELL_STRING_QUOTED_PATH = (
    "import subprocess\n"
    "subprocess.run('\"C:\\\\Program Files\\\\Git\\\\bin\\\\git.exe\" status', shell=True)\n"
)

KEYWORD_ARGS_ARGV = "import subprocess\nsubprocess.run(args=['git', 'status'])\n"

KWARGS_SPLAT_ARGV = (
    "import subprocess\n"
    "def probe(**kw):\n"
    "    return subprocess.run(**kw)\n"
)

EMPTY_SEQUENCE_ARGV = "import subprocess\nsubprocess.run([])\n"

GATED_MODULE = (
    "import subprocess\n"
    "from tests.conftest import require_git_repository\n"
    "def probe():\n"
    "    require_git_repository()\n"
    "    return subprocess.run(['git', 'status'])\n"
)

UNGATED_MODULE = "import subprocess\nsubprocess.run(['git', 'status'])\n"

# ---------------------------------------------------------------------------
# POSITIONS THAT ARE NOT A STATEMENT BODY. Each of these was DROPPED entirely -
# no call site at all - because the walk recursed into a scope node's `body` and
# never into its decorator_list or its argument defaults.
# ---------------------------------------------------------------------------

DECORATOR_ON_FUNCTION = (
    "import subprocess\n"
    "@register(subprocess.run(['git', 'rev-parse']))\n"
    "def probe():\n"
    "    return None\n"
)

DECORATOR_ON_CLASS = (
    "import subprocess\n"
    "@deco(subprocess.run(['git', 'log']))\n"
    "class Probe:\n"
    "    pass\n"
)

DECORATOR_ON_METHOD = (
    "import subprocess\n"
    "class Probe:\n"
    "    @deco(subprocess.run(['git', 'log']))\n"
    "    def method(self):\n"
    "        return None\n"
)

NESTED_DECORATOR = (
    "import subprocess\n"
    "def outer():\n"
    "    @register(subprocess.run(['git', 'diff']))\n"
    "    def inner():\n"
    "        return None\n"
    "    return inner\n"
)

DEFAULT_ARGUMENT_ARGV = (
    "import subprocess\n"
    "def probe(out=subprocess.run(['git', 'log'])):\n"
    "    return out\n"
)

KWONLY_DEFAULT_ARGV = (
    "import subprocess\n"
    "def probe(*, out=subprocess.run(['git', 'status'])):\n"
    "    return out\n"
)

NESTED_DEFAULT_ARGUMENT_ARGV = (
    "import subprocess\n"
    "def outer():\n"
    "    def inner(out=subprocess.run(['git', 'log'])):\n"
    "        return out\n"
    "    return inner\n"
)

LAMBDA_DEFAULT_ARGV = (
    "import subprocess\n"
    "probe = lambda out=subprocess.run(['git', 'log']): out\n"
)

# A default argument is evaluated in the ENCLOSING scope at definition time, so
# the parameter of the very function being defined does NOT shadow the module
# constant of the same spelling. Walking the default with the nested scope chain
# would report a false UNRESOLVED here.
DEFAULT_RESOLVES_IN_THE_ENCLOSING_SCOPE = (
    "import subprocess\n"
    "GIT_ARGV = ['git', 'log']\n"
    "def probe(GIT_ARGV=subprocess.run(GIT_ARGV)):\n"
    "    return GIT_ARGV\n"
)

# ---------------------------------------------------------------------------
# SHELL=TRUE. Element 0 of the list is the command string on POSIX and the head
# of the joined command line on Windows, so the command is the first shell word
# of element 0 under both readings. Without shell= the same bytes name one
# executable whose name contains spaces, which is not git.
# ---------------------------------------------------------------------------

SHELL_TRUE_LIST_HEAD_GIT = (
    "import subprocess\n"
    "subprocess.run(['git log -n 1'], shell=True)\n"
)

SHELL_TRUE_LIST_HEAD_NOT_GIT = (
    "import subprocess\n"
    "subprocess.run(['python -c pass'], shell=True)\n"
)

SHELL_TRUE_LIST_QUOTED_PATH = (
    "import subprocess\n"
    "subprocess.run(['\"C:\\\\Program Files\\\\Git\\\\bin\\\\git.exe\" status'], shell=True)\n"
)

NO_SHELL_LIST_HEAD_WITH_SPACE = (
    "import subprocess\n"
    "subprocess.run(['git log -n 1'])\n"
)

SHELL_NOT_STATICALLY_KNOWN_AMBIGUOUS = (
    "import subprocess\n"
    "def probe(flag):\n"
    "    return subprocess.run(['git log -n 1'], shell=flag)\n"
)

SHELL_NOT_STATICALLY_KNOWN_UNAMBIGUOUS = (
    "import subprocess\n"
    "def probe(flag):\n"
    "    return subprocess.run(['git', 'log'], shell=flag)\n"
)

# ---------------------------------------------------------------------------
# THE UNRESOLVED FALLBACK ITSELF. `shutil.which("git")` is the most ordinary
# dynamic git argv[0] in Python. Folding the fallback into NOT-GIT turns it into
# a silent non-finding while every other arm keeps passing.
# ---------------------------------------------------------------------------

WHICH_CALL_ARGV_HEAD = (
    "import shutil\n"
    "import subprocess\n"
    "subprocess.run([shutil.which('git'), 'log'])\n"
)

WHICH_CALL_WHOLE_ARGV = (
    "import shutil\n"
    "import subprocess\n"
    "subprocess.run(shutil.which('git'))\n"
)

SUBSCRIPT_ARGV_HEAD = (
    "import subprocess\n"
    "def probe(paths):\n"
    "    return subprocess.run([paths[0], 'log'])\n"
)

SUBSCRIPT_WHOLE_ARGV = (
    "import subprocess\n"
    "def probe(cfg):\n"
    "    return subprocess.run(cfg['argv'])\n"
)

# ---------------------------------------------------------------------------
# THE CONSERVATION FIXTURE. Nine launches, counted by hand, in nine different
# positions: module statement, function decorator, module-level default, nested
# statement, nested decorator, nested default, class decorator, method
# decorator, method default. A walk that drops any position fails the SUM.
# ---------------------------------------------------------------------------

CONSERVATION_SOURCE = (
    "import subprocess\n"
    "subprocess.run(['git', 'status'])\n"
    "@register(subprocess.run(['git', 'rev-parse']))\n"
    "def top(out=subprocess.run(['git', 'log'])):\n"
    "    subprocess.run(['python', '-c', 'pass'])\n"
    "    @inner_deco(subprocess.run(argv_from_nowhere))\n"
    "    def nested(arg=subprocess.run(['git', 'diff'])):\n"
    "        return arg\n"
    "    return nested\n"
    "@class_deco(subprocess.run(['git', 'show']))\n"
    "class Probe:\n"
    "    @method_deco(subprocess.run(['hg', 'status']))\n"
    "    def method(self, out=subprocess.run(['git', 'tag'])):\n"
    "        return out\n"
)

CONSERVATION_TOTAL = 9
CONSERVATION_EXPECTED = {"GIT": 6, "NOT-GIT": 2, "UNRESOLVED": 1}



def _buckets(source: str) -> list[str]:
    return [site.bucket for site in census.census_source(source, "<fixture>")]


def _only(source: str) -> census.CallSite:
    sites = census.census_source(source, "<fixture>")
    assert len(sites) == 1, f"expected exactly one call site, got {sites!r}"
    return sites[0]


# ---------------------------------------------------------------------------
# THE GIT BUCKET
# ---------------------------------------------------------------------------


def test_git_list_literal_lands_in_the_git_bucket():
    site = _only(GIT_LIST_LITERAL)
    assert site.bucket == census.GIT
    assert site.callee == "subprocess.run"
    assert site.lineno == 2


def test_module_level_constant_bound_list_resolves_to_git():
    site = _only(MODULE_CONSTANT_ARGV)
    assert site.bucket == census.GIT, (
        "a module-level constant bound to a git argv list is statically resolvable, "
        "so leaving it UNRESOLVED under-reports the git surface"
    )


def test_function_local_constant_bound_list_resolves_to_git():
    assert _only(LOCAL_CONSTANT_ARGV).bucket == census.GIT


def test_literal_head_concatenation_resolves_to_git():
    site = _only(LITERAL_HEAD_CONCATENATION)
    assert site.bucket == census.GIT, (
        "argv[0] is a literal in the left operand of the concatenation, so the tail "
        "being dynamic does not make the head unknown"
    )


def test_absolute_windows_path_to_git_exe_resolves_to_git():
    site = _only(ABSOLUTE_GIT_EXE)
    assert site.bucket == census.GIT
    assert "git.exe" in site.argv0


def test_a_whole_command_shell_string_resolves_on_its_first_word():
    assert _only(SHELL_STRING_GIT).bucket == census.GIT
    assert _only(SHELL_STRING_NOT_GIT).bucket == census.NOT_GIT


def test_a_quoted_absolute_path_in_a_shell_string_resolves_to_git():
    site = _only(SHELL_STRING_QUOTED_PATH)
    assert site.bucket == census.GIT, (
        "a naive whitespace split cuts this at 'C:\\Program' and reports a false "
        "NOT-GIT, which is the same class of error as the name filter this census "
        "replaces"
    )


def test_keyword_args_argv_is_resolved_not_dropped():
    site = _only(KEYWORD_ARGS_ARGV)
    assert site.bucket == census.GIT, (
        "`subprocess.run(args=[...])` has no positional argument; a census that only "
        "reads call.args[0] reports this as no argv at all"
    )


def test_every_launcher_is_detected():
    sites = census.census_source(EVERY_LAUNCHER, "<fixture>")
    assert [site.callee for site in sites] == [
        "subprocess.run",
        "subprocess.check_output",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.Popen",
    ]
    assert {site.bucket for site in sites} == {census.GIT}


def test_from_import_alias_is_detected():
    site = _only(FROM_IMPORT_ALIAS)
    assert site.bucket == census.GIT
    assert site.callee == "subprocess.check_output"


def test_module_alias_is_detected():
    assert _only(MODULE_ALIAS).bucket == census.GIT


# ---------------------------------------------------------------------------
# THE NOT-GIT BUCKET
# ---------------------------------------------------------------------------


def test_non_git_list_literal_lands_in_the_not_git_bucket():
    site = _only(NON_GIT_LIST_LITERAL)
    assert site.bucket == census.NOT_GIT


def test_sys_executable_head_lands_in_the_not_git_bucket():
    site = _only(SYS_EXECUTABLE_HEAD)
    assert site.bucket == census.NOT_GIT, (
        "sys.executable is the running interpreter and can never be git; it is the "
        "only dotted name the census resolves"
    )
    assert site.argv0 == "sys.executable"


# ---------------------------------------------------------------------------
# THE UNRESOLVED BUCKET - the honest one
# ---------------------------------------------------------------------------


def test_bare_name_argv_is_unresolved_and_not_dropped():
    site = _only(BARE_NAME_ARGV)
    assert site.bucket == census.UNRESOLVED, (
        "argv is a function parameter, so argv[0] is unknowable at parse time; "
        "calling it NOT-GIT would under-report and dropping it would hide it"
    )


def test_fstring_argv_is_unresolved():
    assert _only(FSTRING_ARGV).bucket == census.UNRESOLVED


def test_rebound_name_is_unresolved():
    site = _only(REBOUND_NAME_ARGV)
    assert site.bucket == census.UNRESOLVED, (
        "the name is bound twice, once to git and once to something else, so no "
        "single static answer exists"
    )


def test_function_parameter_shadows_a_module_binding():
    site = _only(PARAMETER_SHADOWS_MODULE)
    assert site.bucket == census.UNRESOLVED, (
        "the parameter shadows the module-level GIT_ARGV, so resolving through to "
        "the module constant would be a false GIT"
    )


def test_kwargs_splat_is_unresolved():
    assert _only(KWARGS_SPLAT_ARGV).bucket == census.UNRESOLVED


def test_empty_sequence_argv_is_unresolved():
    assert _only(EMPTY_SEQUENCE_ARGV).bucket == census.UNRESOLVED


# ---------------------------------------------------------------------------
# WHAT MUST NOT BE DETECTED AT ALL
# ---------------------------------------------------------------------------


def test_regex_string_literal_shape_yields_no_call_site():
    sites = census.census_source(REGEX_STRING_SHAPE, "<fixture>")
    assert sites == [], (
        "the only subprocess.run text here is inside a string literal fed to a "
        "regex; an AST walk never parses string contents, so a name filter matching "
        f"this file is the defect, not the census. got {sites!r}"
    )


def test_a_non_subprocess_run_is_not_detected():
    sites = census.census_source(NOT_SUBPROCESS_RUN, "<fixture>")
    assert sites == [], (
        "`other.run(['git'])` is some other object's method; matching it would make "
        f"every GIT count an over-report. got {sites!r}"
    )


# ---------------------------------------------------------------------------
# THE GUARD COLUMN. UNKNOWN never means unguarded.
# ---------------------------------------------------------------------------


def test_guard_column_is_gated_when_the_module_references_a_gate():
    assert _only(GATED_MODULE).guard == census.GATED


def test_guard_column_is_unknown_and_never_says_unguarded():
    site = _only(UNGATED_MODULE)
    assert site.guard == census.GUARD_UNKNOWN
    assert site.guard == "UNKNOWN", (
        "an AST walk for a try block around the call is STRUCTURALLY BLIND to a "
        "guard placed at the CALLER, which is where this tree puts them, so the "
        "absent-guard verdict must be spelled UNKNOWN and never UNGUARDED"
    )


def test_the_census_module_never_emits_the_word_unguarded():
    text = (REPO_ROOT / "tools" / "git_subprocess_census.py").read_text(encoding="ascii")
    emitted = [line for line in text.splitlines() if '"UNGUARDED"' in line]
    assert emitted == [], (
        "a literal UNGUARDED token would let a reader treat a blind spot as a "
        f"finding. offending lines: {emitted!r}"
    )


# ---------------------------------------------------------------------------
# COUNTS AND REPORT
# ---------------------------------------------------------------------------


def test_counts_report_all_three_buckets_even_when_two_are_empty():
    tally = census.counts(census.census_source(GIT_LIST_LITERAL, "<fixture>"))
    assert set(tally) == {census.GIT, census.NOT_GIT, census.UNRESOLVED}, (
        "a two-bucket tally is the defect this row exists to kill; the zero buckets "
        "must still be printed"
    )
    assert tally[census.GIT] == 1
    assert tally[census.NOT_GIT] == 0
    assert tally[census.UNRESOLVED] == 0


def test_report_prints_every_unresolved_site_by_line():
    sites = census.census_source(BARE_NAME_ARGV, "<fixture>")
    report = census.format_report(sites)
    assert "UNRESOLVED" in report
    assert "<fixture>:3" in report, (
        "an unresolved site that is counted but not listed cannot be followed up; "
        f"report was:\n{report}"
    )


def test_the_census_cli_is_not_a_gate():
    assert census.main([]) == 0, (
        "this is a census tool; making it fail a build turns an enumeration into a "
        "sizing decision, which is explicitly not this row"
    )


# ---------------------------------------------------------------------------
# THE REAL TREE. The row makes a prediction; these arms hold it to it.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_sites() -> list[census.CallSite]:
    return census.census_paths(census.DEFAULT_ROOTS, REPO_ROOT)


def test_real_census_finds_a_known_git_site(real_sites):
    git_files = {site.path for site in real_sites if site.bucket == census.GIT}
    assert "tests/test_no_sibling_names.py" in git_files, (
        "this module builds its corpus from `git ls-files`, so a census that cannot "
        "see it is measuring nothing and every arm below it is vacuous"
    )


def test_the_two_predicted_modules_are_absent_from_the_git_bucket(real_sites):
    git_files = {site.path for site in real_sites if site.bucket == census.GIT}
    for predicted in (
        "tests/test_ci_history_depth.py",
        "tests/test_guard_worktree_blindness.py",
    ):
        assert predicted not in git_files, (
            f"{predicted} was measured to shell no git at all; a skip added to it "
            "would be a false skip with no defect behind it"
        )


def test_real_census_reaches_more_than_one_root(real_sites):
    roots = {site.path.split("/", 1)[0] for site in real_sites}
    assert len(roots) >= 2, (
        "every declared root walked to nothing but tests/ would mean the path walk "
        f"is broken rather than that the tree is clean. roots seen: {sorted(roots)}"
    )


# ---------------------------------------------------------------------------
# THIS SLICE'S OWN BYTES. 7-bit ASCII, LF only.
# ---------------------------------------------------------------------------

_AUTHORED = (
    Path("tools") / "git_subprocess_census.py",
    Path("tests") / "test_git_subprocess_census.py",
)


def _non_ascii_offsets(raw: bytes) -> list[int]:
    return [index for index, byte in enumerate(raw) if byte > 0x7F]


def test_authored_bytes_are_seven_bit_ascii_with_no_cr():
    for relative in _AUTHORED:
        raw = (REPO_ROOT / relative).read_bytes()
        assert _non_ascii_offsets(raw) == [], (
            f"{relative.as_posix()} carries non-ASCII bytes at "
            f"{_non_ascii_offsets(raw)[:8]}"
        )
        assert b"\r" not in raw, (
            f"{relative.as_posix()} carries CR; write_text emits CRLF on Windows and "
            "eol=lf in .gitattributes hides it from every diff"
        )


def test_the_ascii_detector_actually_fires():
    dashed = ("clause" + chr(0x2014) + "break").encode("utf-8")
    assert _non_ascii_offsets(dashed), (
        "the ASCII arm above would pass on a file full of em-dashes if the detector "
        "never fired"
    )
    assert _non_ascii_offsets(b"plain ascii") == []


def test_the_fixture_sources_parse():
    """Every fixture source in this module is real Python.

    The filter was once `"subprocess" in source`, which silently excluded every
    unresolvable-callee fixture below - fixtures that name no `subprocess` at
    all - so the arm would have parsed a shrinking subset while
    still reporting a pass. It selects on being a multi-line uppercase string
    instead, and carries a floor so an emptied selection cannot read as green.
    """
    parsed = 0
    for name, source in sorted(globals().items()):
        if name.isupper() and isinstance(source, str) and "\n" in source:
            ast.parse(source)
            parsed += 1
    assert parsed >= 50, (
        f"only {parsed} fixture sources were selected; a selector that matches "
        "almost nothing parses almost nothing and still exits 0"
    )


# ---------------------------------------------------------------------------
# POSITIONS THAT ARE NOT A STATEMENT BODY. A DROPPED SITE IS THE DEFECT.
# ---------------------------------------------------------------------------


def test_a_launch_in_a_function_decorator_is_not_dropped():
    site = _only(DECORATOR_ON_FUNCTION)
    assert site.bucket == census.GIT, (
        "a decorator expression is not in any statement body, so a walk that "
        "recurses into `body` alone emits no row at all for this git launch"
    )
    assert site.lineno == 2


def test_a_launch_in_a_class_decorator_is_not_dropped():
    assert _only(DECORATOR_ON_CLASS).bucket == census.GIT


def test_a_launch_in_a_method_decorator_is_not_dropped():
    assert _only(DECORATOR_ON_METHOD).bucket == census.GIT


def test_a_launch_in_a_nested_function_decorator_is_not_dropped():
    assert _only(NESTED_DECORATOR).bucket == census.GIT


def test_a_launch_in_a_default_argument_is_not_dropped():
    site = _only(DEFAULT_ARGUMENT_ARGV)
    assert site.bucket == census.GIT, (
        "a default argument is evaluated once at definition time and is a real "
        "launch; dropping it makes the git surface look smaller than it is"
    )


def test_a_launch_in_a_keyword_only_default_is_not_dropped():
    assert _only(KWONLY_DEFAULT_ARGV).bucket == census.GIT


def test_a_launch_in_a_nested_default_argument_is_not_dropped():
    assert _only(NESTED_DEFAULT_ARGUMENT_ARGV).bucket == census.GIT


def test_a_launch_in_a_lambda_default_is_not_dropped():
    assert _only(LAMBDA_DEFAULT_ARGV).bucket == census.GIT


def test_a_default_argument_resolves_in_the_enclosing_scope():
    site = _only(DEFAULT_RESOLVES_IN_THE_ENCLOSING_SCOPE)
    assert site.bucket == census.GIT, (
        "the default is evaluated before the parameter of the same spelling "
        "exists, so walking it with the nested chain is a false UNRESOLVED"
    )


# ---------------------------------------------------------------------------
# SHELL=TRUE
# ---------------------------------------------------------------------------


def test_shell_true_resolves_the_command_out_of_list_element_zero():
    site = _only(SHELL_TRUE_LIST_HEAD_GIT)
    assert site.bucket == census.GIT, (
        "under shell=True element 0 carries the command - the string on POSIX, "
        "the head of the joined command line on Windows - so this launches git"
    )


def test_shell_true_list_element_zero_can_still_be_not_git():
    assert _only(SHELL_TRUE_LIST_HEAD_NOT_GIT).bucket == census.NOT_GIT


def test_shell_true_honours_quoting_inside_list_element_zero():
    assert _only(SHELL_TRUE_LIST_QUOTED_PATH).bucket == census.GIT


def test_the_same_bytes_without_shell_true_are_not_git():
    assert _only(NO_SHELL_LIST_HEAD_WITH_SPACE).bucket == census.NOT_GIT, (
        "without shell=True 'git log -n 1' names one executable whose name "
        "contains spaces; splitting it would cut an absolute path at its space"
    )


def test_an_unknowable_shell_flag_over_an_ambiguous_head_is_unresolved():
    site = _only(SHELL_NOT_STATICALLY_KNOWN_AMBIGUOUS)
    assert site.bucket == census.UNRESOLVED, (
        "shell= is a parameter, and the two readings of argv[0] disagree, so "
        "either bucket would be a guess"
    )


def test_an_unknowable_shell_flag_over_an_unambiguous_head_still_resolves():
    assert _only(SHELL_NOT_STATICALLY_KNOWN_UNAMBIGUOUS).bucket == census.GIT


# ---------------------------------------------------------------------------
# THE UNRESOLVED FALLBACK. Flipping it to NOT-GIT must go red HERE.
# ---------------------------------------------------------------------------


def test_a_which_call_as_argv0_is_unresolved_and_never_not_git():
    site = _only(WHICH_CALL_ARGV_HEAD)
    assert site.bucket == census.UNRESOLVED, (
        "shutil.which('git') is the most ordinary dynamic git argv[0] in Python; "
        "an UNRESOLVED fallback folded into NOT-GIT makes it a silent non-finding"
    )
    assert "Call" in site.argv0


def test_a_which_call_as_the_whole_argv_is_unresolved():
    site = _only(WHICH_CALL_WHOLE_ARGV)
    assert site.bucket == census.UNRESOLVED
    assert "Call" in site.argv0


def test_a_subscript_argv0_is_unresolved_and_never_not_git():
    site = _only(SUBSCRIPT_ARGV_HEAD)
    assert site.bucket == census.UNRESOLVED
    assert "Subscript" in site.argv0


def test_a_subscript_whole_argv_is_unresolved():
    site = _only(SUBSCRIPT_WHOLE_ARGV)
    assert site.bucket == census.UNRESOLVED
    assert "Subscript" in site.argv0


# ---------------------------------------------------------------------------
# CONSERVATION. The only arm shape that catches a DROP.
# ---------------------------------------------------------------------------


def test_every_launch_in_the_conservation_fixture_is_conserved():
    sites = census.census_source(CONSERVATION_SOURCE, "<fixture>")
    tally = census.counts(sites)
    assert len(sites) == CONSERVATION_TOTAL, (
        f"{CONSERVATION_TOTAL} launches were counted by hand in this fixture and "
        f"{len(sites)} were emitted; a missing row is invisible where a wrong row "
        f"is arguable. emitted: "
        f"{[(site.lineno, site.bucket, site.argv0) for site in sites]}"
    )
    assert sum(tally.values()) == CONSERVATION_TOTAL, (
        "the three bucket counts must sum to the launch count; a site that is "
        f"neither bucketed nor dropped is unaccounted for. tally: {tally}"
    )
    assert tally == {
        census.GIT: CONSERVATION_EXPECTED["GIT"],
        census.NOT_GIT: CONSERVATION_EXPECTED["NOT-GIT"],
        census.UNRESOLVED: CONSERVATION_EXPECTED["UNRESOLVED"],
    }, f"tally: {tally}"


def test_the_conservation_arm_would_notice_a_drop():
    """Non-vacuity: the fixture really does hold launches in dropped positions.

    Stripping the decorator and default positions out of the fixture leaves
    strictly fewer launches, so the SUM the arm above pins is load-bearing
    rather than a restatement of whatever the walk happens to find.
    """
    body_only = "import subprocess\nsubprocess.run(['git', 'status'])\n"
    assert len(census.census_source(body_only, "<fixture>")) < CONSERVATION_TOTAL


# ---------------------------------------------------------------------------
# AN UNRESOLVABLE CALLEE. THE DEFECT IS SILENCE, NOT A WRONG BUCKET.
#
# `_launcher_for` branched on `ast.Attribute` and `ast.Name` only. When `call.func` is
# ITSELF a call - `getattr(subprocess, "run")(...)`, a `functools.partial`, a
# factory that hands back a stub shaped like `subprocess.run` - it returned None
# and NO ROW WAS EMITTED AT ALL. A conservation assertion cannot catch that:
# there is nothing left to conserve. The same hole is open for every other func
# expression that is neither an Attribute nor a Name - a `ast.Subscript` lookup
# in a dispatch table, an `ast.BoolOp` picking an injected callable over a
# default - so the repair is SUBTRACTIVE, exactly as `_outer_positions` is:
# anything not Attribute and not Name is unresolvable and says so.
#
# THIS IS A CONTRACT-HONESTY REPAIR AND NOT A LEAK FIX. Every func-is-a-Call
# site in `DEFAULT_ROOTS` is a stub or predicate invocation and NONE launches a
# process. What was broken is the module's claim to see every call it buckets,
# not the tree.
#
# THE SIBLING WIDENING THAT WAS REJECTED, recorded so it is not re-derived. An
# `ast.Attribute` func whose RECEIVER does not resolve - `get_runner().run(...)`
# - was proposed for the same treatment. Measured over `DEFAULT_ROOTS`: Attribute
# callees with an unresolvable receiver number in the high hundreds - a figure
# that moves with every edit, so it is deliberately not pinned here - and NOT ONE
# of them is spelled like a subprocess entry point. The count that matters is the
# ZERO, and the arm below is what keeps measuring it. Reachability is zero, so the
# arm exercising it would move with any mutant of the spelling set rather than
# pin an input. That is the same ground - CONTRACT, reachability zero - on which
# this tree has twice ruled DO NOT WIDEN. The boundary is pinned as a SILENCE by
# the decoys below rather than left to whoever reads this next.
# ---------------------------------------------------------------------------

GETATTR_CALLEE = (
    "import subprocess\ngetattr(subprocess, 'run')(['git', 'status'])\n"
)

PARTIAL_CALLEE = (
    "import functools\n"
    "import subprocess\n"
    "functools.partial(subprocess.run)(['git', 'log'])\n"
)

# No `import subprocess` anywhere in this fixture. The row must still appear:
# the point of an unresolvable callee is that the module cannot tell what is
# being called, so making the row conditional on a subprocess import would
# reintroduce the name filter this census exists to replace.
STUB_FACTORY_CALLEE = (
    "def probe(stub, cmd):\n"
    "    return stub(3, '')(cmd, capture_output=True, check=True)\n"
)

SUBSCRIPT_CALLEE = (
    "HANDLERS = {}\ndef probe(key):\n    return HANDLERS[key](['git', 'status'])\n"
)

BOOLOP_CALLEE = (
    "def probe(spawn, prompt):\n    return (spawn or _fallback)(prompt)\n"
)

# THE TWO DECOYS. A repair that emits a row for every call whatsoever would pass
# every arm above and destroy the census. Both of these vary more than one
# position against the fixtures above - receiver spelling AND attribute, bare
# name AND argument shape - and both must still yield NOTHING.
ATTRIBUTE_CALLEE_ON_A_STRANGER = "import subprocess\nother.launch(['git', 'status'])\n"

PLAIN_NAME_CALLEE = "def helper(argv):\n    return None\nhelper(['git', 'status'])\n"

# THE THIRD DECOY, and the one that pins the REJECTED widening. The receiver is
# invisible and the attribute is spelled exactly like a subprocess entry point.
# This is the shape a sibling candidate proposed emitting a row for. It must
# still yield NOTHING: `ast.Attribute` is the commonest func shape in any Python
# tree, and a rule keyed on the attribute name alone would put rows on a large
# share of every module here while reaching not one real call site.
UNRESOLVABLE_RECEIVER_LAUNCHER_SPELLING = (
    "def probe(factory):\n    return factory().run(['git', 'status'])\n"
)

# Every attribute spelling a reader might expect to start a process. Written out
# as a LITERAL here rather than read off the census, because an arm whose fixture
# is derived from the module under test moves with the mutant and pins a format
# instead of an input.
_SPELLINGS_A_READER_WOULD_EXPECT = frozenset(
    {
        "run",
        "check_output",
        "check_call",
        "call",
        "Popen",
        "getoutput",
        "getstatusoutput",
        "system",
        "popen",
        "startfile",
        "execv",
        "execvp",
        "spawnv",
        "spawnvp",
        "posix_spawn",
    }
)


# The conservation fixture for the two shapes this census emits a row for,
# counted by hand: three subprocess calls (2 GIT, 1 NOT-GIT) and three
# unresolvable callees, one per node kind. Six rows, and the two decoy calls on
# the last two lines must add nothing.
WIDENED_CONSERVATION_SOURCE = (
    "import functools\n"
    "import subprocess\n"
    "subprocess.run(['git', 'status'])\n"
    "subprocess.Popen(['git', 'log'])\n"
    "subprocess.run(['python', '-c', 'pass'])\n"
    "getattr(subprocess, 'run')(['git', 'show'])\n"
    "functools.partial(subprocess.run)(['git', 'tag'])\n"
    "HANDLERS['k'](['git', 'diff'])\n"
    "other.launch(['git', 'status'])\n"
    "helper(['git', 'status'])\n"
)

WIDENED_CONSERVATION_TOTAL = 6
WIDENED_CONSERVATION_EXPECTED = {"GIT": 2, "NOT-GIT": 1, "UNRESOLVED": 3}


# ---------------------------------------------------------------------------
# AN UNRESOLVABLE CALLEE MUST PRODUCE A ROW, NOT SILENCE
# ---------------------------------------------------------------------------


def test_a_getattr_callee_emits_an_unresolved_site_rather_than_silence():
    site = _only(GETATTR_CALLEE)
    assert site.bucket == census.UNRESOLVED, (
        "getattr(subprocess, 'run')(...) launches git; the callee is a call "
        "expression so the census cannot resolve it, and UNRESOLVED is the "
        "bucket this module already keeps for what it cannot answer"
    )


def test_a_functools_partial_callee_emits_an_unresolved_site():
    assert _only(PARTIAL_CALLEE).bucket == census.UNRESOLVED


def test_a_stub_factory_callee_is_seen_without_any_subprocess_import():
    site = _only(STUB_FACTORY_CALLEE)
    assert site.bucket == census.UNRESOLVED, (
        "no subprocess import appears in this fixture at all; gating the row on "
        "one would be the name filter this census replaces"
    )


def test_a_subscript_callee_emits_an_unresolved_site():
    assert _only(SUBSCRIPT_CALLEE).bucket == census.UNRESOLVED


def test_a_boolop_callee_emits_an_unresolved_site():
    assert _only(BOOLOP_CALLEE).bucket == census.UNRESOLVED


def test_the_unresolvable_callee_row_names_the_node_kind():
    assert _only(GETATTR_CALLEE).callee == "<unresolved:Call>"
    assert _only(SUBSCRIPT_CALLEE).callee == "<unresolved:Subscript>"
    assert _only(BOOLOP_CALLEE).callee == "<unresolved:BoolOp>"


def test_the_unresolvable_callee_row_says_why_in_the_argv_column():
    site = _only(GETATTR_CALLEE)
    assert "callee" in site.argv0, (
        "the row must say the CALLEE is what could not be resolved, not leave a "
        f"reader to assume argv[0] was the problem: {site.argv0!r}"
    )


def test_an_attribute_callee_on_a_stranger_still_yields_nothing():
    sites = census.census_source(ATTRIBUTE_CALLEE_ON_A_STRANGER, "<fixture>")
    assert sites == [], (
        "the receiver resolves and is not subprocess, so this is a POSITIVE "
        f"not-a-launch answer; emitting a row for it would destroy the census. "
        f"got {sites!r}"
    )


def test_a_plain_name_callee_still_yields_nothing():
    sites = census.census_source(PLAIN_NAME_CALLEE, "<fixture>")
    assert sites == [], (
        "a bare name that was never imported from subprocess is not a launch; a "
        f"repair that emits a row for every call whatsoever passes every "
        f"unresolvable-callee arm above and is still wrong. got {sites!r}"
    )


def test_a_launcher_spelling_through_an_invisible_receiver_stays_a_silence():
    sites = census.census_source(UNRESOLVABLE_RECEIVER_LAUNCHER_SPELLING, "<fixture>")
    assert sites == [], (
        "`factory().run(...)` has an unresolvable receiver and an attribute "
        "spelled like a subprocess entry point. Emitting a row for it was "
        "proposed and REJECTED: ast.Attribute is the commonest func shape in any "
        f"Python tree and the rule reaches nothing here. got {sites!r}"
    )


def test_no_invisible_receiver_in_this_tree_is_spelled_like_a_launcher():
    """The measurement the rejected widening was ruled out on, re-taken each run.

    If a call in `DEFAULT_ROOTS` ever DOES name a subprocess entry point through
    a receiver nobody can see, this arm goes red and the ruling is due a re-look
    on evidence rather than on taste.
    """
    seen = 0
    offenders: list[tuple[str, int, str]] = []
    for name in census.DEFAULT_ROOTS:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        for path in census._python_files(directory):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if census._dotted(func.value) is not None:
                    continue
                seen += 1
                if func.attr in _SPELLINGS_A_READER_WOULD_EXPECT:
                    offenders.append((relative, node.lineno, func.attr))
    assert seen > 100, (
        f"only {seen} Attribute callees with an unresolvable receiver were found; "
        "a walk that reaches almost none of them measures almost nothing and "
        "still exits 0"
    )
    assert offenders == [], (
        "a subprocess entry point is being reached through a receiver this "
        "census cannot see, so the rule that was ruled out on reachability now "
        f"has a real call site behind it: {offenders}"
    )




# ---------------------------------------------------------------------------
# CONSERVATION OVER THE WIDENED SUBJECT
# ---------------------------------------------------------------------------


def test_the_widened_conservation_fixture_is_conserved():
    sites = census.census_source(WIDENED_CONSERVATION_SOURCE, "<fixture>")
    tally = census.counts(sites)
    assert len(sites) == WIDENED_CONSERVATION_TOTAL, (
        f"{WIDENED_CONSERVATION_TOTAL} call sites were counted by hand across "
        f"the two shapes and {len(sites)} were emitted. emitted: "
        f"{[(site.lineno, site.callee, site.bucket) for site in sites]}"
    )
    assert tally == {
        census.GIT: WIDENED_CONSERVATION_EXPECTED["GIT"],
        census.NOT_GIT: WIDENED_CONSERVATION_EXPECTED["NOT-GIT"],
        census.UNRESOLVED: WIDENED_CONSERVATION_EXPECTED["UNRESOLVED"],
    }, f"tally: {tally}"


def test_each_shape_in_the_widened_fixture_contributes_a_row():
    """Non-vacuity: each of the two shapes really is load-bearing here.

    Deleting any one shape from the fixture leaves strictly fewer rows, so the
    total the arm above pins is a hand count rather than a restatement of
    whatever the walk happens to find today.
    """
    lines = WIDENED_CONSERVATION_SOURCE.splitlines(keepends=True)
    full = len(census.census_source(WIDENED_CONSERVATION_SOURCE, "<fixture>"))
    for marker in (
        "subprocess.run(['git', 'status'])",
        "getattr(subprocess, 'run')",
        "HANDLERS['k']",
    ):
        pruned = "".join(line for line in lines if marker not in line)
        assert len(census.census_source(pruned, "<fixture>")) < full, (
            f"removing {marker!r} changed nothing, so that shape contributes no "
            "row and the hand count above is measuring something else"
        )


def test_both_call_shapes_are_distinguishable_in_the_report():
    sites = census.census_source(WIDENED_CONSERVATION_SOURCE, "<fixture>")
    report = census.format_report(sites)
    for expected in ("subprocess.run", "<unresolved:Call>", "<unresolved:Subscript>"):
        assert expected in report, (
            f"{expected} is counted but never named, so a reader cannot follow "
            f"the row up. report was:\n{report}"
        )


def test_the_report_never_calls_an_unresolvable_callee_a_launch():
    """The total line and every row must survive a population that launches nothing.

    `total launch sites : N` was printed over a population that includes rows
    whose callee this module could not read at all. That is a contract lie in the
    one place a reader takes the number from, and the same word had leaked into
    the row's own reason string. The fixture below holds NOTHING BUT opaque
    callees, so the word cannot appear truthfully anywhere in the render.
    """
    source = (
        "import functools\n"
        "getattr(mod, 'run')(['git', 'status'])\n"
        "HANDLERS['k'](['git', 'log'])\n"
        "(spawn or fallback)(['git', 'diff'])\n"
    )
    sites = census.census_source(source, "<fixture>")
    assert len(sites) == 3, f"fixture must be all-opaque, got {sites!r}"
    assert {site.bucket for site in sites} == {census.UNRESOLVED}
    report = census.format_report(sites)
    offenders = [line for line in report.splitlines() if "launch" in line.lower()]
    assert offenders == [], (
        "every row here is a call this census could not resolve, so calling any "
        f"of them a launch asserts something the UNRESOLVED bucket refuses to "
        f"assert. offending lines: {offenders!r}"
    )


def test_the_launch_word_detector_actually_fires():
    """Non-vacuity for the arm above: the scan really can see the word."""
    faked = "total launch sites : 3\n  UNRESOLVED : 3"
    assert [line for line in faked.splitlines() if "launch" in line.lower()], (
        "the arm above would pass over a report full of the word if the scan "
        "never matched it"
    )


def _opaque_callee_nodes(root: Path) -> list[tuple[str, int]]:
    """Every `ast.Call` under `root` whose func is neither Attribute nor Name.

    Derived from the tree by an INDEPENDENT walk - `ast.walk`, not the census's
    own scope recursion - so the count this returns is not a restatement of the
    thing it is used to check. A file the census would report `<unparseable>`
    or `<unreadable>` for contributes nothing here and its row carries a
    different callee spelling, so the two populations stay aligned.
    """
    found: list[tuple[str, int]] = []
    for name in census.DEFAULT_ROOTS:
        directory = root / name
        if not directory.is_dir():
            continue
        for path in census._python_files(directory):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            relative = path.relative_to(root).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and not isinstance(
                    node.func, (ast.Attribute, ast.Name)
                ):
                    found.append((relative, node.lineno))
    return found


def test_the_widened_conservation_arm_would_notice_a_drop(real_sites):
    """NODE-TO-ROW CONSERVATION over the real tree, not over a fixture.

    Every `ast.Call` in `DEFAULT_ROOTS` whose func is neither an `ast.Attribute`
    nor an `ast.Name` must yield EXACTLY ONE row. This is the only arm here that
    goes red when the opaque-callee branch is reverted: reverting it restores the
    silence, the rows vanish, and every fixture arm above keeps passing because a
    fixture arm cannot see a real-tree drop. The two sides are counted by
    different walks, so agreeing is evidence rather than a tautology.
    """
    nodes = _opaque_callee_nodes(REPO_ROOT)
    rows = [
        (site.path, site.lineno)
        for site in real_sites
        if site.callee.startswith(census.UNRESOLVED_CALLEE_PREFIX)
    ]
    assert nodes, (
        "no opaque-callee node was found anywhere in DEFAULT_ROOTS, so this arm "
        "is comparing zero with zero and cannot fail"
    )
    assert sorted(rows) == sorted(nodes), (
        f"{len(nodes)} opaque-callee call nodes were walked and {len(rows)} rows "
        "were emitted; a node with no row is a SILENCE, which is the defect the "
        f"opaque-callee branch exists to close. nodes not rowed: "
        f"{sorted(set(nodes) - set(rows))}. rows with no node: "
        f"{sorted(set(rows) - set(nodes))}"
    )
    assert all(site.bucket == census.UNRESOLVED for site in real_sites
               if site.callee.startswith(census.UNRESOLVED_CALLEE_PREFIX)), (
        "an unresolvable callee that landed in GIT or NOT-GIT would be a "
        "confident answer over a call nobody could read"
    )


# ---------------------------------------------------------------------------
# THE DECLARED-OUT-OF-SCOPE PREMISE, TURNED FROM PROSE INTO A RED ARM
# ---------------------------------------------------------------------------
#
# The census docstring DECLARES what it does not cover - `subprocess.getoutput`,
# `subprocess.getstatusoutput`, `os.system`, `os.popen` and the `os` exec and
# spawn families - and it justifies leaving the population narrow with a
# MEASURED PROSE PREMISE: "none has a call site in `DEFAULT_ROOTS`". That
# premise is true in this run and was guarded by NOTHING, so the day a call site
# arrives the census goes SILENT and the docstring goes QUIETLY FALSE. A prose
# premise that decays takes the next reader's question with it, and that exact
# failure mode was measured in this tree.
#
# The arm below is the OPPOSITE move to widening the census. It does not add a
# bucket, a launcher or a row. It asserts that the population the docstring
# measured at zero really is zero, so the decay becomes a RED SUITE rather than
# a silence. Widening a mechanism to a population measured at zero was proposed
# here, refuted, and adjudicated out on contract grounds - see the entry in
# `ROADMAP.md` recording that call, found by its heading and never by line
# number.


# The names the census DECLARES out of scope, spelled out HERE as a literal and
# never read back out of the module. An arm whose fixture is derived from the
# module under test MOVES WITH THE MUTANT: delete a name from `LAUNCHERS` or a
# clause from that docstring and a derived fixture shrinks with it, so the arm
# pins a FORMAT instead of an INPUT. `_SPELLINGS_A_READER_WOULD_EXPECT` above is
# the precedent in this same file.
#
# `os.startfile` is deliberately ABSENT. The census docstring does not declare
# it, so guarding it would be guarding a claim nobody made.
_DECLARED_OUT_OF_SCOPE: dict[str, frozenset[str]] = {
    "subprocess": frozenset({"getoutput", "getstatusoutput"}),
    "os": frozenset(
        {
            "system",
            "popen",
            "execl",
            "execle",
            "execlp",
            "execlpe",
            "execv",
            "execve",
            "execvp",
            "execvpe",
            "spawnl",
            "spawnle",
            "spawnlp",
            "spawnlpe",
            "spawnv",
            "spawnve",
            "spawnvp",
            "spawnvpe",
            "posix_spawn",
            "posix_spawnp",
        }
    ),
}

# ---------------------------------------------------------------------------
# BOTH DIRECTIONS, BECAUSE ONE DIRECTION WAS MEASURED AND IT WAS NOT ENOUGH
# ---------------------------------------------------------------------------
#
# The literal above started life pinned in ONE direction only. Adding a name
# went red - `test_the_out_of_scope_names_literal_is_not_derived_from_the_census`
# rejects "startfile" - but REMOVING one did not. Measured on the bytes this
# block repairs: deleting "spawnve" alone left the whole file green, and deleting
# ALL SEVENTEEN names that no hand fixture spells, in one edit, also left it
# green. Only the five names a fixture happens to mention - system, popen,
# execvp, getoutput, getstatusoutput - were pinned at all, so seventeen of the
# twenty-two were decoration.
#
# This tree measured the identical trap this session on a different sweep: an
# UNPATCHED ADDITION went red while a PATCHED REMOVAL stayed green, and the
# repair there is the repair here - assert both directions, and say in the code
# why, because the asymmetry is invisible to a reader who only sees the green.
#
# A fixture DERIVED from the literal cannot close this on its own: delete a name
# and its derived fixture goes with it, so the arm shrinks in step with the
# mutant and pins a format instead of an input. Three pins are therefore used,
# and each one is named with the names it actually holds:
#
#   1  THE EXACT SET, below. Every declared name written a SECOND time, in dotted
#      form, so the expectation is not a copy of the literal's shape. This is the
#      pin that makes a REMOVAL red, for any of the 22, and it is the only one
#      that does.
#   2  THE RUNNING INTERPRETER'S OWN `os` NAMESPACE, which is not the module
#      under test and not this file. Every `exec*` / `spawn*` attribute `os`
#      really has must be declared. Measured on this platform: 12 such
#      attributes, all 12 declared. Six declared names - posix_spawn,
#      posix_spawnp, spawnlp, spawnlpe, spawnvp, spawnvpe - are POSIX-only and
#      are NOT `os` attributes here, so this pin does not reach them on Windows
#      and the arm says so rather than leaving it to be discovered.
#   3  A PER-NAME CALL SITE, generated in memory. Every declared name gets a real
#      call the sweep must find, so the SWEEP'S REACH is pinned across all 22
#      rather than across the 5 the hand fixtures spell. This one cannot catch a
#      removal, by construction, and pin 1 is what does.

# Pin 1. Hand-typed, dotted, sorted. Never built from `_DECLARED_OUT_OF_SCOPE`.
_EVERY_DECLARED_NAME_DOTTED = (
    "os.execl",
    "os.execle",
    "os.execlp",
    "os.execlpe",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "os.popen",
    "os.posix_spawn",
    "os.posix_spawnp",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "os.system",
    "subprocess.getoutput",
    "subprocess.getstatusoutput",
)

# Pin 2. The prefixes the docstring's family phrase covers, and the names that
# phrase covers which this interpreter does not have. The residue is asserted as
# a SUBSET and never as an equality: CI runs ubuntu-latest, where all six exist,
# so an equality here would be green on Windows and red on Linux at the same
# commit. A subset arm holds on both and still catches a typo.
_OS_FAMILY_PREFIXES = ("exec", "spawn", "posix_spawn")
_KNOWN_POSIX_ONLY_SPELLINGS = frozenset(
    {
        "posix_spawn",
        "posix_spawnp",
        "spawnlp",
        "spawnlpe",
        "spawnvp",
        "spawnvpe",
    }
)

# ---------------------------------------------------------------------------
# FINDING 4's SEAM: TWO ARTIFACTS DESCRIBING ONE MECHANISM, AND NOTHING JOINING
# THEM
# ---------------------------------------------------------------------------
#
# `tools/git_subprocess_census.py` declares its out-of-scope names in PROSE:
# four spelled out literally, and the rest folded into one family phrase. The
# literal above expands that phrase to 18 enumerated names, and until this arm
# existed NOTHING compared the two. That unguarded seam is exactly why the
# removals above could stay green: the literal could drift away from the
# docstring, or the docstring could drop a declaration, and both artifacts would
# keep reading as if they agreed.
#
# Hand-typed here, not read off the module, for the reason stated above the
# literal.
_LITERALLY_DECLARED_IN_THE_DOCSTRING = (
    "`subprocess.getoutput`",
    "`subprocess.getstatusoutput`",
    "`os.system`",
    "`os.popen`",
)
_DECLARED_FAMILY_PHRASE = "the `os` exec and spawn families"

# The roots the premise is a claim ABOUT, spelled out here for the same reason.
# `DEFAULT_ROOTS` shrinking to `()` would leave A SWEEP OVER IT green having
# measured nothing, so the arm compares the module's tuple against this literal
# and sweeps THIS one.
#
# NOT A NOVEL CATCHER, and the claim is trimmed to what was measured. Two
# floors already in this file go red on a root shrink WITHOUT this equality:
# the `seen > 100` floor in
# `test_no_invisible_receiver_in_this_tree_is_spelled_like_a_launcher` and the
# `assert nodes` floor in `test_the_widened_conservation_arm_would_notice_a_drop`.
# What this equality adds is that it names the DRIFT directly rather than
# reporting it as an undersized population, which is worth having and is not a
# first.
_ROOTS_THE_PREMISE_COVERS = ("tests", "tools", "ops", "headless", "scripts")

# 108 python files were in the sweep population in this run. The floor is well
# below that so an ordinary deletion does not trip it, and far enough above zero
# that an emptied population cannot read as a pass - zero out of zero reads as
# green, which is the shape this whole file exists to refuse.
_POPULATION_FLOOR = 80

# Both import forms the sweep must see, plus the aliased and star spellings of
# each. Six call sites, counted by hand, one per line from the fifth line down.
OUT_OF_SCOPE_BOTH_IMPORT_FORMS = (
    "import os\n"
    "import subprocess\n"
    "from os import system as sh\n"
    "from subprocess import getoutput\n"
    "os.system('git status')\n"
    "sh('git log')\n"
    "getoutput('git rev-parse --git-dir')\n"
    "subprocess.getstatusoutput('git diff')\n"
    "os.popen('git tag')\n"
    "os.execvp('git', ['git', 'show'])\n"
)

OUT_OF_SCOPE_STAR_IMPORT = "from os import *\nsystem('git status')\n"

OUT_OF_SCOPE_MODULE_ALIAS = "import subprocess as sp\nsp.getoutput('git rev-parse')\n"

# THE NEIGHBOURS THAT MUST SURVIVE. A sweep that scores 100 percent on the
# offenders arm by flagging everything shaped vaguely like a launcher has
# failed, which is exactly what a blind find-replace does. Every line here names
# an out-of-scope spelling somewhere and NOT ONE of them is a call to one:
# a regex pattern, a string literal, a dict key, an in-scope launcher, an
# unrelated `os.path` attribute, an attribute on a stranger, and a `system`
# imported from a module that is not `os`.
OUT_OF_SCOPE_NEIGHBOURS_THAT_MUST_SURVIVE = (
    "import os\n"
    "import re\n"
    "import subprocess\n"
    "from platform import system\n"
    "PATTERN = re.compile('os.system')\n"
    "TEXT = \"os.popen('git tag')\"\n"
    "HANDLERS = {'getoutput': 'subprocess.getoutput'}\n"
    "subprocess.run(['git', 'status'])\n"
    "os.path.join('a', 'b')\n"
    "other.system('git log')\n"
    "system()\n"
)


# THE RECEIVER RESOLVER THAT USED TO LIVE HERE IS GONE, and its removal is the
# repair rather than a tidy-up. It walked an `ast.Attribute` chain and returned
# a DOTTED string such as `os.path`, and `receiver_modules` below is keyed on
# SINGLE-SEGMENT module names only, so a dotted receiver could never match a
# key. It was BEHAVIOUR-DEAD: collapsing the nine-line loop to
# `node.id if isinstance(node, ast.Name) else None` left every arm in this file
# green, measured. Worse, the offenders message described the counting shape as
# "an Attribute on a dotted Name", so a reader who failed that arm would have
# believed `pkg.os.system(...)` was checked when it never was.
#
# Two repairs were available and the SEAM was fixed rather than the symptom.
# Handling a dotted receiver for real was rejected: it has ZERO call sites over
# these roots, this tree has ruled against widening a mechanism to a population
# measured at zero, and the census itself resolves only single-segment receivers
# - `_import_aliases` in `tools/git_subprocess_census.py` collects bare module
# bases and nothing else - so a sweep with MORE receiver reach than the module it
# grades would red on shapes the census is not claiming to see. The dead code is
# therefore deleted, the message now says exactly what is walked, and the gap is
# DECLARED as a pinned silence in `_DECLARED_BLIND_SPOTS` rather than implied
# away.

def _out_of_scope_call_sites(source: str, path: str) -> list[tuple[str, int, str]]:
    """Every call site in one source that reaches a declared-out-of-scope name.

    AN AST WALK, NEVER A GREP, and the reason is measured rather than asserted.
    A grep for `getoutput` over these roots returns hits in this run - dict KEYS
    in `tests/test_task_liveness.py` and prose in the census docstring itself -
    and not one of them is a call. A text filter cannot tell a string literal
    from a call, which is the exact premise of the module this file grades.

    THREE FORMS, because a one-form sweep is a fixture built parallel to its own
    assumption:

      Attribute-on-Name  `os.system(...)`, and `sp.getoutput(...)` under an
                         `import subprocess as sp`. A PLAIN Name receiver and
                         nothing else - `pkg.os.system(...)` is a declared
                         blind spot, pinned as a silence below
      direct import      `from os import system` then `system(...)`, alias
                         included - `from os import system as sh` then `sh(...)`
      star import        `from os import *` then `system(...)`. Unresolvable in
                         general, so a star import from either module makes every
                         bare name spelled like an out-of-scope entry point
                         count. A false red there is a human reading one line; a
                         false green is the silence this arm exists to remove.

    `os` and `subprocess` seed the receiver map UNCONDITIONALLY, matching the
    census's own `_import_aliases`. A file that calls `.system(...)` on an `os`
    it rebound to something else earns a red that a human reads, which is the
    cheaper of the two errors here.

    Returns `(path, lineno, described)` so an assertion can name the site rather
    than only count it.
    """
    tree = ast.parse(source)
    receiver_modules = {name: name for name in _DECLARED_OUT_OF_SCOPE}
    direct: dict[str, tuple[str, str]] = {}
    starred: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname and alias.name in _DECLARED_OUT_OF_SCOPE:
                    receiver_modules[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module is None or module not in _DECLARED_OUT_OF_SCOPE:
                continue
            for alias in node.names:
                if alias.name == "*":
                    starred.add(module)
                elif alias.name in _DECLARED_OUT_OF_SCOPE[module]:
                    direct[alias.asname or alias.name] = (module, alias.name)
    star_names = {
        spelling
        for module in starred
        for spelling in _DECLARED_OUT_OF_SCOPE[module]
    }
    found: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            # A PLAIN, SINGLE-SEGMENT NAME RECEIVER ONLY. A dotted receiver is
            # a declared blind spot - see `_DECLARED_BLIND_SPOTS` - and not an
            # oversight; it is the same reach the census itself has.
            if not isinstance(func.value, ast.Name):
                continue
            receiver = func.value.id
            module = receiver_modules.get(receiver)
            if module is None:
                continue
            if func.attr in _DECLARED_OUT_OF_SCOPE[module]:
                found.append((path, node.lineno, f"{receiver}.{func.attr}"))
        elif isinstance(func, ast.Name):
            binding = direct.get(func.id)
            if binding is not None:
                found.append(
                    (path, node.lineno, f"{func.id} -> {binding[0]}.{binding[1]}")
                )
            elif func.id in star_names:
                found.append((path, node.lineno, f"{func.id} via a star import"))
    return sorted(found)


def _sweep(
    sources: list[tuple[str, str]],
) -> tuple[int, list[str], list[tuple[str, int, str]]]:
    """`(walked, unparseable, offenders)` over `(path, source)` pairs.

    THE TREE ARM AND EVERY POSITIVE CONTROL GO THROUGH HERE. A control built as
    a parallel copy of the sweep grades the copy, so it can pass while the code
    the tree arm actually runs is dead. One entry point, two callers.
    """
    walked = 0
    unparseable: list[str] = []
    offenders: list[tuple[str, int, str]] = []
    for path, source in sources:
        try:
            offenders.extend(_out_of_scope_call_sites(source, path))
        except SyntaxError:
            unparseable.append(path)
            continue
        walked += 1
    return walked, unparseable, sorted(offenders)


def _sweep_population() -> list[str]:
    """The python files the premise is measured over, from `git ls-files`.

    `git ls-files`, ALWAYS, and never an `rglob`. `.claude/worktrees/` holds many
    stale copies of this tree and is ignored by `.gitignore:86` (`.claude/*`), so
    an `rglob` from the repo root reports content that is not the current tree's.
    This very test run is executing inside one of those worktree copies, which is
    what makes the distinction load-bearing rather than theoretical.

    `--cached --others --exclude-standard` is the population and not `--cached`
    alone. A brand new module that has not been `git add`ed yet is EXACTLY where a
    fresh `os.system` lands, and a tracked-only population would let it hide from
    this arm until somebody staged it. `--exclude-standard` is what keeps the
    ignored worktree copies out of the `--others` half.

    GATED. A git-less checkout is a shape this repository is routinely received
    in - Download ZIP, an sdist, a `git archive` extract - and there the
    population is simply UNKNOWABLE. A skip that names the missing repository is
    the honest answer; falling back to an `rglob` would answer a different
    question while reporting green.
    """
    require_git_repository()
    out = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *_ROOTS_THE_PREMISE_COVERS,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(
        {line for line in out.stdout.splitlines() if line.strip().endswith(".py")}
    )


def test_no_declared_out_of_scope_launcher_has_a_call_site_in_the_roots():
    """The census docstring's measured premise, RE-MEASURED EVERY RUN.

    This is the arm that makes "none has a call site in `DEFAULT_ROOTS`" a fact
    the suite holds rather than a sentence somebody typed once. It widens
    nothing: no launcher is added to the census and no row is emitted. It asserts
    the population is still zero, so the day an `os.system` call site arrives
    under one of these roots the suite goes RED and the docstring's narrow scope
    is re-decided on evidence.
    """
    assert census.DEFAULT_ROOTS == _ROOTS_THE_PREMISE_COVERS, (
        "the census's DEFAULT_ROOTS moved away from the literal this arm sweeps, "
        "so the premise is now a claim about a population this arm does not "
        f"measure. module: {census.DEFAULT_ROOTS}. literal here: "
        f"{_ROOTS_THE_PREMISE_COVERS}"
    )
    paths = _sweep_population()
    sources: list[tuple[str, str]] = []
    unreadable: list[str] = []
    for relative in paths:
        try:
            sources.append(
                (relative, (REPO_ROOT / relative).read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeDecodeError):
            unreadable.append(relative)
    walked, unparseable, offenders = _sweep(sources)
    assert walked >= _POPULATION_FLOOR, (
        f"only {walked} of {len(paths)} python files under "
        f"{_ROOTS_THE_PREMISE_COVERS} were parsed and walked, against a floor of "
        f"{_POPULATION_FLOOR}. A sweep over almost nothing finds almost nothing "
        "and still exits 0"
    )
    assert unreadable == [] and unparseable == [], (
        "the premise is UNMEASURED over these files and an unmeasured file "
        "reading as clean is the defect this arm exists to remove. unreadable: "
        f"{unreadable}. unparseable: {unparseable}"
    )
    assert offenders == [], (
        "the census docstring declares these names out of scope on the measured "
        "premise that NONE HAS A CALL SITE in DEFAULT_ROOTS, and that premise is "
        "now false. population: "
        f"{len(paths)} paths from `git ls-files --cached --others "
        f"--exclude-standard` over {_ROOTS_THE_PREMISE_COVERS}, of which {walked} "
        "parsed and were walked. node shapes that count: an ast.Call whose func "
        "is an Attribute whose receiver is a PLAIN SINGLE-SEGMENT Name bound to "
        "os or subprocess, or a bare Name bound by a from-import (alias "
        "included) or by a star import from either module. A DOTTED receiver - "
        "pkg.os.system(...) - is NOT among them and is a declared blind spot, "
        "so do not read this arm as having checked one. names: "
        f"{sorted(_DECLARED_OUT_OF_SCOPE['os'])} and "
        f"{sorted(_DECLARED_OUT_OF_SCOPE['subprocess'])}. offenders: {offenders}"
    )


def test_the_out_of_scope_sweep_finds_both_import_forms():
    """POSITIVE CONTROL. Without it the arm above is a gate that cannot fail.

    This tree has shipped a gate whose fixture excluded the very defect it was
    written for and stayed green on both sides of a real violation. The fixture
    here carries the Attribute form, the direct-import form, an aliased
    direct import, and three more out-of-scope spellings, and it runs through
    `_sweep` - the same entry point the tree arm calls.
    """
    walked, unparseable, offenders = _sweep(
        [("<fixture>", OUT_OF_SCOPE_BOTH_IMPORT_FORMS)]
    )
    assert (walked, unparseable) == (1, [])
    described = [entry[2] for entry in offenders]
    assert len(offenders) == 6, (
        "six call sites were counted by hand in this fixture and "
        f"{len(offenders)} were found: {offenders}"
    )
    for expected in (
        "os.system",
        "sh -> os.system",
        "getoutput -> subprocess.getoutput",
        "subprocess.getstatusoutput",
        "os.popen",
        "os.execvp",
    ):
        assert expected in described, (
            f"{expected} is in the fixture and the sweep did not report it, so "
            f"that spelling is invisible to the tree arm. reported: {described}"
        )


def test_the_out_of_scope_sweep_finds_a_star_import_call():
    walked, unparseable, offenders = _sweep(
        [("<fixture>", OUT_OF_SCOPE_STAR_IMPORT)]
    )
    assert (walked, unparseable) == (1, [])
    assert [entry[2] for entry in offenders] == ["system via a star import"], (
        "`from os import *` then `system(...)` launches a process and binds the "
        f"name through a form nothing can resolve. found: {offenders}"
    )


def test_the_out_of_scope_sweep_finds_an_aliased_module_receiver():
    walked, unparseable, offenders = _sweep(
        [("<fixture>", OUT_OF_SCOPE_MODULE_ALIAS)]
    )
    assert (walked, unparseable) == (1, [])
    assert [entry[2] for entry in offenders] == ["sp.getoutput"], (
        "`import subprocess as sp` then `sp.getoutput(...)` is the same call "
        f"under a different receiver spelling. found: {offenders}"
    )


def test_the_out_of_scope_sweep_leaves_legitimate_neighbours_alone():
    """THE SECOND GUARD. A sweep that flags everything has failed, not passed.

    Every line of this fixture names an out-of-scope spelling and none of them
    is a call to one. A sweep that reds here would red the tree arm on the real
    corpus - `tests/test_task_liveness.py` carries `getoutput` as a DICT KEY and
    the census docstring carries `os.system` as PROSE - and the arm above would
    then be measuring the sweep's appetite rather than the tree's contents.
    """
    walked, unparseable, offenders = _sweep(
        [("<fixture>", OUT_OF_SCOPE_NEIGHBOURS_THAT_MUST_SURVIVE)]
    )
    assert (walked, unparseable) == (1, [])
    assert offenders == [], (
        "not one line of this fixture calls an out-of-scope entry point - a "
        "regex pattern, a string literal, a dict key, an in-scope launcher, an "
        "os.path attribute, an attribute on a stranger, and a `system` imported "
        f"from `platform`. false positives: {offenders}"
    )


def test_the_out_of_scope_names_literal_is_not_derived_from_the_census():
    """The literal must be an INPUT, so it must not be the module's own set.

    `LAUNCHERS` is what the census DOES cover and `_DECLARED_OUT_OF_SCOPE` is
    what it declares it does NOT. If the two ever intersect, one of them has
    been edited into the other and this arm has started asserting that the
    census fails to see calls it in fact buckets.
    """
    declared = {
        spelling
        for spellings in _DECLARED_OUT_OF_SCOPE.values()
        for spelling in spellings
    }
    assert declared & census.LAUNCHERS == set(), (
        "a name is both covered and declared out of scope: "
        f"{sorted(declared & census.LAUNCHERS)}"
    )
    assert "startfile" not in declared, (
        "the census docstring does not declare os.startfile out of scope, so "
        "guarding it here would guard a claim nobody made"
    )


def test_every_declared_out_of_scope_name_is_pinned_in_both_directions():
    """PIN 1. The only arm here that makes a REMOVAL red, for any of the 22.

    Measured before it was written: deleting "spawnve" left this file green, and
    deleting all seventeen names no hand fixture spells left it green too, while
    ADDING an undeclared name was already red. A one-directional honesty arm
    reads exactly like a two-directional one until somebody deletes something.

    The expectation is hand-typed in DOTTED form so it is not a copy of the
    literal's shape - a reviewer comparing the two has to read names rather than
    scan an indent - and it is never derived from `_DECLARED_OUT_OF_SCOPE`,
    because a derived expectation shrinks in step with the mutant it exists to
    catch.
    """
    dotted = tuple(
        sorted(
            f"{module}.{spelling}"
            for module, spellings in _DECLARED_OUT_OF_SCOPE.items()
            for spelling in spellings
        )
    )
    removed = sorted(set(_EVERY_DECLARED_NAME_DOTTED) - set(dotted))
    added = sorted(set(dotted) - set(_EVERY_DECLARED_NAME_DOTTED))
    assert removed == [], (
        "a name was REMOVED from the declared-out-of-scope literal. The census "
        "docstring still declares it out of scope, so the sweep has quietly "
        "stopped looking for a spelling the module's own prose says it does not "
        f"cover: {removed}"
    )
    assert added == [], (
        "a name was ADDED to the declared-out-of-scope literal without being "
        "added here. Either the census docstring now declares it - in which case "
        "add it to this tuple too - or this arm has started guarding a claim "
        f"nobody made: {added}"
    )
    assert dotted == _EVERY_DECLARED_NAME_DOTTED, (
        "the two spellings of the declared name set hold the same names in a "
        f"different order. literal: {dotted}. expectation: "
        f"{_EVERY_DECLARED_NAME_DOTTED}"
    )


def test_every_exec_and_spawn_attribute_this_interpreter_has_is_declared():
    """PIN 2. An INDEPENDENT source for the family the docstring only names.

    The census docstring says "the `os` exec and spawn families" and enumerates
    none of them. The literal in this file enumerates 18, and the only way to
    check an expansion is against something that is neither the literal nor the
    module under test. `os` itself is that something.

    Platform-conditional by nature, and written for both platforms. Measured
    here: 12 `exec*` / `spawn*` attributes on `os`, all 12 declared. Six declared
    names are POSIX-only and absent here, so the residue is asserted as a SUBSET
    of a known set rather than as an equality - an equality would be green on
    Windows and red on CI's ubuntu-latest at the same commit, which is a shape
    this tree has already been bitten by.
    """
    present = {
        name
        for name in dir(os)
        if name.startswith(_OS_FAMILY_PREFIXES) and callable(getattr(os, name, None))
    }
    assert len(present) >= 12, (
        f"only {len(present)} exec/spawn attributes were found on `os`, against "
        "the 12 measured on this platform. A near-empty namespace reading as a "
        f"pass is zero out of zero. found: {sorted(present)}"
    )
    undeclared = sorted(present - _DECLARED_OUT_OF_SCOPE["os"])
    assert undeclared == [], (
        "the census docstring declares the os exec and spawn families out of "
        "scope, and these real `os` attributes fall inside that phrase while the "
        "literal in this file does not enumerate them, so the sweep does not "
        "look for them. Either add them here or narrow the docstring's phrase: "
        f"{undeclared}"
    )
    residue = {
        spelling
        for spelling in _DECLARED_OUT_OF_SCOPE["os"]
        if not hasattr(os, spelling)
    }
    unexplained = sorted(residue - _KNOWN_POSIX_ONLY_SPELLINGS)
    assert unexplained == [], (
        "a declared name is not an `os` attribute on this interpreter and is not "
        "one of the six known POSIX-only spellings, so it is most likely a typo "
        f"that no sweep will ever match: {unexplained}"
    )
    assert _KNOWN_POSIX_ONLY_SPELLINGS <= _DECLARED_OUT_OF_SCOPE["os"], (
        "a spelling this file calls POSIX-only is not in the declared set at "
        "all, so the exemption above is excusing a name nobody declared: "
        f"{sorted(_KNOWN_POSIX_ONLY_SPELLINGS - _DECLARED_OUT_OF_SCOPE['os'])}"
    )


def _per_name_call_site_sources() -> dict[str, str]:
    """PIN 3. One synthetic module per declared name, each with a real call.

    DERIVED from the literal on purpose, and therefore NOT a removal pin - a
    deleted name takes its generated source with it. What it pins is the SWEEP'S
    REACH: before this existed, only the five names a hand fixture happened to
    spell were ever put in front of the sweep, so the hand fixtures were built
    parallel to the implementation's own assumption about which names matter.
    """
    return {
        f"{module}.{spelling}": f"import {module}\n{module}.{spelling}('git status')\n"
        for module, spellings in _DECLARED_OUT_OF_SCOPE.items()
        for spelling in sorted(spellings)
    }


def test_the_sweep_finds_a_call_site_for_every_declared_name():
    """PIN 3's arm. Every one of the 22, not the 5 a hand fixture spells."""
    sources = _per_name_call_site_sources()
    expected_total = sum(
        len(spellings) for spellings in _DECLARED_OUT_OF_SCOPE.values()
    )
    assert len(sources) == expected_total >= 2, (
        f"{len(sources)} generated sources against {expected_total} declared "
        "names; a generator that collides two names measures fewer than it "
        "reports"
    )
    for dotted, source in sorted(sources.items()):
        walked, unparseable, offenders = _sweep([(f"<per-name:{dotted}>", source)])
        assert (walked, unparseable) == (1, []), (
            f"the generated source for {dotted} did not parse: {source!r}"
        )
        assert [entry[2] for entry in offenders] == [dotted], (
            f"{dotted} is declared out of scope and the sweep did not report a "
            "plain call to it, so that name is invisible to the tree arm. "
            f"source: {source!r}. found: {offenders}"
        )


def test_the_census_docstring_still_declares_what_this_literal_expands():
    """FINDING 4's SEAM. Two artifacts, one mechanism, nothing joining them.

    The census declares its out-of-scope names in prose - four spelled out and
    the rest folded into a family phrase - and the literal in this file expands
    that phrase to 18 names. Nothing compared the two, so a future edit that
    dropped a declaration would leave this file sweeping for a name the module no
    longer claims to exclude, in silence, on both sides of the seam at once.

    Whitespace is collapsed before the search so a re-wrap of the docstring is
    not a false red. The needles are hand-typed; reading them off the module
    would make this arm agree with whatever the module says today.
    """
    docstring = census.__doc__
    assert docstring, "the census module has no docstring to compare against"
    flat = " ".join(docstring.split())
    missing = [
        needle for needle in _LITERALLY_DECLARED_IN_THE_DOCSTRING if needle not in flat
    ]
    assert missing == [], (
        "the census docstring no longer declares these names out of scope, and "
        "this file still sweeps for them. A declaration dropped on one side of "
        "the seam and kept on the other is how the two artifacts disagree in "
        f"silence: {missing}"
    )
    assert _DECLARED_FAMILY_PHRASE in flat, (
        "the census docstring no longer carries the family phrase "
        f"{_DECLARED_FAMILY_PHRASE!r}, which is the ONLY declaration behind the "
        "18 exec and spawn names enumerated in `_DECLARED_OUT_OF_SCOPE`. Those "
        "names are now guarding a claim the module does not make"
    )


# ---------------------------------------------------------------------------
# THE BLIND SPOTS, DECLARED AND PINNED AS SILENCES
# ---------------------------------------------------------------------------
#
# THE RULE THIS TREE MEASURED: an instrument that does not name its own blind
# spots converts a negative reading into a FALSE CLAIM. The tree arm above
# reports zero offenders every run, and a reader is entitled to know what that
# zero is and is not a statement about.
#
# Every shape below was MEASURED silent against `_sweep` while GENUINELY
# LAUNCHING a process or naming a real launch API. None of them is a defect to be
# chased: static resolution cannot follow a rebind, and widening a mechanism to a
# population measured at zero is ruled against here. They are pinned as SILENCES
# instead - the same shape as `UNRESOLVABLE_RECEIVER_LAUNCHER_SPELLING` above -
# so the limit is a tested fact rather than a thing a future reader has to
# rediscover, and so a sweep that started reporting one of them is NOTICED rather
# than welcomed.
#
# TWO CLASSES, and the difference matters to whoever reads a zero.
#
# A  INDIRECT CALLEE. The target IS a declared out-of-scope name, reached through
#    a binding no static walk can resolve. Note that
#    `tools/git_subprocess_census.py` emits a ROW for the `getattr` shape -
#    `CallSite(bucket='UNRESOLVED', callee='<unresolved:Call>')` - so on that one
#    shape the grader in this file is WEAKER than the module it grades. That is
#    recorded rather than repaired: the census must bucket every call it walks,
#    and this sweep only has to answer one question about one name set.
#
# B  A LAUNCH API THE CENSUS DOCSTRING NEVER DECLARES. Not a blind spot against
#    the docstring's literal words - the docstring does not claim these - but a
#    CONTRACT GAP a reader could mistake for coverage. `os.startfile` is the
#    sharp one: a real Windows launch shape in a tree with an `ops/` lane, and
#    honestly omitted rather than covered. Measured over the five roots,
#    `os.startfile`, `asyncio.create_subprocess_shell`,
#    `asyncio.create_subprocess_exec`, `pty.spawn`, `os.fork` and `os.forkpty`
#    have ZERO call sites, so these are contract gaps and not live leaks.
#
# EXACTLY ONE LIST. Every registered shape is either covered or
# declared-uncovered and never both, which is the standard
# `tools/write_tracer.py` already sets here, and the partition is asserted below
# rather than trusted.
_DECLARED_BLIND_SPOTS: dict[str, str] = {
    "A: a dotted receiver": "import shim\nshim.os.system('git status')\n",
    "A: a dotted receiver spelled through os itself": (
        "import os\nos.path.system('git status')\n"
    ),
    "A: a name rebound to the attribute": (
        "import os\nrun = os.system\nrun('git status')\n"
    ),
    "A: getattr on the module": "import os\ngetattr(os, 'system')('git status')\n",
    "A: a subscript into the module __dict__": (
        "import os\nos.__dict__['system']('git status')\n"
    ),
    "A: a dict dispatch table": (
        "import os\nTABLE = {'go': os.system}\nTABLE['go']('git status')\n"
    ),
    "A: functools.partial around the attribute": (
        "import functools\nimport os\nfunctools.partial(os.system)('git status')\n"
    ),
    "A: importlib.import_module": (
        "import importlib\nimportlib.import_module('os').system('git status')\n"
    ),
    "A: the __import__ builtin": "__import__('os').system('git status')\n",
    "A: a conditional expression as the callee": (
        "import os\n"
        "def pick(flag, alt):\n"
        "    return (alt if flag else os.system)('git status')\n"
    ),
    "B: os.startfile, undeclared and a real Windows launch": (
        "import os\nos.startfile('build.bat')\n"
    ),
    "B: asyncio.create_subprocess_shell": (
        "import asyncio\n"
        "async def go():\n"
        "    await asyncio.create_subprocess_shell('git status')\n"
    ),
    "B: asyncio.create_subprocess_exec": (
        "import asyncio\n"
        "async def go():\n"
        "    await asyncio.create_subprocess_exec('git', 'status')\n"
    ),
    "B: pty.spawn": "import pty\npty.spawn(['git', 'status'])\n",
    "B: multiprocessing.Process().start()": (
        "import multiprocessing\nmultiprocessing.Process(target=None).start()\n"
    ),
    "B: os.fork": "import os\nif os.fork() == 0:\n    pass\n",
    "B: os.forkpty": "import os\npid, fd = os.forkpty()\n",
}

# The covered shapes, registered so the partition arm below has two halves to
# compare. These three hand fixtures plus the generated per-name sources are
# everything this sweep claims to see.
_COVERED_SHAPES: dict[str, str] = {
    "covered: attribute, direct import and alias forms": (
        OUT_OF_SCOPE_BOTH_IMPORT_FORMS
    ),
    "covered: star import": OUT_OF_SCOPE_STAR_IMPORT,
    "covered: aliased module receiver": OUT_OF_SCOPE_MODULE_ALIAS,
}


def test_every_declared_blind_spot_really_is_a_silence():
    """The zero the tree arm reports, bounded by what it cannot see.

    Each fixture here parses, holds at least one real `ast.Call`, and yields
    NOTHING. The call floor is the non-vacuity arm: a fixture with no call in it
    would pass this silently while asserting nothing at all, which is the exact
    shape of a gate whose fixture excludes its own defect.
    """
    assert len(_DECLARED_BLIND_SPOTS) >= 17, (
        f"only {len(_DECLARED_BLIND_SPOTS)} blind spots are registered against "
        "the 17 measured; a shrinking registry silently re-implies coverage"
    )
    for label, source in sorted(_DECLARED_BLIND_SPOTS.items()):
        calls = [
            node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
        ]
        assert calls, (
            f"the blind-spot fixture {label!r} holds no call at all, so the "
            f"silence it asserts is about nothing. source: {source!r}"
        )
        walked, unparseable, offenders = _sweep([(f"<blind:{label}>", source)])
        assert (walked, unparseable) == (1, []), (
            f"the blind-spot fixture {label!r} did not parse: {source!r}"
        )
        assert offenders == [], (
            f"{label} is DECLARED as a shape this sweep cannot see and the sweep "
            "now reports it. That is not a failure of the sweep - it is a "
            "declaration that has gone stale, so move the shape out of "
            f"`_DECLARED_BLIND_SPOTS` and into the covered list. found: {offenders}"
        )


def test_every_registered_shape_lands_in_exactly_one_list():
    """Covered or declared-uncovered, never both and never neither.

    A shape in both lists would have one arm asserting it is seen and another
    asserting it is not, and whichever ran second would be describing the
    other's subject. The two halves are compared by SOURCE as well as by label,
    because two different labels over one source string is the same defect
    wearing a different name.
    """
    covered = dict(_COVERED_SHAPES)
    covered.update(_per_name_call_site_sources())
    shared_labels = sorted(set(covered) & set(_DECLARED_BLIND_SPOTS))
    assert shared_labels == [], (
        f"a shape is registered as both covered and blind: {shared_labels}"
    )
    shared_sources = sorted(set(covered.values()) & set(_DECLARED_BLIND_SPOTS.values()))
    assert shared_sources == [], (
        "one source string is registered under both a covered label and a "
        f"blind-spot label: {shared_sources}"
    )
    for label, source in sorted(covered.items()):
        walked, unparseable, offenders = _sweep([(f"<covered:{label}>", source)])
        assert (walked, unparseable) == (1, []), (
            f"the covered fixture {label!r} did not parse: {source!r}"
        )
        assert offenders, (
            f"{label} is registered as a shape this sweep DOES see and it was "
            "not reported, so the covered list is overstating the reach. "
            f"source: {source!r}"
        )
