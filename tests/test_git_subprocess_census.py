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
from pathlib import Path

import pytest

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
    for name, source in sorted(globals().items()):
        if name.isupper() and isinstance(source, str) and "subprocess" in source:
            ast.parse(source)


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
