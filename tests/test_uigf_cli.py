"""The documented UIGF command, `python -m ingest.uigf` (MAIN ORDER item RSC-1).

The importer existed and nothing called it. These arms run the command the docs
print, as a real subprocess, against the invented fixture, and compare with
figures derived WITHOUT the importer: the pity numbers by hand from the fixture
rows, the forecasts from the engine's own `forecast_payload` over that
hand-typed state, and one from the literal README example.

A failure must be one friendly ASCII line on stderr, an empty stdout and a
non-zero exit: never a traceback, an exception class name or a parser's
complaint. Non-ASCII inputs are built with chr(), never typed as literals
(banned-glyph rule).

The command lives in `ingest/`, not in the engine, because ADR-005 says the
engine "holds no account state and reads no file". The purity arms at the end
pin that direction.
"""
from __future__ import annotations

import ast
import json
import shlex
import subprocess
import sys
from pathlib import Path

import fleet_test_guard  # on sys.path via tests/conftest.py
import pytest

from agents.pity_engine import ENGINE_VERSION
from agents.pity_engine.__main__ import forecast_payload
from core.types import BannerKind
from ingest.uigf import UigfError, _chronological, loads, parse_document, pity_state_from_uigf

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = "data/fixtures/uigf_v4_sample.json"
UID = "000000001"

DOCUMENTED = (
    "python -m ingest.uigf data/fixtures/uigf_v4_sample.json "
    "--uid 000000001 --banner character_event --target-count 1 --pull-budget 30"
)
DOCS = ("README.md", "docs/OPERATIONS.md")

#: Words that only a leaked raw error would put on stderr.
RAW_ERROR_WORDS = (
    "Traceback",
    "UigfError",
    "JSONDecodeError",
    "ValueError",
    "RecursionError",
    "Errno",
    "Exception",
    "usage:",
    "invalid int value",
    "line 1 column",
)


def _run(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "ingest.uigf", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=120,
        check=False,
    )


def _ok(*args: str) -> dict:
    result = _run(*args)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b"", "a success writes nothing to stderr, a warning included"
    assert result.stdout.isascii()
    return json.loads(result.stdout)


def _assert_friendly_failure(result: subprocess.CompletedProcess[bytes]) -> str:
    assert result.returncode != 0
    assert result.stdout == b"", "a failure prints no partial answer"
    assert result.stderr.isascii(), result.stderr
    text = result.stderr.decode("ascii")
    assert len(text.splitlines()) == 1, text
    for word in RAW_ERROR_WORDS:
        assert word not in text, text
    return text


def _wish(number: int, rank: str | None = "3", wish_id: str | None = None) -> dict:
    item = {
        "uigf_gacha_type": "301",
        "gacha_type": "301",
        "item_id": "90000003",
        "time": f"2026-01-01 {number // 3600:02d}:{number // 60 % 60:02d}:{number % 60:02d}",
        "id": wish_id if wish_id is not None else str(1000 + number),
    }
    if rank is not None:
        item["rank_type"] = rank
    return item


def _document(items: list[dict], uid: object = UID) -> dict:
    return {
        "info": {
            "export_timestamp": 1767225600,
            "export_app": "TestExporter",
            "export_app_version": "0.0.1",
            "version": "v4.0",
        },
        "hk4e": [{"uid": uid, "timezone": 8, "list": items}],
    }


#: A VALID document whose unknown top-level key nests too deep to carry through:
#: the decoder accepts it, and only `parse_document`'s deepcopy overflows. It
#: must be otherwise valid or a missing `info` refuses it before that line runs.
CARRIED_DEEP_KEY = json.dumps(_document([]))[:-1] + ', "x": ' + "[" * 5000 + "]" * 5000 + "}"


def _write(path: Path, text: str) -> str:
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def _fenced_lines(text: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("```"):
            inside = not inside
        elif inside:
            lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# ACCEPT: the documented command loads the fixture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc", DOCS)
def test_the_command_is_in_a_code_block_of_the_doc(doc: str):
    text = (REPO_ROOT / doc).read_text(encoding="utf-8")
    assert DOCUMENTED in _fenced_lines(text), f"{doc} does not document: {DOCUMENTED}"


def test_the_command_the_docs_print_loads_the_fixture():
    """Runs the line READ FROM THE DOC, so the doc cannot drift from the command."""
    text = (REPO_ROOT / "docs/OPERATIONS.md").read_text(encoding="utf-8")
    lines = [line for line in _fenced_lines(text) if line.startswith("python -m ingest.uigf ")]
    assert lines, "non-vacuity: the doc carries no such command line"
    argv = shlex.split(lines[0])
    assert argv[:3] == ["python", "-m", "ingest.uigf"]

    answer = _ok(*argv[3:])

    # By hand from the 301 rows of the fixture, ordered by (time, id): wish ...04
    # is the last rank 5 and four wishes follow it (...05 to ...08); wish ...06 is
    # the last rank 4 or 5 and two follow it (...07, ...08). Eight rows in all.
    assert answer["uid"] == UID
    assert answer["banner"] == "character_event"
    assert answer["wishes_seen"] == 8
    assert answer["pity_5star"] == 4
    assert answer["pity_4star"] == 2
    assert answer["has_guarantee"] is False
    assert answer["consecutive_5050_losses"] == 0
    assert answer["fate_points"] == 0
    assert answer["engine_version"] == ENGINE_VERSION
    assert answer["status"] == "ok"

    engine = forecast_payload(
        {"banner": "character_event", "pity_5star": 4, "pity_4star": 2, "target_count": 1, "pull_budget": 30}
    )
    forecast = answer["forecast"]
    assert forecast["probability"] == engine["probability"]
    assert forecast["distribution"] == engine["distribution"]
    assert forecast["expected_pulls"] == engine["expected_pulls"]
    assert forecast["target_count"] == 1
    assert forecast["pull_budget"] == 30
    assert 0.0 < forecast["probability"] < 1.0


@pytest.mark.parametrize(
    ("banner", "seen", "p5", "p4"),
    [
        ("weapon_event", 3, 3, 3),  # three rank 3 rows, no payout yet
        ("standard", 2, 1, 1),  # a rank 5, then one rank 3
        ("chronicled", 0, 0, 0),  # the fixture has no 500 rows
    ],
)
def test_every_banner_family_without_a_forecast(banner: str, seen: int, p5: int, p4: int):
    answer = _ok(FIXTURE, "--uid", UID, "--banner", banner)
    assert (answer["wishes_seen"], answer["pity_5star"], answer["pity_4star"]) == (seen, p5, p4)
    assert answer["banner"] == banner
    assert answer["forecast"] is None


def test_the_seeded_pity_reaches_the_forecast_against_the_readme_figure(tmp_path: Path):
    """74 wishes with no payout must reproduce the README's literal example."""
    path = _write(tmp_path / "h.json", json.dumps(_document([_wish(n) for n in range(74)])))
    answer = _ok(path, "--uid", UID, "--banner", "character_event", "--target-count", "1", "--pull-budget", "30")
    assert answer["pity_5star"] == 74
    assert answer["forecast"]["probability"] == 0.5904331542650183
    assert answer["forecast"]["expected_pulls"] == 33.82161353538069


def test_the_seed_changes_the_answer():
    """Non-vacuity of the arm above: an unseeded forecast is a different number."""
    # 80 pulls, because the hazard is flat below soft pity: pity 4 and pity 0 give
    # byte-equal answers at 30 pulls, measured, and only differ once one reaches it.
    seeded = _ok(FIXTURE, "--uid", UID, "--banner", "character_event", "--target-count", "1", "--pull-budget", "80")
    unseeded = forecast_payload({"banner": "character_event", "target_count": 1, "pull_budget": 80})
    assert seeded["forecast"]["probability"] != unseeded["probability"]


@pytest.mark.parametrize(
    ("banner", "flags", "body"),
    [
        ("character_event", ("--has-guarantee",), {"has_guarantee": True}),
        ("character_event", ("--consecutive-5050-losses", "3"), {"consecutive_5050_losses": 3}),
        ("weapon_event", ("--fate-points", "1"), {"fate_points": 1}),
    ],
)
def test_the_caller_guarantee_inputs_reach_the_engine(banner: str, flags: tuple[str, ...], body: dict):
    base = _ok(FIXTURE, "--uid", UID, "--banner", banner, "--target-count", "1", "--pull-budget", "75")
    moved = _ok(FIXTURE, "--uid", UID, "--banner", banner, "--target-count", "1", "--pull-budget", "75", *flags)
    assert moved["forecast"]["probability"] != base["forecast"]["probability"], "the flag changed nothing"
    for key, value in body.items():
        assert moved[key] == value
    engine = forecast_payload(
        {
            "banner": banner,
            "pity_5star": moved["pity_5star"],
            "pity_4star": moved["pity_4star"],
            "target_count": 1,
            "pull_budget": 75,
            **body,
        }
    )
    assert moved["forecast"]["probability"] == engine["probability"]


def test_output_is_deterministic():
    args = (FIXTURE, "--uid", UID, "--banner", "weapon_event", "--target-count", "2", "--pull-budget", "100")
    first = _run(*args)
    assert first.returncode == 0
    assert first.stdout == _run(*args).stdout


def test_an_integer_uid_in_the_file_matches(tmp_path: Path):
    path = _write(tmp_path / "h.json", json.dumps(_document([_wish(1)], uid=123456789)))
    assert _ok(path, "--uid", "123456789", "--banner", "character_event")["pity_5star"] == 1


def test_help_is_ascii_and_exits_zero():
    result = _run("--help")
    assert result.returncode == 0
    assert result.stdout.isascii()
    assert b"--target-count" in result.stdout


def test_the_largest_accepted_values_answer():
    """The legitimate neighbour of the over-limit refusals below."""
    answer = _ok(FIXTURE, "--uid", UID, "--banner", "character_event", "--target-count", "7", "--pull-budget", "5000")
    assert answer["forecast"]["target_count"] == 7
    assert answer["forecast"]["pull_budget"] == 5000


def test_a_zero_budget_is_a_legitimate_question():
    answer = _ok(FIXTURE, "--uid", UID, "--banner", "character_event", "--target-count", "1", "--pull-budget", "0")
    assert answer["forecast"]["probability"] == 0.0


# ---------------------------------------------------------------------------
# Failure handling: file and document
# ---------------------------------------------------------------------------


def test_a_missing_file_is_refused(tmp_path: Path):
    text = _assert_friendly_failure(_run(str(tmp_path / "absent.json"), "--uid", UID, "--banner", "standard"))
    assert "could not be read" in text
    assert "absent.json" not in text, "the raw path stays out of the message"


def test_a_directory_is_refused(tmp_path: Path):
    text = _assert_friendly_failure(_run(str(tmp_path), "--uid", UID, "--banner", "standard"))
    assert "could not be read" in text


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("empty file", b""),
        ("truncated JSON", b'{"info": {'),
        ("not an object", b"[1, 2, 3]"),
        ("not UTF-8", b'{"info": "\xff\xfe"}'),
        ("UTF-8 BOM", b"\xef\xbb\xbf" + json.dumps(_document([])).encode("ascii")),
        ("unknown version", json.dumps({**_document([]), "info": {"version": "v3.0"}}).encode("ascii")),
        ("deep nesting", b"[" * 200000),
        ("deep nesting in a carried key", CARRIED_DEEP_KEY.encode("ascii")),
        ("an integer past the digit limit", b'{"info": ' + b"1" * 5000 + b"}"),
        ("a bad row", json.dumps(_document([{"uigf_gacha_type": "999"}])).encode("ascii")),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_a_bad_document_is_refused(tmp_path: Path, label: str, payload: bytes):
    path = tmp_path / "h.json"
    path.write_bytes(payload)
    text = _assert_friendly_failure(_run(str(path), "--uid", UID, "--banner", "standard"))
    assert "not a valid UIGF v4" in text, label


def test_an_unknown_uid_is_refused():
    text = _assert_friendly_failure(_run(FIXTURE, "--uid", "999999999", "--banner", "standard"))
    assert "no account" in text


def test_uid_matching_is_exact_text_not_numeric():
    """The fixture's uid has leading zeros; `1` is a different account string."""
    _assert_friendly_failure(_run(FIXTURE, "--uid", "1", "--banner", "standard"))


def test_a_wish_without_a_rank_is_refused(tmp_path: Path):
    path = _write(tmp_path / "h.json", json.dumps(_document([_wish(1, rank=None)])))
    text = _assert_friendly_failure(_run(path, "--uid", UID, "--banner", "character_event"))
    assert "pity" in text


def test_a_history_past_hard_pity_cannot_be_forecast(tmp_path: Path):
    path = _write(tmp_path / "h.json", json.dumps(_document([_wish(n) for n in range(90)])))
    args = (path, "--uid", UID, "--banner", "character_event")
    assert _ok(*args)["pity_5star"] == 90, "the count alone is still answerable"
    text = _assert_friendly_failure(_run(*args, "--target-count", "1", "--pull-budget", "1"))
    assert "hard pity" in text


# ---------------------------------------------------------------------------
# Failure handling: command-line arguments
# ---------------------------------------------------------------------------

ARABIC_ONE = chr(0x0661)
FULLWIDTH_ONE = chr(0xFF11)
SUPERSCRIPT_TWO = chr(0x00B2)
DEVANAGARI_THREE = chr(0x0969)

BAD_INTEGERS = (
    "-1",
    "abc",
    "1.5",
    "",
    " 1",
    "1\n",
    "1_000",
    "+1",
    "0x10",
    "9" * 5000,
    ARABIC_ONE,
    FULLWIDTH_ONE,
    SUPERSCRIPT_TWO,
    DEVANAGARI_THREE,
)


@pytest.mark.parametrize("value", BAD_INTEGERS, ids=[f"bad{n}" for n in range(len(BAD_INTEGERS))])
@pytest.mark.parametrize(
    "flag", ["--target-count", "--pull-budget", "--consecutive-5050-losses", "--fate-points"]
)
def test_a_bad_integer_argument_is_refused(flag: str, value: str):
    args = [FIXTURE, "--uid", UID, "--banner", "character_event", "--target-count", "1", "--pull-budget", "1"]
    args += [flag, value]
    text = _assert_friendly_failure(_run(*args))
    assert flag in text, "the message names the argument"
    assert "ASCII digits" in text


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--target-count", "0"),
        ("--target-count", "8"),
        ("--pull-budget", "5001"),
        ("--consecutive-5050-losses", "4"),
        ("--fate-points", "2"),
    ],
)
def test_an_out_of_range_integer_is_refused_before_any_solve(flag: str, value: str):
    args = [FIXTURE, "--uid", UID, "--banner", "character_event", "--target-count", "1", "--pull-budget", "1"]
    text = _assert_friendly_failure(_run(*args, flag, value))
    assert flag in text


@pytest.mark.parametrize(
    "banner",
    ["novice", "CHARACTER_EVENT", "", "character_event\n", chr(0x00E9)],
    ids=["novice", "upper", "empty", "newline", "non-ascii"],
)
def test_an_unknown_banner_is_refused(banner: str):
    text = _assert_friendly_failure(_run(FIXTURE, "--uid", UID, "--banner", banner))
    assert "--banner" in text
    assert "character_event" in text, "the message lists what is accepted"


@pytest.mark.parametrize(
    "uid",
    ["", "abc", "12 3", "1\n", "-1", ARABIC_ONE * 9, FULLWIDTH_ONE * 9, "12345678" + SUPERSCRIPT_TWO],
    ids=["empty", "letters", "space", "newline", "negative", "arabic", "fullwidth", "superscript"],
)
def test_a_bad_uid_is_refused(uid: str):
    text = _assert_friendly_failure(_run(FIXTURE, f"--uid={uid}", "--banner", "standard"))
    assert "--uid" in text


@pytest.mark.parametrize(
    "args",
    [
        (),
        (FIXTURE,),
        (FIXTURE, "--uid", UID),
        (FIXTURE, "--banner", "standard"),
        ("--uid", UID, "--banner", "standard"),
        (FIXTURE, "--uid"),
    ],
)
def test_missing_arguments_are_refused(args: tuple[str, ...]):
    _assert_friendly_failure(_run(*args))


@pytest.mark.parametrize("flag", ["--target-count", "--pull-budget"])
def test_a_forecast_needs_both_of_its_arguments(flag: str):
    text = _assert_friendly_failure(_run(FIXTURE, "--uid", UID, "--banner", "standard", flag, "1"))
    assert "--target-count" in text
    assert "--pull-budget" in text


@pytest.mark.parametrize(
    "extra",
    [
        ("--nope",),
        ("stray-positional",),
        ("--has-guarantee=yes" + chr(0x00E9),),
        ("--" + chr(0x00E9),),
        ("--nope\nsecond line",),
        ("--target", "1"),  # no abbreviations: a typo is not an alias
    ],
)
def test_an_unrecognised_argument_is_refused_and_not_echoed(extra: tuple[str, ...]):
    text = _assert_friendly_failure(_run(FIXTURE, "--uid", UID, "--banner", "standard", *extra))
    assert "nope" not in text
    assert "stray" not in text


@pytest.mark.parametrize(
    ("code", "args"),
    [
        (1, ("absent.json", "--uid", UID, "--banner", "standard")),
        (1, (FIXTURE, "--uid", "999999999", "--banner", "standard")),
        (2, (FIXTURE, "--uid", UID, "--banner", "nope")),
        (2, (FIXTURE, "--uid", UID, "--banner", "standard", "--nope")),
        (2, (FIXTURE, "--uid", UID, "--banner", "standard", "--pull-budget", "1")),
    ],
)
def test_the_documented_exit_codes(code: int, args: tuple[str, ...]):
    assert _run(*args).returncode == code


def test_a_closed_stdout_is_not_a_traceback():
    process = subprocess.Popen(
        [sys.executable, "-m", "ingest.uigf", FIXTURE, "--uid", UID, "--banner", "standard"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    process.stdout.close()  # long before the child has imported anything
    stderr = process.stderr.read()
    process.stderr.close()
    assert process.wait(timeout=fleet_test_guard.budget(120)) != 0
    assert stderr.isascii()
    text = stderr.decode("ascii")
    assert len(text.splitlines()) == 1, text
    assert "output could not be written" in text


# ---------------------------------------------------------------------------
# The library half of the same root cause: the docstrings promise UigfError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "[" * 200000,
        CARRIED_DEEP_KEY,
        '{"info": ' + "1" * 5000 + "}",
    ],
    ids=["deep nesting", "deep nesting in a carried key", "an integer past the digit limit"],
)
def test_loads_turns_every_decode_failure_into_a_uigf_error(text: str):
    with pytest.raises(UigfError):
        loads(text)


def test_a_wish_id_past_the_digit_limit_is_not_a_bare_value_error():
    """`int(item.id)` raised 'Exceeds the limit' on a 4301-digit id."""
    huge = "9" * 5000
    doc = parse_document(_document([_wish(1, wish_id=huge), _wish(1, rank="5", wish_id="7")]))
    # Same timestamp, so the id decides: 7 is the earlier wish, then one more.
    assert pity_state_from_uigf(doc, UID, BannerKind.CHARACTER_EVENT).pity_5star == 1


def test_the_id_tie_break_is_numeric_not_lexical():
    """The legitimate neighbour of the arm above: 9 sorts before 10, 007 before 8."""
    doc = parse_document(
        _document([_wish(1, wish_id="10"), _wish(1, wish_id="9"), _wish(1, wish_id="007"), _wish(1, wish_id="8")])
    )
    ordered = [item.id for item in _chronological(doc.hk4e[0].items)]
    assert ordered == ["007", "8", "9", "10"]


# ---------------------------------------------------------------------------
# The engine stays pure: ingest imports the engine, never the reverse
# ---------------------------------------------------------------------------


def _ingest_imports(source: str) -> list[str]:
    """Every import of `ingest`, at any nesting depth, a lazy one included."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names if alias.name.split(".")[0] == "ingest"]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            if (node.module or "").split(".")[0] == "ingest":
                found.append(node.module or "")
    return found


def _engine_sources() -> list[Path]:
    root = REPO_ROOT / "agents" / "pity_engine"
    return [path for path in sorted(root.rglob("*.py")) if "tests" not in path.relative_to(root).parts]


def test_no_engine_module_imports_ingest():
    sources = _engine_sources()
    assert any(path.name == "__main__.py" for path in sources), "non-vacuity: the sweep missed the transport"
    offenders = {
        path.name: _ingest_imports(path.read_text(encoding="utf-8"))
        for path in sources
        if _ingest_imports(path.read_text(encoding="utf-8"))
    }
    assert offenders == {}


@pytest.mark.parametrize(
    "source",
    [
        "import ingest\n",
        "import ingest.uigf\n",
        "from ingest.uigf import read_uigf\n",
        "def main():\n    from ingest.uigf import read_uigf\n",
    ],
)
def test_the_import_detector_fires_on_a_lazy_import(source: str):
    assert _ingest_imports(source)


def test_the_import_detector_spares_a_neighbour():
    assert _ingest_imports("import ingestion\nfrom . import ingest\n'''from ingest.uigf import x'''\n") == []


@pytest.mark.parametrize(
    "code",
    [
        "import agents.pity_engine.__main__, sys; "
        "assert not [m for m in sys.modules if m == 'ingest' or m.startswith('ingest.')]",
        "import ingest.uigf, agents.pity_engine.__main__",
        "import agents.pity_engine.__main__, ingest.uigf",
    ],
)
def test_import_order_has_no_cycle_in_a_fresh_process(code: str):
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, timeout=120, check=False
    )
    assert result.returncode == 0, result.stderr


def test_the_engine_header_points_at_the_command():
    source = (REPO_ROOT / "agents" / "pity_engine" / "__main__.py").read_text(encoding="utf-8")
    assert "python -m ingest.uigf" in (ast.get_docstring(ast.parse(source)) or "")
