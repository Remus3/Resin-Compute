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
    0  every check passed, or passed with skips
    1  at least one check FAILED
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
        print(f"\n  {passed} passed, {failed} failed, {skipped} skipped")
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
            report.add(OK, "page is ascii", "")
        else:
            report.add(FAIL, "page is ascii", "the rendered page left 7-bit ASCII")

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
