"""FLEET-KIT conformance: this tree carries MAIN's kit unedited.

MAIN's FLEET-KIT is vendored byte-for-byte at `ops/fleet_kit/` and pinned by
`ops/fleet_kit/MANIFEST.json`. The kit's own `conformance()` is the check every
fleet repo runs in its suite: it reports a kit file edited locally, a manifest
version that disagrees with the module, a `CLAUDE.md` that is CRLF, one that
lacks the FLEET-COMMON markers, and one whose block between the markers does
not hash to the manifest's `common_block_sha256`.

The repo arm is meaningless unless the detector can fire, so every problem
string the function can emit for `CLAUDE.md` and for a kit file is provoked
here on a scratch COPY of the tree's own bytes - never on the tree itself. The
copy is checked to conform first, so a mutant that reports a problem is
reporting the mutation and not a defect in the copying.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = REPO_ROOT / "ops" / "fleet_kit"


def _load_kit() -> ModuleType:
    """Import the vendored module from its file, without touching sys.path."""
    spec = importlib.util.spec_from_file_location("fleet_headless_under_test", KIT_DIR / "fleet_headless.py")
    assert spec is not None and spec.loader is not None, "ops/fleet_kit/fleet_headless.py is not importable"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KIT = _load_kit()


def _scratch_copy(tmp_path: Path) -> Path:
    """The two inputs conformance() reads - CLAUDE.md and the kit dir - copied as bytes."""
    root = tmp_path / "repo"
    (root / "ops").mkdir(parents=True)
    shutil.copytree(KIT_DIR, root / "ops" / "fleet_kit")
    (root / "CLAUDE.md").write_bytes((REPO_ROOT / "CLAUDE.md").read_bytes())
    return root


def test_this_tree_conforms_to_the_fleet_kit():
    assert KIT.conformance(REPO_ROOT) == []


def test_the_markers_appear_exactly_once_each():
    """conformance() uses str.find, so a SECOND block would go unchecked.

    A stale duplicate below the real one would read as fleet doctrine to a
    session and never be compared against the manifest.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_bytes().decode("ascii")
    assert text.count(KIT.BEGIN) == 1, f"BEGIN marker count {text.count(KIT.BEGIN)}"
    assert text.count(KIT.END) == 1, f"END marker count {text.count(KIT.END)}"


def test_the_embedded_block_is_the_kit_file_byte_for_byte():
    """The hash arm restated as a byte comparison, so a failure names the drift."""
    text = (REPO_ROOT / "CLAUDE.md").read_bytes().decode("ascii")
    i, j = text.find(KIT.BEGIN), text.find(KIT.END)
    assert 0 <= i < j, "CLAUDE.md lacks the FLEET-COMMON markers"
    block = text[i + len(KIT.BEGIN) : j].encode("ascii")
    assert block == (KIT_DIR / "FLEET-COMMON.md").read_bytes()


def test_an_unmutated_scratch_copy_conforms(tmp_path):
    """Control for the mutants below: the copy itself is faithful."""
    assert KIT.conformance(_scratch_copy(tmp_path)) == []


def _mutate_claude_md(root: Path, old: bytes, new: bytes) -> None:
    path = root / "CLAUDE.md"
    data = path.read_bytes()
    assert old in data, f"mutation target {old!r} absent - this mutant would be a no-op"
    path.write_bytes(data.replace(old, new, 1))


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        # One word changed INSIDE the common block.
        (b"1. ACT, DON'T ASK.", b"1. ACT, DO ASK.", "CLAUDE.md FLEET-COMMON block edited"),
        # The BEGIN marker removed.
        (b"<!-- FLEET-COMMON BEGIN -->\n", b"", "CLAUDE.md lacks the FLEET-COMMON markers"),
        # The END marker removed.
        (b"<!-- FLEET-COMMON END -->", b"", "CLAUDE.md lacks the FLEET-COMMON markers"),
        # CRLF anywhere in the file.
        (b"\n", b"\r\n", "CLAUDE.md is CRLF; the fleet rule is LF"),
        # A non-ASCII byte anywhere in the file.
        (b" - ", b" \xe2\x80\x94 ", "CLAUDE.md missing or not ASCII"),
    ],
    ids=["block-edited", "begin-removed", "end-removed", "crlf", "non-ascii"],
)
def test_a_mutated_claude_md_is_reported(tmp_path, old, new, expected):
    root = _scratch_copy(tmp_path)
    _mutate_claude_md(root, old, new)
    assert expected in KIT.conformance(root)


#: The files kit v12 pins, per the MAIN 2031 ORDER of 2026-10-08, sorted as
#: `sorted()` orders them. v4 added LICENSE and NOTICE (Apache-2.0, holder the
#: operator); v5 added fleet_watch.py, fleet_secrets.py and the two token
#: files; v6 added fleet_lanes.py; v7 added fleet_checklist.py; v8 added
#: fleet_inbox.py; v9 added fleet_done.py, fleet_statusline.js,
#: fleet_subagent_status.js and cli_display.json, and changed FLEET-COMMON.md
#: (item 15), the token files, fleet_headless.py, fleet_inbox.py and
#: fleet_checklist.py besides; v10 added fleet_subagent_first.py and changed
#: FLEET-COMMON.md (the banner), NOTICE, cli_display.json, fleet_checklist.py,
#: fleet_done.py, fleet_headless.py, fleet_inbox.py, fleet_lanes.py and
#: fleet_watch.py besides; v11 added no file and changed fleet_done.py,
#: fleet_headless.py, fleet_inbox.py, fleet_lanes.py, fleet_subagent_first.py
#: and fleet_watch.py (FLEET-COMMON.md unchanged); v12 added fleet_claims.py,
#: fleet_gitlock.py, fleet_suite_gate.py and fleet_test_guard.py and changed
#: FLEET-COMMON.md (item 12 sentence, item 16), NOTICE, fleet_checklist.py
#: and fleet_headless.py.
PINNED_FILES = (
    "FLEET-COMMON.md",
    "LICENSE",
    "NOTICE",
    "cli_display.json",
    "fleet_checklist.py",
    "fleet_claims.py",
    "fleet_done.py",
    "fleet_gitlock.py",
    "fleet_headless.py",
    "fleet_inbox.py",
    "fleet_lanes.py",
    "fleet_secrets.py",
    "fleet_statusline.js",
    "fleet_subagent_first.py",
    "fleet_subagent_status.js",
    "fleet_suite_gate.py",
    "fleet_test_guard.py",
    "fleet_watch.py",
    "tokens.css",
    "tokens.json",
)

#: MANIFEST.json is not in its own `files` map, so conformance() cannot notice
#: a file and the manifest edited TOGETHER (its own docstring says MAIN's drift
#: sweep catches that). Pinning the manifest's digest here, as the MAIN 2031
#: ORDER section 1 states it, closes that gap inside this tree.
PINNED_KIT_VERSION = 12
MANIFEST_SHA256 = "781996ac966c11cb83d357afc39ac634d7d9ae6cdd39e7282b0ddb2309bd600d"


def test_the_vendored_kit_is_the_pinned_version_and_pins_its_licence_files():
    """The ORDER adopted is v12; a v13 drop must update this arm deliberately."""
    raw = (KIT_DIR / "MANIFEST.json").read_bytes()
    manifest = json.loads(raw.decode("ascii"))
    assert KIT.KIT_VERSION == PINNED_KIT_VERSION
    assert manifest["version"] == PINNED_KIT_VERSION
    assert tuple(sorted(manifest["files"])) == PINNED_FILES
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256, (
        "ops/fleet_kit/MANIFEST.json is not MAIN's v12 manifest byte-for-byte"
    )


def test_the_kit_directory_holds_only_the_pinned_files():
    """conformance() reads only the files its manifest names, so a rogue file
    dropped beside them is invisible to it. The directory must hold exactly the
    pinned set plus MANIFEST.json (bytecode caches excepted)."""
    present = sorted(
        p.name for p in KIT_DIR.iterdir() if p.name != "__pycache__"
    )
    assert tuple(present) == tuple(sorted((*PINNED_FILES, "MANIFEST.json")))


@pytest.mark.parametrize("name", PINNED_FILES)
def test_an_edited_kit_file_is_reported(tmp_path, name):
    root = _scratch_copy(tmp_path)
    target = root / "ops" / "fleet_kit" / name
    target.write_bytes(target.read_bytes() + b"\n# local edit\n")
    assert f"kit file missing or edited: {name}" in KIT.conformance(root)


@pytest.mark.parametrize("name", ("LICENSE", "NOTICE"))
def test_a_deleted_licence_file_is_reported(tmp_path, name):
    """Apache-2.0 s4(a) and s4(d): the grant must travel with the code."""
    root = _scratch_copy(tmp_path)
    (root / "ops" / "fleet_kit" / name).unlink()
    assert f"kit file missing or edited: {name}" in KIT.conformance(root)


def test_a_manifest_version_mismatch_is_reported(tmp_path):
    root = _scratch_copy(tmp_path)
    path = root / "ops" / "fleet_kit" / "MANIFEST.json"
    data = path.read_bytes()
    assert b'"version": 12' in data, "mutation target absent - this mutant would be a no-op"
    path.write_bytes(data.replace(b'"version": 12', b'"version": 11', 1))
    assert "manifest v11 != kit v12" in KIT.conformance(root)


#: U+2610 as UTF-8, built from the code point so this file stays 7-bit.
_BOX_UTF8 = chr(0x2610).encode("utf-8")
#: The same glyph as the ASCII escape the kit source is required to carry.
_BOX_ESCAPE = b"\\u2610"


def _box_offences(raw: bytes) -> list[str]:
    """Why `raw` is not an ASCII source that spells the box as an escape."""
    found: list[str] = []
    if _BOX_UTF8 in raw:
        found.append("literal U+2610")
    if any(b > 0x7F for b in raw):
        found.append("non-ASCII byte")
    if _BOX_ESCAPE not in raw:
        found.append("no U+2610 escape")
    return found


def test_the_checklist_box_is_an_escape_never_a_literal():
    """FLEET-COMMON item 13: <box> is U+2610, and this tree is 7-bit.

    The kit's checklist helper must therefore carry the box as an escape in an
    ASCII source and still EMIT the real glyph. Both halves are checked, plus
    the detector itself, so neither a literal smuggled into the source nor an
    escape that renders as something else can pass.
    """
    raw = (KIT_DIR / "fleet_checklist.py").read_bytes()
    assert _box_offences(raw) == []
    spec = importlib.util.spec_from_file_location("fleet_checklist_under_test", KIT_DIR / "fleet_checklist.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.BOX == chr(0x2610)
    assert module.DONE_LINE == chr(0x2610) + " /done"
    # Non-vacuity: the escape swapped for the literal glyph is reported on
    # all three counts, and a source with no box at all on the third.
    assert raw.count(_BOX_ESCAPE) >= 1, "mutation target absent - this mutant would be a no-op"
    assert _box_offences(raw.replace(_BOX_ESCAPE, _BOX_UTF8)) == [
        "literal U+2610",
        "non-ASCII byte",
        "no U+2610 escape",
    ]
    assert _box_offences(b"BOX = '[ ]'\n") == ["no U+2610 escape"]
