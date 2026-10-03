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


@pytest.mark.parametrize(
    ("env", "config", "stripped"),
    [
        # -F / -m: git exports GIT_EDITOR=: and the default cleanup keeps `#`.
        (IN_HOOK_NO_EDITOR, {}, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "default"}, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "whitespace"}, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "verbatim"}, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "scissors"}, False),
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "strip"}, True),
        # Editor: the default cleanup is strip.
        (IN_HOOK_EDITOR, {}, True),
        (IN_HOOK_EDITOR_UNSET, {}, True),
        (IN_HOOK_EDITOR, {"commit.cleanup": "default"}, True),
        # Scissors keeps `#` lines above its marker, measured in editor mode.
        (IN_HOOK_EDITOR, {"commit.cleanup": "scissors"}, False),
        (IN_HOOK_EDITOR, {"commit.cleanup": "strip"}, True),
        (IN_HOOK_EDITOR, {"commit.cleanup": "whitespace"}, False),
        (IN_HOOK_EDITOR, {"commit.cleanup": "verbatim"}, False),
        # Case-insensitive, as git parses it.
        (IN_HOOK_NO_EDITOR, {"commit.cleanup": "STRIP"}, True),
        # Unknown mode: fail closed.
        (IN_HOOK_EDITOR, {"commit.cleanup": "frobnicate"}, False),
        # A comment character other than `#` means `#` is ordinary content.
        (IN_HOOK_EDITOR, {"core.commentChar": ";"}, False),
        (IN_HOOK_EDITOR, {"core.commentChar": "auto"}, False),
        (IN_HOOK_EDITOR, {"core.commentString": "//"}, False),
        (IN_HOOK_EDITOR, {"core.commentChar": "#"}, True),
        # Not inside a git commit hook at all: nothing is known, fail closed.
        ({}, {}, False),
        ({"GIT_EDITOR": "vi"}, {"commit.cleanup": "strip"}, False),
    ],
)
def test_the_cleanup_decision_table(env, config, stripped):
    assert msg_check.hash_lines_are_stripped(env, _config(config)) is stripped


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
    f.write_bytes(b"# not conventional\nfeat: real\n")
    monkeypatch.setattr(sys, "argv", ["precommit_msg_check.py", str(f)])
    assert msg_check.main() == 0


# ---------------------------------------------------------------------------
# The glyph half scans EVERY line, comments included
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    ["# note " + EM_DASH + " kept by -F", "  # indented " + EM_DASH, "#" + EM_DASH],
    ids=["hash", "indented-hash", "bare-hash"],
)
def test_the_glyph_half_refuses_a_glyph_on_a_hash_line(tmp_path, capsys, line):
    f = tmp_path / "msg"
    f.write_bytes(("docs: clean\n\n" + line + "\n").encode("utf-8"))
    assert precommit_gate._check_message_file(str(f)) == 1
    assert "precommit_gate BLOCKED" in capsys.readouterr().err


def test_non_vacuity_the_glyph_half_passes_ascii_hash_lines(tmp_path):
    """The legitimate neighbour survives: git's own ASCII template comments."""
    f = tmp_path / "msg"
    f.write_bytes(
        b"docs: clean\n\n# Please enter the commit message for your changes. Lines starting\n"
        b"# with '#' will be ignored, and an empty message aborts the commit.\n"
    )
    assert precommit_gate._check_message_file(str(f)) == 0
