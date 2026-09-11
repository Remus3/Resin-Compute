"""An AST census of every subprocess call in this tree whose argv[0] is git.

WHY AN AST WALK AND NOT A GREP.

Two false-red figures were quoted in this tree - "8 red arms over 7 modules" and
a "5-module candidate list" - and both were produced by NAME-BASED ONE-TERM
FILTERS. The 5-module list was then measured and OVER-REPORTED: only three of
the five shell git at all. `tests/test_ci_history_depth.py` launches nothing -
its only `subprocess.run` text is a STRING LITERAL handed to a regex, which a
text filter cannot tell from a call - and `tests/test_guard_worktree_blindness.py`
has no subprocess call anywhere. A skip added to either would have been a FALSE
SKIP with no defect behind it.

An AST walk never parses the contents of a string literal, so the string-in-a-
regex shape is structurally invisible to it. That is the whole point.

THREE BUCKETS, NEVER TWO.

  GIT         argv[0] statically resolves to a git executable
  NOT-GIT     argv[0] statically resolves to something that is not git
  UNRESOLVED  argv[0] is a parameter, a call, an f-string, a rebound name, a
              starred splat, an empty sequence - OR THE CALLEE ITSELF cannot be
              resolved, so whether this is a call into subprocess at all is
              unknown. Anything this module cannot answer at parse time

The UNRESOLVED bucket is the honest part. A census that silently folds what it
cannot resolve into NOT-GIT, or drops it, has reproduced the very defect this
module exists to kill: a confident number whose denominator was never checked.

AN UNRESOLVABLE CALLEE IS A ROW, NOT A SILENCE.

`_launcher_for` used to branch on `ast.Attribute` and `ast.Name` and return None
for everything else, which meant NO ROW AT ALL when `call.func` was itself a
call - `getattr(subprocess, "run")(...)`, `functools.partial(subprocess.run)(...)`,
a factory handing back a stub shaped exactly like `subprocess.run`. Silence, and
a conservation assertion cannot catch silence because there is nothing left to
conserve. The repair is SUBTRACTIVE, the same shape as `_outer_positions`: a
func that is neither an Attribute nor a Name is unresolvable and says so, which
also covers an `ast.Subscript` dispatch table and an `ast.BoolOp` picking an
injected callable over a default without either having to be enumerated.

An Attribute func whose RECEIVER does not resolve stays a silence. That was
measured before it was decided: over `DEFAULT_ROOTS` there are hundreds of
Attribute callees with an unresolvable receiver and not one of them is spelled
like a subprocess entry point, so a rule keyed on the attribute name would have
added rows to this census that no call site in this tree can reach. An arm for
an unreachable rule is decoration, and this tree has ruled against widening a
mechanism to a population measured at zero more than once.

This widening is a CONTRACT-HONESTY repair and not a leak fix. Every
func-is-a-call site in this tree was measured to be a stub or predicate
invocation and none launches a process. What was broken was this module's claim
to see every call it buckets.

WHAT THIS CENSUS DOES NOT COVER, DECLARED RATHER THAN IMPLIED.

`LAUNCHERS` is the five `subprocess` entry points below and nothing else, so
`subprocess.getoutput` and `subprocess.getstatusoutput` are outside this
census by construction even though both start a process. `os.system`,
`os.popen` and the `os` exec and spawn families are outside it too. None of
those is a leak in this tree - none has a call site in `DEFAULT_ROOTS` - and
that is exactly why the population is left where it is rather than widened to
cover a shape nothing here uses. The title of this module is narrow on purpose:
it says SUBPROCESS CALL and not PROCESS LAUNCH, because the wider word would be
a claim these names disprove.

POSITIONS THAT ARE NOT A STATEMENT BODY.

A call can sit in a decorator expression, a default argument, an annotation or
a class base. Every one of those is evaluated in the ENCLOSING scope at
definition time, and none of them is reachable by recursing into a scope node's
`body` - which is all this module used to do, so every such call was DROPPED and
produced no row at all. A dropped row is worse than a misbucketed one: a wrong
row is arguable, a missing row is invisible. `_outer_positions` therefore
derives those positions by SUBTRACTING the body from `ast.iter_child_nodes`
rather than naming them one by one, so a position nobody enumerated is walked
anyway.

SHELL=TRUE CHANGES WHAT ARGV[0] MEANS.

`subprocess.run(["git log -n 1"], shell=True)` launches git. Under `shell=True`
element 0 of a list IS the command string on POSIX - the remaining elements
become the shell's own positional arguments - while on Windows the list is
joined by `list2cmdline` and handed to `cmd.exe`, where the leading token is
still the executable. Both readings put the command in the FIRST SHELL WORD of
element 0, and that shared reading is the only thing modelled here; this module
does NOT model either platform's full argument semantics beyond argv[0]. Where
`shell=` is not a literal, both readings are computed and a DISAGREEMENT between
them is recorded UNRESOLVED rather than guessed.

THE GUARD COLUMN IS A BLIND SPOT, DECLARED AS ONE.

Each site carries GATED or UNKNOWN. GATED means the module textually references
one of this tree's git-presence gates. UNKNOWN means this module could not see
one, and it means NOTHING MORE THAN THAT. This tree has been bitten by the
opposite reading: an AST walk for a `try` block directly containing the call is
STRUCTURALLY BLIND to a guard placed at the CALLER, and the caller is exactly
where this tree puts them. So UNKNOWN is never to be read as unguarded, and
there is deliberately no token in this file that says otherwise.

THIS IS A CENSUS TOOL AND NOT A GATE. `main()` prints and returns 0. Sizing a
repair is a separate decision from enumerating the population, and conflating
the two is how the over-reported list got quoted in the first place.

Usage:
    python -m tools.git_subprocess_census
    python tools/git_subprocess_census.py tests tools
"""

from __future__ import annotations

import argparse
import ast
import shlex
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_ROOTS: tuple[str, ...] = ("tests", "tools", "ops", "headless", "scripts")

GIT = "GIT"
NOT_GIT = "NOT-GIT"
UNRESOLVED = "UNRESOLVED"
BUCKETS: tuple[str, ...] = (GIT, NOT_GIT, UNRESOLVED)

GATED = "GATED"
GUARD_UNKNOWN = "UNKNOWN"

# The five subprocess entry points that actually launch a process. `Popen` is
# included because a long-lived handle shells git exactly as much as `run` does.
# See the module docstring for what this set deliberately leaves out.
LAUNCHERS = frozenset({"run", "check_output", "check_call", "call", "Popen"})

# The callee column for a row whose callee could not be resolved. The node kind
# is appended so the report says WHAT was unresolvable rather than only that
# something was.
UNRESOLVED_CALLEE_PREFIX = "<unresolved:"

# This tree's git-presence gates, defined in `tests/conftest.py`. A module that
# names any of them is recorded GATED.
GUARD_NAMES = frozenset(
    {
        "require_git_repository",
        "skip_module_without_git",
        "git_unusable_reason",
        "classify_git_probe",
    }
)

# The ONLY dotted name resolved to a verdict. `sys.executable` is the running
# interpreter by definition and can never be git, so folding it into UNRESOLVED
# would inflate the unknown bucket with a case that is in fact known. Every
# other attribute or name stays UNRESOLVED.
NEVER_GIT_DOTTED = frozenset({"sys.executable"})

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)

# A name present in a scope map with value None is AMBIGUOUS - bound more than
# once, bound by a loop or a `with`, or a parameter - and is distinct from a
# name that is absent, which is simply not bound in any visible scope.
_Bindings = dict[str, "ast.expr | None"]


@dataclass(frozen=True)
class CallSite:
    """One call site this census could or could not resolve.

    A row is NOT a claim that a process starts here. A resolved row names a
    subprocess entry point; an UNRESOLVED row may name a callee this module
    could not read at all, which is precisely why it is a row rather than a
    silence.
    """

    path: str
    lineno: int
    col: int
    callee: str
    bucket: str
    argv0: str
    guard: str

    def render(self) -> str:
        return (
            f"{self.path}:{self.lineno}:{self.col}  {self.bucket:<10} "
            f"{self.callee:<24} guard={self.guard:<7} argv0={self.argv0}"
        )


def _dotted(node: ast.AST) -> str | None:
    """`sys.executable` for an Attribute chain of plain Names, else None."""
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _is_git_executable(text: str, *, shell_string: bool) -> bool:
    """Whether a literal argv[0] names git.

    Handles a bare `git`, a `git.exe` and an absolute POSIX or Windows path to
    either.

    `shell_string` is the WHOLE-COMMAND form passed under `shell=True`, such as
    `git log -n 1`, where only the first shell word is the executable. It is the
    only form that may be split on whitespace. Splitting a LIST ELEMENT instead
    cuts `C:\\Program Files\\Git\\bin\\git.exe` at `C:\\Program` and reports a
    false NOT-GIT - the same class of error as the name filter this census
    replaces - so the two cases are separated here rather than guessed at.
    Quoting is honoured through `shlex` so a quoted path survives the split.
    """
    stripped = text.strip()
    if not stripped:
        return False
    if shell_string:
        try:
            tokens = shlex.split(stripped, posix=False)
        except ValueError:
            tokens = stripped.split()
        if not tokens:
            return False
        first = tokens[0].strip("\"'")
    else:
        first = stripped
    base = first.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base.lower() == "git"


def _iter_shallow(body: Sequence[ast.AST]) -> Iterator[ast.AST]:
    """Every node reachable from these statements WITHOUT entering a new scope.

    A nested function or lambda is yielded so the caller can recurse into it
    deliberately, but is never descended into here. That is what makes a
    parameter able to shadow a module-level constant rather than resolve
    through to it.
    """
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, _SCOPE_NODES):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _target_names(target: ast.AST) -> Iterator[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _target_names(element)
    elif isinstance(target, ast.Starred):
        yield from _target_names(target.value)


def _bind(bindings: _Bindings, name: str, value: ast.expr | None) -> None:
    """Record a binding. A second binding of the same name makes it ambiguous."""
    bindings[name] = None if name in bindings else value


def _bindings_of(body: Sequence[ast.AST], seed: Iterable[str] = ()) -> _Bindings:
    """Names bound in one scope, mapped to their value where it is single.

    `seed` carries the enclosing function's parameters, which must shadow any
    outer name of the same spelling and are never statically resolvable.
    """
    bindings: _Bindings = {}
    for name in seed:
        bindings[name] = None
    for node in _iter_shallow(body):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for name in _target_names(target):
                    _bind(bindings, name, node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                _bind(bindings, node.target.id, node.value)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                bindings[node.target.id] = None
        elif isinstance(node, ast.NamedExpr):
            _bind(bindings, node.target.id, node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for name in _target_names(node.target):
                bindings[name] = None
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                for name in _target_names(node.optional_vars):
                    bindings[name] = None
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                bindings[node.name] = None
    return bindings


def _parameter_names(node: ast.AST) -> list[str]:
    args = getattr(node, "args", None)
    if not isinstance(args, ast.arguments):
        return []
    collected = [
        *args.posonlyargs,
        *args.args,
        *args.kwonlyargs,
    ]
    names = [arg.arg for arg in collected]
    if args.vararg is not None:
        names.append(args.vararg.arg)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    return names


def _lookup(name: str, chain: Sequence[_Bindings]) -> tuple[bool, ast.expr | None]:
    """(found, value). A found name with value None is ambiguous, not missing."""
    for scope in reversed(chain):
        if name in scope:
            return True, scope[name]
    return False, None


@dataclass(frozen=True)
class _Imports:
    """What the module's imports say `subprocess` is called here."""

    subprocess_bases: frozenset[str]
    subprocess_direct: dict[str, str]


def _import_aliases(tree: ast.AST) -> _Imports:
    """Module bases that mean `subprocess`, and bare names bound to a launcher.

    Imports are collected across the whole tree rather than top-level only,
    because a `from subprocess import run` inside a function body is a real
    shape and skipping it would under-report.
    """
    sub_bases = {"subprocess"}
    sub_direct: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.asname:
                    continue
                if alias.name == "subprocess":
                    sub_bases.add(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                for alias in node.names:
                    if alias.name in LAUNCHERS:
                        sub_direct[alias.asname or alias.name] = alias.name
    return _Imports(
        subprocess_bases=frozenset(sub_bases),
        subprocess_direct=sub_direct,
    )


_KIND_SUBPROCESS = "subprocess"
_KIND_OPAQUE = "opaque"


@dataclass(frozen=True)
class _Launch:
    """One resolved-or-not callee, and why it could not be resolved."""

    callee: str
    kind: str
    reason: str = ""


def _opaque_launch(func: ast.expr, reason: str) -> _Launch:
    return _Launch(
        callee=f"{UNRESOLVED_CALLEE_PREFIX}{type(func).__name__}>",
        kind=_KIND_OPAQUE,
        reason=reason,
    )


def _launcher_for(call: ast.Call, imports: _Imports) -> _Launch | None:
    """The launcher this call reaches, or None where it reaches none.

    None is a POSITIVE not-a-launch answer and is only ever returned where the
    callee actually resolved. Where it did not, the answer is an opaque callee
    that becomes an UNRESOLVED row - see the module docstring.
    """
    func = call.func
    if isinstance(func, ast.Attribute):
        receiver = _dotted(func.value)
        if receiver is None:
            return None
        if func.attr in LAUNCHERS and receiver in imports.subprocess_bases:
            return _Launch(callee=f"subprocess.{func.attr}", kind=_KIND_SUBPROCESS)
        return None
    if isinstance(func, ast.Name):
        target = imports.subprocess_direct.get(func.id)
        if target is not None:
            return _Launch(callee=f"subprocess.{target}", kind=_KIND_SUBPROCESS)
        return None
    return _opaque_launch(
        func,
        f"callee is a {type(func).__name__} expression, so whether this is a "
        "subprocess entry point at all is unknowable at parse time",
    )


def _verdict_for_text(text: str, *, shell_string: bool) -> tuple[str, str]:
    bucket = GIT if _is_git_executable(text, shell_string=shell_string) else NOT_GIT
    return bucket, repr(text)


def _shell_flag(call: ast.Call) -> bool | None:
    """Whether `shell=` is literally true, literally false, or not knowable.

    None is the honest third answer: a `**kwargs` splat or a computed flag can
    carry `shell=True` at runtime, and assuming either way would decide a
    bucket on a guess.
    """
    for keyword in call.keywords:
        if keyword.arg is None:
            return None
        if keyword.arg != "shell":
            continue
        value = keyword.value
        if isinstance(value, ast.Constant) and isinstance(value.value, (bool, int)):
            return bool(value.value)
        if isinstance(value, ast.Constant) and value.value is None:
            return False
        return None
    return False


def _head_verdict(text: str, *, shell: bool | None) -> tuple[str, str]:
    """Bucket a LITERAL argv[0] taken from a sequence element.

    Under `shell=True` element 0 carries the whole command, so only its first
    shell word is the executable - `git log -n 1` is a git launch. Without
    `shell=True` the same bytes name one executable whose name contains spaces,
    which is not git, and splitting it would cut an absolute path with a space
    in it at the space and report a false NOT-GIT. When `shell=` cannot be
    resolved the two readings are compared, and a disagreement is UNRESOLVED.
    """
    as_shell = _is_git_executable(text, shell_string=True)
    as_path = _is_git_executable(text, shell_string=False)
    if shell is True:
        return (GIT if as_shell else NOT_GIT), repr(text)
    if shell is False:
        return (GIT if as_path else NOT_GIT), repr(text)
    if as_shell == as_path:
        return (GIT if as_shell else NOT_GIT), repr(text)
    return (
        UNRESOLVED,
        f"shell= not statically known and argv[0] {text!r} reads both ways",
    )


def _resolve_head(
    node: ast.expr,
    chain: Sequence[_Bindings],
    seen: set[str],
    *,
    shell: bool | None,
) -> tuple[str, str]:
    """Classify the FIRST ELEMENT of an argv sequence."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _head_verdict(node.value, shell=shell)
    if isinstance(node, ast.JoinedStr):
        return UNRESOLVED, "f-string argv[0]"
    if isinstance(node, ast.Starred):
        return UNRESOLVED, "starred argv[0]"
    if isinstance(node, ast.Name):
        if node.id in seen:
            return UNRESOLVED, f"self-referential binding {node.id!r}"
        seen.add(node.id)
        found, value = _lookup(node.id, chain)
        if not found:
            return UNRESOLVED, f"name {node.id!r} not statically bound"
        if value is None:
            return UNRESOLVED, f"name {node.id!r} rebound or non-literal"
        return _resolve_head(value, chain, seen, shell=shell)
    dotted = _dotted(node)
    if dotted in NEVER_GIT_DOTTED:
        return NOT_GIT, dotted or ""
    if dotted is not None:
        return UNRESOLVED, f"dotted name {dotted}"
    return UNRESOLVED, f"{type(node).__name__} argv[0]"


def _resolve_argv(
    node: ast.expr,
    chain: Sequence[_Bindings],
    seen: set[str],
    *,
    shell: bool | None,
) -> tuple[str, str]:
    """Classify the whole argv expression handed to a launcher."""
    if isinstance(node, (ast.List, ast.Tuple)):
        if not node.elts:
            return UNRESOLVED, "empty argv sequence"
        return _resolve_head(node.elts[0], chain, seen, shell=shell)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        # A bare string argv is the whole-command form on Windows and under
        # shell=True, so its first shell word is the executable either way.
        return _verdict_for_text(node.value, shell_string=True)
    if isinstance(node, ast.JoinedStr):
        return UNRESOLVED, "f-string argv"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # A literal head concatenated with a dynamic tail: argv[0] is knowable.
        return _resolve_argv(node.left, chain, seen, shell=shell)
    if isinstance(node, ast.Name):
        if node.id in seen:
            return UNRESOLVED, f"self-referential binding {node.id!r}"
        seen.add(node.id)
        found, value = _lookup(node.id, chain)
        if not found:
            return UNRESOLVED, f"name {node.id!r} not statically bound"
        if value is None:
            return UNRESOLVED, f"name {node.id!r} rebound or non-literal"
        return _resolve_argv(value, chain, seen, shell=shell)
    dotted = _dotted(node)
    if dotted in NEVER_GIT_DOTTED:
        return NOT_GIT, dotted or ""
    if dotted is not None:
        return UNRESOLVED, f"dotted name {dotted}"
    return UNRESOLVED, f"{type(node).__name__} argv"


def _argv_expression(call: ast.Call) -> ast.expr | None:
    """The argv expression, whether passed positionally or as `args=`."""
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg == "args":
            return keyword.value
    return None


def _guard_of(tree: ast.AST) -> str:
    """GATED if the module names a git gate. UNKNOWN means only that."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in GUARD_NAMES:
            return GATED
        if isinstance(node, ast.Attribute) and node.attr in GUARD_NAMES:
            return GATED
        if isinstance(node, ast.alias):
            if node.name in GUARD_NAMES or (node.asname or "") in GUARD_NAMES:
                return GATED
    return GUARD_UNKNOWN


def _scope_body(node: ast.AST) -> list[ast.AST]:
    """The statements of a scope node. A lambda's body is one expression."""
    body = getattr(node, "body", [])
    return list(body) if isinstance(body, list) else [body]


def _outer_positions(node: ast.AST) -> list[ast.AST]:
    """Every child of a scope node that is NOT part of its body.

    Decorator expressions, default arguments, annotations and class bases live
    here. They are evaluated in the ENCLOSING scope, so they are walked with
    the enclosing binding chain and never with the nested one. Subtracting the
    body from `ast.iter_child_nodes` rather than naming these positions one by
    one is what stops a position nobody thought of from being dropped.
    """
    body_ids = {id(child) for child in _scope_body(node)}
    return [child for child in ast.iter_child_nodes(node) if id(child) not in body_ids]


def _bucket_for(
    call: ast.Call, launch: _Launch, scopes: Sequence[_Bindings]
) -> tuple[str, str]:
    """The bucket and the argv0 column for one call site."""
    if launch.kind == _KIND_OPAQUE:
        return UNRESOLVED, launch.reason
    argv = _argv_expression(call)
    if argv is None:
        return UNRESOLVED, "no statically visible argv"
    return _resolve_argv(argv, scopes, set(), shell=_shell_flag(call))


def _walk_nodes(
    nodes: Sequence[ast.AST],
    scopes: list[_Bindings],
    path: str,
    guard: str,
    imports: _Imports,
    out: list[CallSite],
) -> None:
    """Record every call site reachable from `nodes` under one binding chain."""
    for node in _iter_shallow(nodes):
        if isinstance(node, ast.Call):
            launch = _launcher_for(node, imports)
            if launch is None:
                continue
            bucket, described = _bucket_for(node, launch, scopes)
            out.append(
                CallSite(
                    path=path,
                    lineno=node.lineno,
                    col=node.col_offset,
                    callee=launch.callee,
                    bucket=bucket,
                    argv0=described,
                    guard=guard,
                )
            )
        elif isinstance(node, _SCOPE_NODES):
            _walk_nodes(_outer_positions(node), scopes, path, guard, imports, out)
            _walk_scope(
                _scope_body(node),
                scopes,
                path,
                guard,
                imports,
                out,
                _parameter_names(node),
            )


def _walk_scope(
    body: Sequence[ast.AST],
    chain: list[_Bindings],
    path: str,
    guard: str,
    imports: _Imports,
    out: list[CallSite],
    seed: Iterable[str] = (),
) -> None:
    scopes = [*chain, _bindings_of(body, seed)]
    _walk_nodes(body, scopes, path, guard, imports, out)


def census_source(source: str, path: str) -> list[CallSite]:
    """Every call site this census could or could not resolve, in one source."""
    tree = ast.parse(source)
    imports = _import_aliases(tree)
    guard = _guard_of(tree)
    out: list[CallSite] = []
    _walk_scope(tree.body, [], path, guard, imports, out)
    out.sort(key=lambda site: (site.lineno, site.col))
    return out


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and ".git" not in path.parts
    )


def census_paths(roots: Iterable[str], repo_root: Path) -> list[CallSite]:
    """The census over whole directories, keyed by repo-relative posix path."""
    out: list[CallSite] = []
    for name in roots:
        directory = repo_root / name
        if not directory.is_dir():
            continue
        for path in _python_files(directory):
            relative = path.relative_to(repo_root).as_posix()
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                out.append(
                    CallSite(
                        path=relative,
                        lineno=0,
                        col=0,
                        callee="<unreadable>",
                        bucket=UNRESOLVED,
                        argv0=f"{type(exc).__name__}: {exc}",
                        guard=GUARD_UNKNOWN,
                    )
                )
                continue
            try:
                out.extend(census_source(source, relative))
            except SyntaxError as exc:
                out.append(
                    CallSite(
                        path=relative,
                        lineno=exc.lineno or 0,
                        col=exc.offset or 0,
                        callee="<unparseable>",
                        bucket=UNRESOLVED,
                        argv0=f"SyntaxError: {exc.msg}",
                        guard=GUARD_UNKNOWN,
                    )
                )
    out.sort(key=lambda site: (site.path, site.lineno, site.col))
    return out


def counts(sites: Iterable[CallSite]) -> dict[str, int]:
    """A tally with ALL THREE buckets present, including the empty ones."""
    tally = dict.fromkeys(BUCKETS, 0)
    for site in sites:
        tally[site.bucket] = tally.get(site.bucket, 0) + 1
    return tally


def format_report(sites: Sequence[CallSite]) -> str:
    tally = counts(sites)
    lines: list[str] = []
    lines.append("git subprocess census - AST enumeration, three buckets")
    lines.append("")
    # NOT "launch sites". The population includes rows whose callee this module
    # could not resolve at all, and calling those launches would be a claim the
    # UNRESOLVED bucket exists precisely to refuse.
    lines.append(f"total call sites : {len(sites)}")
    for bucket in BUCKETS:
        lines.append(f"  {bucket:<10} : {tally[bucket]}")
    lines.append("")
    lines.append(
        "guard column: GATED means the module names a git gate. UNKNOWN means this"
    )
    lines.append(
        "census could not see one AND NOTHING MORE - a guard at the caller is"
    )
    lines.append("invisible to an AST walk rooted at the call.")
    for bucket in BUCKETS:
        selected = [site for site in sites if site.bucket == bucket]
        lines.append("")
        lines.append(f"--- {bucket} ({len(selected)}) ---")
        if not selected:
            lines.append("  (none)")
            continue
        for site in selected:
            lines.append("  " + site.render())
    files = sorted({site.path for site in sites if site.bucket == GIT})
    lines.append("")
    lines.append(f"--- files with at least one GIT site ({len(files)}) ---")
    for name in files:
        lines.append(f"  {name}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enumerate every subprocess call whose argv[0] is git, plus every "
            "call whose callee could not be resolved. A census, not a gate: it "
            "always exits 0."
        )
    )
    parser.add_argument(
        "roots",
        nargs="*",
        default=list(DEFAULT_ROOTS),
        help="directories to walk, relative to the repo root",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="repository root the roots are resolved against",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    roots = args.roots or list(DEFAULT_ROOTS)
    sites = census_paths(roots, Path(args.repo_root).resolve())
    print(format_report(sites))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
