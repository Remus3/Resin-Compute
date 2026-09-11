#!/usr/bin/env python3
"""Dashboard companion QA - one runnable end-to-end check of the whole stack.

WHY A SCRIPT AND NOT JUST TESTS. The suites already grade every piece in
isolation: the model is pure, the renderer is pure, the shell's libraries are
graded by `node --test`, and `tests/test_shell_contract.py` pins the port across
the language boundary. What none of them answer is the question an operator
actually asks at the start of a session - "is the companion working right now, on
this machine, as installed?" That needs a real bind, a real request, and a look
at artefacts that live outside the repository.

TOTAL, AND NEVER DESTRUCTIVE. Every check degrades to a reported failure rather
than an exception, nothing is written, and nothing already running is touched.
The probe binds an EPHEMERAL port so it cannot contend with a dashboard the
operator has open - and contending would not merely be rude, it is the exact
defect ADR-006's sibling commit fixed, where two surfaces held one port and the
older one silently answered everything.

Exit codes, so this can gate a script:
    0  every check passed, or passed with skips or notes
    1  at least one check FAILED

FOUR STATUS WORDS, NOT THREE. PASS, FAIL and SKIP are the original three. NOTE
is a fourth, and it exists because SKIP already means something specific and
incompatible: a SKIP is a DECLINED-TO-MEASURE disposition, printed when the
probe could not run at all - no Electron binary, nothing listening, no user
profile. A row that DID measure, got an answer, and simply has no business
changing an exit code is not a skip, and filing it as one would inflate the
skipped count with measurements that succeeded. `check_dev_pin_drift` is the
first such row. Neither SKIP nor NOTE can make this script exit 1.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OK = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"
#: Measured, reported, and deliberately not graded. See the module docstring for
#: why this is not spelled SKIP.
NOTE = "NOTE"

#: Panels the dashboard is expected to declare. A panel silently disappearing is
#: a regression an operator would not otherwise notice, because a missing card
#: looks like a layout choice.
EXPECTED_PANELS = ("resin", "today", "wishes", "roster", "plan", "teams")


class Report:
    """Collects results and decides the exit code."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, status: str, name: str, detail: str = "") -> None:
        self.rows.append((status, name, detail))

    def render(self) -> int:
        width = max(len(name) for _, name, _ in self.rows) if self.rows else 0
        for status, name, detail in self.rows:
            line = f"  {status}  {name.ljust(width)}"
            if detail:
                line += f"  {detail}"
            print(line)
        failed = sum(1 for status, _, _ in self.rows if status == FAIL)
        passed = sum(1 for status, _, _ in self.rows if status == OK)
        skipped = sum(1 for status, _, _ in self.rows if status == SKIP)
        # THE FOUR COUNTS PARTITION THE ROWS BY CONSTRUCTION. `noted` is the
        # remainder rather than a fourth `sum(... == NOTE)` so that a status
        # word added later cannot silently vanish from the tally, which is
        # exactly how a tally starts lying about what it counted.
        noted = len(self.rows) - passed - failed - skipped
        # Still not a pytest terminal summary: counts with no `in <float>s`.
        # `tools/stop_claim_gate.py` refuses this line on that basis, and
        # `tests/test_stop_claim_gate.py` pins the refusal. Adding a duration
        # here would launder a number no pytest run produced.
        print(f"\n  {passed} passed, {failed} failed, {skipped} skipped, {noted} noted")
        return 1 if failed else 0


def _get(url: str, timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, "", exc.read().decode("utf-8", errors="replace")


def check_ports(report: Report) -> None:
    from core import ports

    report.add(OK, "port block", f"{ports.RSC_BLOCK.start}-{ports.RSC_BLOCK.stop - 1} (rsc)")
    for name, value in (("engine", ports.ENGINE), ("dashboard", ports.DASHBOARD)):
        if ports.is_ours(value):
            report.add(OK, f"port {name}", str(value))
        else:
            report.add(FAIL, f"port {name}", f"{value} is outside the reserved block")


def check_shell_contract(report: Report) -> None:
    """The port is duplicated across a language boundary; it must not drift."""
    import re

    from core import ports

    endpoint = REPO_ROOT / "shell" / "lib" / "endpoint.js"
    if not endpoint.is_file():
        report.add(FAIL, "shell endpoint", "shell/lib/endpoint.js is missing")
        return
    match = re.search(r"const\s+DEFAULT_PORT\s*=\s*(\d+)\s*;", endpoint.read_text(encoding="utf-8"))
    if match is None:
        report.add(FAIL, "shell endpoint", "no DEFAULT_PORT to compare")
    elif int(match.group(1)) != ports.DASHBOARD:
        report.add(FAIL, "shell endpoint", f"JS says {match.group(1)}, Python says {ports.DASHBOARD}")
    else:
        report.add(OK, "shell endpoint", f"JS and Python agree on {ports.DASHBOARD}")


def check_surface(report: Report) -> None:
    """Bind an EPHEMERAL port and exercise every route."""
    from surface.server import DashboardServer

    server = DashboardServer(host="127.0.0.1", port=0)
    try:
        server.start()
    except OSError as exc:
        report.add(FAIL, "surface bind", f"{exc.__class__.__name__}")
        return

    try:
        status, content_type, body = _get(f"{server.base_url}/health")
        if status == 200 and "json" in content_type:
            report.add(OK, "route /health", f"pid {json.loads(body).get('pid')}")
        else:
            report.add(FAIL, "route /health", f"status {status}")

        status, content_type, body = _get(f"{server.base_url}/")
        if status == 200 and body.startswith("<!doctype html>"):
            report.add(OK, "route /", f"{len(body)} bytes of html")
        else:
            report.add(FAIL, "route /", f"status {status}")

        if "id=\"dragbar\"" in body:
            report.add(OK, "drag strip", "present - the window is frameless")
        else:
            report.add(FAIL, "drag strip", "absent: the window would be unmovable")

        if body.isascii():
            report.add(OK, "page is ascii", "authored text only - the served state has no roster")
        else:
            report.add(FAIL, "page is ascii", "the rendered page left 7-bit ASCII")

        # A SECOND ASCII ROW, BECAUSE THE FIRST ONE CANNOT SEE THE HAZARD.
        # The route above serves the EMPTY state: no roster, so every byte it
        # measures is text this repository authored, and it stayed green on
        # both sides of a real defect. A `display_name` is a nickname another
        # player typed and arrives from `enka.network`. `html.escape` closes
        # the markup hole and passes every non-ASCII codepoint through
        # untouched, so this row renders a roster carrying the glyphs the tree
        # bans - built with `chr()`, never typed, or this file would violate
        # the rule it is checking - plus one wide character. Survival is graded
        # too: dropping the name would satisfy `isascii()` and be worse.
        report.add(*_external_name_ascii_row())

        status, _, body = _get(f"{server.base_url}/api/dashboard")
        if status != 200:
            report.add(FAIL, "route /api/dashboard", f"status {status}")
            return
        payload = json.loads(body)
        seen = tuple(p["panel_id"] for p in payload["panels"])
        if seen == EXPECTED_PANELS:
            report.add(OK, "panels", ", ".join(seen))
        else:
            report.add(FAIL, "panels", f"expected {EXPECTED_PANELS}, got {seen}")

        # The invariant ADR-005 exists for: a panel that is not live must say
        # what it is waiting on, and must never show a placeholder number.
        offenders = [
            p["panel_id"]
            for p in payload["panels"]
            if p["state"] != "ready" and not p["waiting_on"]
        ]
        if offenders:
            report.add(FAIL, "readiness honesty", f"silent gaps: {offenders}")
        else:
            report.add(OK, "readiness honesty", "every non-live panel names what it needs")

        numbered = [
            p["panel_id"] for p in payload["panels"] if p["state"] == "not_wired" and p["rows"]
        ]
        if numbered:
            report.add(FAIL, "no placeholder numbers", f"unwired panels carrying rows: {numbered}")
        else:
            report.add(OK, "no placeholder numbers", "")

        report.add(OK, "freshness", payload.get("freshness", "?"))
        report.add(
            OK,
            "readiness",
            f"{round(payload['readiness'] * 100)}% "
            f"({payload['ready_count']} live, {payload['partial_count']} partial, "
            f"{payload['not_wired_count']} not wired)",
        )

        status, _, body = _get(f"{server.base_url}/no/such/route")
        if status == 404 and "Traceback" not in body:
            report.add(OK, "unknown route", "friendly 404")
        else:
            report.add(FAIL, "unknown route", f"status {status}")
    finally:
        server.stop()


def _external_name_ascii_row() -> tuple[str, str, str]:
    """Render a board whose roster name is not ASCII, and grade the page.

    Returned as a row rather than added in place so the renderer import stays
    next to the check that needs it, and so a failure here reads as a graded
    FAIL instead of an exception - this script is never allowed to raise.
    """
    from datetime import UTC, datetime

    from core.types import AccountState, MappedCharacter
    from surface.model import build_dashboard
    from surface.render import render_html

    glyphs = (chr(0x2014), chr(0x2013), chr(0x2019), chr(0x00A0), chr(0x4E2D))
    display_name = "Ayaka" + "".join(glyphs)
    state = AccountState(uid="000000000")
    state.roster = (
        MappedCharacter(
            avatar_id=10000002,
            level=90,
            ascension=6,
            constellations=0,
            display_name=display_name,
        ),
    )
    try:
        page = render_html(
            build_dashboard(state, now=datetime(2026, 9, 6, 19, 30, tzinfo=UTC))
        )
    except Exception as exc:  # noqa: BLE001 - a row, never a traceback
        return (FAIL, "external name is ascii", f"{exc.__class__.__name__}")

    if not page.isascii():
        offenders = sorted({hex(ord(ch)) for ch in page if not ch.isascii()})
        return (FAIL, "external name is ascii", f"raw codepoints reached the page: {offenders}")
    encoded = "Ayaka" + "".join(f"&#{ord(ch)};" for ch in glyphs)
    if encoded not in page:
        return (FAIL, "external name is ascii", "ascii, but the name was dropped not encoded")
    return (OK, "external name is ascii", f"{len(glyphs)} glyphs survived as numeric refs")


def _version_tuple(text: str) -> tuple[int, ...] | None:
    """`"0.16.6"` to `(0, 16, 6)`, or None when any segment is not a plain integer.

    NO THIRD-PARTY IMPORT. `packaging` is present on this box only because
    pytest happens to depend on it, and this file is a SCRIPT an operator runs
    outside pytest. Leaning on it would work here and vanish elsewhere.

    The cost of that choice is stated rather than hidden: this understands
    dotted integers and nothing else, so `1.0.0rc1`, `2.3.1+local` and a git sha
    all return None and are reported as not comparable. That is the right
    failure - a wrong ordering asserted confidently is worse than declining.
    """
    parts: list[int] = []
    for chunk in text.strip().split("."):
        if not chunk.isdigit():
            return None
        parts.append(int(chunk))
    return tuple(parts) if parts else None


def _compare_versions(installed: str, pinned: str) -> int | None:
    """-1 installed is older, 0 equal, 1 installed is newer, None not comparable.

    Zero-padded to a common length so `1.2` and `1.2.0` compare equal rather
    than the shorter one sorting first.
    """
    left = _version_tuple(installed)
    right = _version_tuple(pinned)
    if left is None or right is None:
        return None
    width = max(len(left), len(right))
    left += (0,) * (width - len(left))
    right += (0,) * (width - len(right))
    return (left > right) - (left < right)


def check_dev_pin_drift(report: Report) -> None:
    """Report - never enforce - the gap between what is installed and what is pinned.

    WHY THIS IS A REPORTER AND NOT A GUARD. CI pip-installs requirements-dev.txt
    on a clean ubuntu-latest runner before it runs a single gate, so the runner
    is AT the pin by construction whatever the pin says. An equality assertion
    would therefore be green on the lane that decides whether a commit ships and
    red on every developer box that has not just reinstalled - backwards from
    useful, and a guard that only ever reddens locally is a guard the operator
    turns off. `tests/test_dev_pin_declaration.py` carries the half of this that
    IS host-independent: that the gates' tools are pinned at all.

    WHY THE DIRECTION IS PRINTED AND NOT JUST "differs". The direction is the
    whole actionable content. If the local tool is OLDER than the pin, CI runs a
    NEWER one whose new rules this box never applied, so a local green is
    OPTIMISTIC - it can still go red on the runner. If the local tool is NEWER,
    the local run is the stricter of the two and a local green is PESSIMISTIC.
    A bare "differs" leaves the reader unable to tell which way to worry.
    """
    import re
    from importlib.metadata import PackageNotFoundError, version

    pin_file = REPO_ROOT / "requirements-dev.txt"
    try:
        text = pin_file.read_text(encoding="utf-8")
    except OSError as exc:
        report.add(NOTE, "dev pin drift", f"requirements-dev.txt unreadable ({exc.__class__.__name__})")
        return

    pinned_rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$", line)
        if match:
            pinned_rows.append((match.group(1), match.group(2)))

    if not pinned_rows:
        report.add(NOTE, "dev pin drift", "requirements-dev.txt declares no == pins, so there is nothing to compare")
        return

    for name, pinned in pinned_rows:
        try:
            installed = version(name)
        except PackageNotFoundError:
            report.add(NOTE, f"dev pin {name}", f"pinned {pinned}, not installed here - CI installs it on the runner")
            continue
        except Exception as exc:  # noqa: BLE001 - a friendly row, never a raw error string
            report.add(NOTE, f"dev pin {name}", f"pinned {pinned}, installed version unreadable ({exc.__class__.__name__})")
            continue
        order = _compare_versions(installed, pinned)
        if order is None:
            direction = "not comparable - a version segment is not a plain integer"
        elif order == 0:
            direction = "AT THE PIN"
        elif order < 0:
            direction = "OLDER here than CI - a local green is OPTIMISTIC"
        else:
            direction = "NEWER here than CI - a local green is PESSIMISTIC"
        report.add(NOTE, f"dev pin {name}", f"{installed} installed / {pinned} pinned - {direction}")


def check_snapshot(report: Report) -> None:
    """Is there a cold-start source, and how old is it?"""
    from core.config import load_config
    from core.state_io import DEFAULT_STATE_FILENAME, read_state

    target = Path(load_config().data_dir) / DEFAULT_STATE_FILENAME
    if not target.exists():
        report.add(
            SKIP,
            "account snapshot",
            "none yet - the dashboard renders the empty state, which is correct for an unplayed account",
        )
        return
    state = read_state(target)
    if state is None:
        report.add(FAIL, "account snapshot", "present but unreadable - see the log")
    else:
        report.add(OK, "account snapshot", f"{len(state.roster)} roster entries")


def check_runtime(report: Report) -> None:
    """Artefacts outside the repository: the Electron binary and the shortcut."""
    electron = REPO_ROOT / "shell" / "node_modules" / "electron" / "dist" / "electron.exe"
    if electron.is_file():
        report.add(OK, "electron runtime", f"{electron.stat().st_size // (1024 * 1024)} MB")
    else:
        report.add(SKIP, "electron runtime", "absent - install with: npm install --prefix shell")

    import os

    profile = os.environ.get("USERPROFILE")
    if not profile:
        report.add(SKIP, "desktop shortcut", "no user profile on this platform")
        return

    # LOOKED UP BY TARGET, NOT BY NAME, and reusing make_shortcut's own
    # comparison so the two cannot disagree. The operator renamed the shortcut
    # this project created; a name-only check reported it absent, which is a
    # false negative, and false negatives are how a QA report stops being read.
    # The FILE is named in the output, never the directory: a profile path
    # carries the Windows account name.
    from scripts import make_shortcut

    desktop = Path(profile) / "Desktop"
    canonical = desktop / (make_shortcut.DEFAULT_SHORTCUT_NAME + make_shortcut.SHORTCUT_SUFFIX)
    desired = make_shortcut.desired_state()

    powershell = make_shortcut._resolve_powershell()
    if powershell is None:
        report.add(SKIP, "desktop shortcut", "no PowerShell to read a shortcut with")
        return

    observed = make_shortcut.observe(powershell, canonical)
    if observed is not None and make_shortcut.matches(observed, desired):
        report.add(OK, "desktop shortcut", canonical.name)
        return

    twin = make_shortcut.find_renamed_twin(powershell, desktop, desired, skip=canonical)
    if twin is not None:
        report.add(OK, "desktop shortcut", f"{twin.name} (renamed from the default)")
    else:
        report.add(SKIP, "desktop shortcut", "absent - create with: python scripts/make_shortcut.py")


def check_live_dashboard(report: Report) -> None:
    """Is a dashboard already up on the reserved port? Purely informational."""
    from core import ports

    try:
        status, _, body = _get(f"http://127.0.0.1:{ports.DASHBOARD}/health", timeout=2.0)
    except OSError:
        report.add(SKIP, "live dashboard", f"nothing listening on {ports.DASHBOARD}")
        return
    if status == 200:
        report.add(OK, "live dashboard", f"answering on {ports.DASHBOARD}, pid {json.loads(body).get('pid')}")
    else:
        report.add(FAIL, "live dashboard", f"something on {ports.DASHBOARD} answered {status}")


def main() -> int:
    print("ResinCompute companion QA\n")
    report = Report()
    for check in (
        check_ports,
        check_shell_contract,
        check_surface,
        check_dev_pin_drift,
        check_snapshot,
        check_runtime,
        check_live_dashboard,
    ):
        try:
            check(report)
        except Exception as exc:  # noqa: BLE001 - a broken check must not hide the others
            report.add(FAIL, check.__name__, f"{exc.__class__.__name__}: {exc}")
    return report.render()


if __name__ == "__main__":
    sys.exit(main())
