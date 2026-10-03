"""tests/test_precommit_gate_message.py - the two MESSAGE halves judge what lands.

`git commit -F <file>` and `-m` default to `--cleanup=whitespace`, which KEEPS a
line starting with `#`. Both message halves used to skip such lines as
"template comments", so a `#` line carrying an em-dash reached history and a
`#` first line bypassed the subject check. Measured 2026-10-03 on
git 2.53.0.windows.3; the measured table is in `tests/test_hook_gate.py`
beside the end-to-end arms.

These arms are pure: no git is launched. The decision function takes its
environment and its config reader as arguments, so every row of the decision
table is driven directly, including the ones this host cannot easily produce.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import precommit_gate

REPO_ROOT = Path(__file__).resolve().parents[1]
EM_DASH = chr(0x2014)


def _load_msg_check():
    spec = importlib.util.spec_from_file_location(
        "precommit_msg_check_under_test", REPO_ROOT / "scripts" / "precommit_msg_check.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


msg_check = _load_msg_check()

IN_HOOK_NO_EDITOR = {"GIT_INDEX_FILE": ".git/index", "GIT_EDITOR": ":"}
IN_HOOK_EDITOR = {"GIT_INDEX_FILE": ".git/index", "GIT_EDITOR": "vi"}
IN_HOOK_EDITOR_UNSET = {"GIT_INDEX_FILE": ".git/index"}


def _config(values: dict[str, str]):
    def read(key: str) -> str | None:
        return values.get(key)

    return read


def _broken_config(key: str) -> str | None:
    raise msg_check.ConfigUnreadable(key)


# ---------------------------------------------------------------------------
# The decision table: will git strip `#` lines from this commit?
# ---------------------------------------------------------------------------


# Git's editor template, typed here as LITERALS and not imported from the
# module, so a mutated constant there cannot move this side with it. Measured
# 2026-10-03 on git 2.53.0.windows.3; the end-to-end arms in
# `tests/test_hook_gate.py` prove git still writes these bytes.
STRIP_HINT = (
    "# Please enter the commit message for your changes. Lines starting\n"
    "# with '#' will be ignored, and an empty message aborts the commit.\n"
)
KEEP_HINT = (
    "# Please enter the commit message for your changes. Lines starting\n"
    "# with '#' will be kept; you may remove them yourself if you want to.\n"
    "# An empty message aborts the commit.\n"
)
STATUS = "#\n# On branch main\n# Changes to be committed:\n#\tmodified:   a\n#\n"
STRIP_TEMPLATE = "\n" + STRIP_HINT + STATUS
KEEP_TEMPLATE = "\n" + KEEP_HINT + STATUS
SCISSORS_TEMPLATE = (
    "\n# ------------------------ >8 ------------------------\n"
    "# Do not modify or remove the line above.\n"
    "# Everything below it will be ignored.\n" + STATUS
)
MERGE_TEMPLATE = (
    "Merge branch 'side'\n"
    "# Please enter a commit message to explain why this merge is necessary,\n"
    "# especially if it merges an updated upstream into a topic branch.\n"
    "#\n"
    "# Lines starting with '#' will be ignored, and an empty message aborts\n"
    "# the commit.\n"
)
AUTHORED = "feat: real\n# a line of mine\n"


@pytest.mark.parametrize(
    ("env", "config", "message", "stripped"),
    [
        # -F / -m: git exports GIT_EDITOR=: and the default cleanup keeps `#`.
        # No template is written, so config alone decides.
        (IN_HOOK_NO_EDITOR, {}, AUTHORED, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "default"}, AUTHORED, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "whitespace"}, AUTHORED, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "verbatim"}, AUTHORED, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "scissors"}, AUTHORED, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "strip"}, AUTHORED, True),
        # Case-insensitive, as git parses it.
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "STRIP"}, AUTHORED, True),
        # Unknown mode: fail closed.
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "frobnicate"}, AUTHORED, False),
        # A pasted strip sentence is not trusted without an editor.
        (IN_HOOK_NO_EDITOR, {}, AUTHORED + STRIP_TEMPLATE, False),
        # Editor: git's template carries the EFFECTIVE mode, flag applied.
        (IN_HOOK_EDITOR, {}, AUTHORED + STRIP_TEMPLATE, True),
        (IN_HOOK_EDITOR_UNSET, {}, AUTHORED + STRIP_TEMPLATE, True),
        (IN_HOOK_EDITOR, {"commit.cleanup": "default"}, AUTHORED + STRIP_TEMPLATE, True),
        # --cleanup=strip on the command line over a keeping config.
        (IN_HOOK_EDITOR, {"commit.cleanup": "whitespace"}, AUTHORED + STRIP_TEMPLATE, True),
        # --cleanup=whitespace|verbatim on the command line: THE GAP this closes.
        (IN_HOOK_EDITOR, {}, AUTHORED + KEEP_TEMPLATE, False),
        (IN_HOOK_EDITOR, {"commit.cleanup": "strip"}, AUTHORED + KEEP_TEMPLATE, False),
        # An amend can carry an old landed strip sentence; the keep one wins.
        (IN_HOOK_EDITOR, {}, AUTHORED + STRIP_HINT + KEEP_TEMPLATE, False),
        # Scissors keeps `#` lines above its marker, measured in editor mode.
        (IN_HOOK_EDITOR, {}, AUTHORED + SCISSORS_TEMPLATE, False),
        # --no-status writes no template at all: unknown, fail closed.
        (IN_HOOK_EDITOR, {}, AUTHORED, False),
        # git merge --edit says "ignored" even under verbatim: not a signal.
        (IN_HOOK_EDITOR, {}, MERGE_TEMPLATE, False),
        # Half a sentence is not the sentence.
        (IN_HOOK_EDITOR, {}, AUTHORED + STRIP_HINT.splitlines()[0] + "\n" + STATUS, False),
        (IN_HOOK_EDITOR, {}, AUTHORED + STRIP_HINT.splitlines()[1] + "\n" + STATUS, False),
        # CRLF from an editor on Windows is still the sentence.
        (IN_HOOK_EDITOR, {}, (AUTHORED + STRIP_TEMPLATE).replace("\n", "\r\n"), True),
        # No message reachable at all: fail closed.
        (IN_HOOK_EDITOR, {}, None, False),
        # A comment character other than `#` means `#` is ordinary content.
        (IN_HOOK_EDITOR, {"core.commentChar": ";"}, AUTHORED + STRIP_TEMPLATE, False),
        (IN_HOOK_EDITOR, {"core.commentChar": "auto"}, AUTHORED + STRIP_TEMPLATE, False),
        (IN_HOOK_EDITOR, {"core.commentString": "//"}, AUTHORED + STRIP_TEMPLATE, False),
        (IN_HOOK_EDITOR, {"core.commentChar": "#"}, AUTHORED + STRIP_TEMPLATE, True),
        # Not inside a git commit hook at all: nothing is known, fail closed.
        ({}, {}, AUTHORED + STRIP_TEMPLATE, False),
        ({"GIT_EDITOR": "vi"}, {"commit.cleanup": "strip"}, AUTHORED + STRIP_TEMPLATE, False),
    ],
)
def test_the_cleanup_decision_table(env, config, message, stripped):
    assert msg_check.hash_lines_are_stripped(env, _config(config), message) is stripped


def test_the_message_is_read_from_the_path_the_hook_exports(tmp_path):
    """The glyph half calls the predicate with no message; the hook exports
    the path git handed it, and that file is what is read."""
    f = tmp_path / "COMMIT_EDITMSG"
    f.write_bytes((AUTHORED + STRIP_TEMPLATE).encode("ascii"))
    env = dict(IN_HOOK_EDITOR, RESIN_COMMIT_MSG_FILE=str(f))
    assert msg_check.hash_lines_are_stripped(env, _config({})) is True
    f.write_bytes((AUTHORED + KEEP_TEMPLATE).encode("ascii"))
    assert msg_check.hash_lines_are_stripped(env, _config({})) is False


def test_a_missing_exported_path_fails_closed(tmp_path):
    env = dict(IN_HOOK_EDITOR, RESIN_COMMIT_MSG_FILE=str(tmp_path / "absent"))
    assert msg_check.hash_lines_are_stripped(env, _config({})) is False


def test_the_hook_exports_the_message_path_before_both_scripts():
    """Without the export the glyph half sees no template and fails closed on
    every editor commit - the five false blocks of 8436e68 come back."""
    hook = (REPO_ROOT / ".githooks" / "commit-msg").read_text(encoding="utf-8")
    export_at = hook.find("export RESIN_COMMIT_MSG_FILE")
    assert 'RESIN_COMMIT_MSG_FILE="$1"' in hook and export_at != -1
    assert export_at < hook.index("precommit_gate.py") < hook.index("precommit_msg_check.py")


def test_an_unreadable_config_fails_closed():
    assert msg_check.hash_lines_are_stripped(IN_HOOK_EDITOR, _broken_config) is False


# ---------------------------------------------------------------------------
# The subject reader
# ---------------------------------------------------------------------------


def test_a_hash_first_line_is_the_subject_when_git_keeps_it(tmp_path):
    f = tmp_path / "msg"
    f.write_bytes(b"# not conventional\nfeat: real\n")
    assert msg_check._read_subject(f, hash_is_content=True) == "# not conventional"


def test_a_hash_first_line_is_skipped_when_git_strips_it(tmp_path):
    f = tmp_path / "msg"
    f.write_bytes(b"# This is a combination of 2 commits.\n\nfeat: real\n")
    assert msg_check._read_subject(f, hash_is_content=False) == "feat: real"


def test_leading_blank_lines_are_skipped_either_way(tmp_path):
    f = tmp_path / "msg"
    f.write_bytes(b"\n\n  \nfeat: real\n")
    assert msg_check._read_subject(f, hash_is_content=True) == "feat: real"
    assert msg_check._read_subject(f, hash_is_content=False) == "feat: real"


def test_main_refuses_a_hash_subject_outside_any_hook(tmp_path, monkeypatch, capsys):
    """Run by hand, outside git, nothing says `#` will be stripped: fail closed."""
    for key in ("GIT_INDEX_FILE", "GIT_EDITOR"):
        monkeypatch.delenv(key, raising=False)
    f = tmp_path / "msg"
    f.write_bytes(b"# not conventional\nfeat: real\n")
    monkeypatch.setattr(sys, "argv", ["precommit_msg_check.py", str(f)])
    assert msg_check.main() == 1
    assert "subject line rejected" in capsys.readouterr().err


def test_non_vacuity_main_accepts_the_same_file_when_git_will_strip(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_INDEX_FILE", ".git/index")
    monkeypatch.setenv("GIT_EDITOR", "vi")
    monkeypatch.setattr(msg_check, "_git_config_get", _config({}))
    f = tmp_path / "msg"
    f.write_bytes(b"# not conventional\nfeat: real\n" + STRIP_TEMPLATE.encode("ascii"))
    monkeypatch.setattr(sys, "argv", ["precommit_msg_check.py", str(f)])
    assert msg_check.main() == 0


# ---------------------------------------------------------------------------
# The glyph half skips `#` lines ONLY when the shared predicate says git strips
# them. The predicate is pinned per arm, so these do not depend on the env.
# ---------------------------------------------------------------------------

E_ACUTE = chr(0x00E9)
HASH_GLYPH_LINES = ["# note " + EM_DASH + " kept by -F", "#" + EM_DASH, "# On branch caf" + E_ACUTE]
HASH_IDS = ["hash", "bare-hash", "template-branch"]


def _msg(tmp_path, line):
    f = tmp_path / "msg"
    f.write_bytes(("docs: clean\n\n" + line + "\n").encode("utf-8"))
    return str(f)


@pytest.mark.parametrize("line", HASH_GLYPH_LINES, ids=HASH_IDS)
def test_the_glyph_half_refuses_a_hash_line_glyph_when_git_keeps_it(
    tmp_path, capsys, monkeypatch, line
):
    monkeypatch.setattr(precommit_gate, "_hash_lines_are_stripped", lambda: False)
    assert precommit_gate._check_message_file(_msg(tmp_path, line)) == 1
    assert "precommit_gate BLOCKED" in capsys.readouterr().err


@pytest.mark.parametrize("line", HASH_GLYPH_LINES, ids=HASH_IDS)
def test_the_glyph_half_skips_a_hash_line_when_git_strips_it(tmp_path, monkeypatch, line):
    monkeypatch.setattr(precommit_gate, "_hash_lines_are_stripped", lambda: True)
    assert precommit_gate._check_message_file(_msg(tmp_path, line)) == 0


def test_an_indented_hash_is_not_a_comment_and_is_always_scanned(tmp_path, monkeypatch):
    """Git's comment test is a line STARTING with the comment char."""
    monkeypatch.setattr(precommit_gate, "_hash_lines_are_stripped", lambda: True)
    assert precommit_gate._check_message_file(_msg(tmp_path, "  # indented " + EM_DASH)) == 1


def test_non_vacuity_a_body_glyph_is_refused_even_when_git_strips_hash_lines(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(precommit_gate, "_hash_lines_are_stripped", lambda: True)
    assert precommit_gate._check_message_file(_msg(tmp_path, "body " + EM_DASH)) == 1


def test_the_glyph_half_loads_the_subject_halfs_predicate(monkeypatch):
    """One predicate, loaded from the subject half's own file: both fail-closed
    rows of its table read False through the glyph half too."""
    monkeypatch.setenv("GIT_INDEX_FILE", ".git/index")
    monkeypatch.setenv("GIT_EDITOR", ":")
    assert precommit_gate._hash_lines_are_stripped() is False
    monkeypatch.delenv("GIT_INDEX_FILE")
    monkeypatch.setenv("GIT_EDITOR", "vi")
    assert precommit_gate._hash_lines_are_stripped() is False


def test_an_unloadable_predicate_fails_closed(monkeypatch, capsys):
    import importlib.util

    def _boom(*args, **kwargs):
        raise ImportError("planted")

    monkeypatch.setattr(importlib.util, "spec_from_file_location", _boom)
    assert precommit_gate._hash_lines_are_stripped() is False
    assert "scanning `#` lines too" in capsys.readouterr().err


@pytest.mark.parametrize(
    "body",
    [b"raise SystemExit(0)\n", b"raise KeyboardInterrupt\n", b"raise SystemExit(1)\n"],
    ids=["systemexit-0", "keyboardinterrupt", "systemexit-1"],
)
def test_a_predicate_that_raises_baseexception_at_import_fails_closed(tmp_path, body):
    """A BaseException at predicate load used to escape `except Exception` and
    end the gate with nothing scanned - SystemExit(0) passed an em-dash on the
    SUBJECT line itself. Run as the hook runs it: the real gate file in a tree
    whose `scripts/precommit_msg_check.py` raises at import."""
    (tmp_path / "tools").mkdir()
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO_ROOT / "tools" / "precommit_gate.py", tmp_path / "tools" / "precommit_gate.py")
    (tmp_path / "scripts" / "precommit_msg_check.py").write_bytes(body)
    msg = tmp_path / "msg"
    msg.write_bytes(("docs: subject " + EM_DASH + " here\n").encode("utf-8"))
    proc = subprocess.run(
        [sys.executable, str(tmp_path / "tools" / "precommit_gate.py"), "--message-file", str(msg)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 1, (proc.returncode, proc.stderr)
    assert "precommit_gate BLOCKED" in proc.stderr, proc.stderr
    assert "scanning `#` lines too" in proc.stderr, proc.stderr


def test_non_vacuity_the_glyph_half_passes_ascii_hash_lines(tmp_path, monkeypatch):
    """The legitimate neighbour survives: ASCII comments, kept or stripped."""
    for stripped in (False, True):
        monkeypatch.setattr(precommit_gate, "_hash_lines_are_stripped", lambda s=stripped: s)
        f = tmp_path / "msg"
        f.write_bytes(
            b"docs: clean\n\n# Please enter the commit message for your changes. Lines starting\n"
            b"# with '#' will be ignored, and an empty message aborts the commit.\n"
        )
        assert precommit_gate._check_message_file(str(f)) == 0
