# install_scheduled_task.ps1 - register ResinCompute-Supervisor.
#
# Usage, from the repo root:
#
#     powershell -ExecutionPolicy Bypass -File .\ops\install_scheduled_task.ps1
#     powershell -ExecutionPolicy Bypass -File .\ops\install_scheduled_task.ps1 -WhatIfOnly
#
# ---------------------------------------------------------------------------
# ASCII-ONLY RULE. This file must stay pure 7-bit ASCII, and the reason is
# mechanical rather than stylistic.
#
# Windows PowerShell 5.1 ParseFile ANSI-decodes a .ps1 that carries no BOM. A
# UTF-8 em-dash inside a DOUBLE-QUOTED string therefore decodes into a
# smart-quote character, the tokenizer treats that as a string terminator, and
# the parse fails somewhere far away from the real cause with an error that
# names the wrong line. Sibling-C lost a boot script to exactly this on
# 2026-05-18. The same applies to en-dashes and to smart quotes.
#
# Two defences, both used here:
#   1. No non-ASCII byte anywhere in this file. Use a spaced hyphen for a
#      clause break.
#   2. Prefer SINGLE-quoted strings. They do not interpolate, so a stray
#      character cannot start an expansion, and the failure mode above needs a
#      double-quoted string to bite.
# ---------------------------------------------------------------------------
#
# The task itself is defined in ops/ResinCompute-Supervisor.xml. This script
# only substitutes the placeholders and registers it, so the task shape lives
# in one place and is reviewable as data.

[CmdletBinding()]
param(
    # Repo checkout to install from. Defaults to this script's parent's parent,
    # which is the repo root when the file is left where it was committed.
    [string] $InstallRoot,

    # Full path to pythonw.exe. pythonw and not python: a logon-triggered task
    # started with python.exe flashes a console window on every boot and on
    # every restart.
    [string] $PythonwExe,

    # Account the task runs as. Defaults to the current user.
    [string] $TaskUser,

    [string] $TaskName = 'ResinCompute-Supervisor',

    # Print what would be registered and exit without touching the scheduler.
    [switch] $WhatIfOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step {
    param([string] $Message)
    Write-Host ('[install] ' + $Message)
}

function Resolve-ConsolePython {
    # The TASK runs under pythonw.exe so a logon-triggered start does not flash
    # a console. The liveness CHECKER is the opposite case - run here, once,
    # with its report going to the operator's screen - so it needs console
    # python.exe. Returns $null rather than throwing: an absent interpreter
    # must degrade into an honest UNVERIFIED, never into a silent fallback that
    # prints a state string as if it had answered the question.
    if (-not [string]::IsNullOrWhiteSpace($PythonwExe)) {
        $sibling = Join-Path (Split-Path -Parent $PythonwExe) 'python.exe'
        if (Test-Path -LiteralPath $sibling) {
            return $sibling
        }
    }
    $found = Get-Command -Name 'python.exe' -ErrorAction SilentlyContinue
    if ($null -ne $found) {
        return $found.Source
    }
    return $null
}

# --- Resolve the install root ---------------------------------------------

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $InstallRoot = Split-Path -Parent $scriptDir
}
$InstallRoot = (Resolve-Path -LiteralPath $InstallRoot).Path

if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot 'ops'))) {
    throw ('InstallRoot does not look like a ResinCompute checkout: ' + $InstallRoot)
}

# --- Resolve pythonw.exe ---------------------------------------------------

if ([string]::IsNullOrWhiteSpace($PythonwExe)) {
    $candidate = Get-Command -Name 'pythonw.exe' -ErrorAction SilentlyContinue
    if ($null -ne $candidate) {
        $PythonwExe = $candidate.Source
    }
}
if ([string]::IsNullOrWhiteSpace($PythonwExe)) {
    throw 'Could not locate pythonw.exe. Pass -PythonwExe with the full path.'
}
if (-not (Test-Path -LiteralPath $PythonwExe)) {
    throw ('pythonw.exe not found at: ' + $PythonwExe)
}

# --- Resolve the task user -------------------------------------------------

if ([string]::IsNullOrWhiteSpace($TaskUser)) {
    $TaskUser = ($env:USERDOMAIN + '\' + $env:USERNAME)
}

# --- Load the task definition and substitute the placeholders --------------

$xmlPath = Join-Path $InstallRoot 'ops\ResinCompute-Supervisor.xml'
if (-not (Test-Path -LiteralPath $xmlPath)) {
    throw ('Task definition not found at: ' + $xmlPath)
}

$xml = Get-Content -LiteralPath $xmlPath -Raw
$xml = $xml.Replace('__PYTHONW_EXE__', $PythonwExe)
$xml = $xml.Replace('__INSTALL_ROOT__', $InstallRoot)
$xml = $xml.Replace('__TASK_USER__', $TaskUser)

# THE GRAMMAR IS THE DELIMITER, NOT THE SPELLING.
#
# Derived by SUBTRACTION rather than by listing the Replace calls above, which
# would only ever restate them and would omit the token nobody named. Scanning
# ops/ResinCompute-Supervisor.xml and ops/ResinCompute-Responder.xml for the
# delimiter pair alone - every __...__ run, whatever it spells - returns the three
# tokens above and the responder's six, and NOTHING ELSE. In the template
# files the delimiter is a perfect discriminator: every occurrence of it is a
# placeholder and no other construct uses it. Subtracting what the previous
# '__[A-Z_]+__' already caught left the EMPTY SET, so this widening fixes no
# surviving token that exists today.
#
# What it does fix is the guard's REACH. This guard's subject is the string about
# to reach Register-ScheduledTask, and its token content is set by two lists
# maintained separately by hand - the template, which is editable data, and the
# Replace calls above. The guard exists to catch DRIFT between them, so a
# grammar derived from the current SPELLING of one list is exactly as tight as
# the other already is and adds nothing. Only the DELIMITER is invariant across
# a template edit.
#
# WHICH AXIS ACTUALLY LEAKED, and it is not the one this was first reported as.
# PowerShell's -match is case-INSENSITIVE; -cmatch is the case-sensitive
# operator. The old '__[A-Z_]+__' therefore behaved as '__[A-Za-z_]+__' at
# runtime, so a lowercase token never leaked at all. Measured 2026-09-11 end to
# end against both real installers with -WhatIfOnly, return codes read in
# Python: a planted '__pythonw_exe__' threw in BOTH (rc=1), while a planted
# '__Slot1__' cleared BOTH (rc=0) and would have been registered verbatim. The
# axis that defeated the guard was the DIGIT, and only the digit.
#
# The inner class is written out rather than as \w. .NET's \w is Unicode-aware,
# so it would also match non-ASCII text arriving through a substituted path;
# this stays deterministic and ASCII-scoped. Spelling both cases out rather than
# leaning on -match's case-insensitivity also closes a second gap: the graders
# in tests/ compile this pattern with Python's re, which IS case-sensitive, so a
# class that is not case-complete makes the grader and the installer disagree
# about a token neither of them names.
#
# COST, stated rather than hidden: a checkout under a directory spelled
# my__build__2 now trips this where it did not before. That failure is loud,
# names the matched text and is recoverable in one read. The failure it replaces
# is a task ARMED with a literal placeholder inside its argv, which the
# scheduler reports as State Ready forever.
if ($xml -match '__[A-Za-z0-9_]+__') {
    throw ('Unsubstituted placeholder left in the task XML: ' + $Matches[0])
}

Write-Step ('install root : ' + $InstallRoot)
Write-Step ('interpreter  : ' + $PythonwExe)
Write-Step ('task user    : ' + $TaskUser)
Write-Step ('task name    : ' + $TaskName)
Write-Step ('command      : ' + $PythonwExe + ' -m ops.supervisor')

if ($WhatIfOnly) {
    Write-Step 'WhatIfOnly was set - nothing was registered.'
    exit 0
}

# --- Register --------------------------------------------------------------
#
# Unregister first so a re-run is idempotent rather than failing on an
# existing task. -Confirm:$false because this script is run non-interactively
# from a provisioning step.

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    Write-Step 'Existing task found - unregistering it first.'
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null
Write-Step 'Registered.'

# --- Verify ----------------------------------------------------------------
#
# Do not trust the absence of an error as proof of registration. Read it back.

$check = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $check) {
    throw ('Registration reported success but the task is not present: ' + $TaskName)
}
Write-Step ('Present in the scheduler store: ' + $TaskName)

# The comment above is right and the read that used to sit here was wrong. The
# absence of an error is not proof of registration - true, and handled by the
# null check. But PRESENCE is not proof it will ever fire either, and this line
# used to end on the State string as though it were the verdict.
#
# A scheduled task reports State Ready and last result 0 FOREVER once every
# trigger on it has expired; there is no state value meaning "expired".
# Measured on this machine 2026-09-08 on the sibling responder task: Ready, with
# its EndBoundary a full day in the past and NextRunTime empty. A state string
# names a state, not a capability.
#
# State is therefore printed as CONTEXT below. The verdict comes from
# ops/check_task_liveness.py, whose command-line contract is fixed: exit 0 IF
# AND ONLY IF the task is positively established to fire again. Every non-zero
# exit means NOT ESTABLISHED, and the values are deliberately not enumerated
# here so that checker can add new ones without lying through this script.

Write-Step ('Context only, not a verdict - reported state is ' + $check.State)

$livenessChecker = Join-Path $InstallRoot 'ops\check_task_liveness.py'
$consolePython = Resolve-ConsolePython

if ((-not (Test-Path -LiteralPath $livenessChecker)) -or ($null -eq $consolePython)) {
    if (-not (Test-Path -LiteralPath $livenessChecker)) {
        Write-Step 'LIVENESS UNVERIFIED - ops/check_task_liveness.py is absent, and a state string does not answer the question.'
    } else {
        Write-Step 'LIVENESS UNVERIFIED - no console python.exe was found to run the liveness checker.'
    }
    Write-Step 'The task is REGISTERED. Whether it will ever fire is UNKNOWN from this script.'
    Write-Step 'Start it now with: Start-ScheduledTask -TaskName ResinCompute-Supervisor'
    exit 3
}

Write-Step ('Running the liveness checker: ' + $consolePython + ' ' + $livenessChecker + ' ' + $TaskName)
& $consolePython $livenessChecker $TaskName
$livenessExit = $LASTEXITCODE

if ($livenessExit -eq 0) {
    Write-Step 'LIVENESS ESTABLISHED - the checker exited 0, so this task is positively established to fire again.'
} else {
    Write-Step ('LIVENESS NOT ESTABLISHED - the checker exited ' + $livenessExit + '. The task is registered, but it is NOT established that it will fire again. Read the checker report above.')
}
Write-Step 'Start it now with: Start-ScheduledTask -TaskName ResinCompute-Supervisor'

# NOTE ON STOPPING THE CHILD, inherited hard rule: never use Stop-Process to
# kill the supervised process. Use: taskkill /F /PID <pid>
# ops/supervisor.py implements that path itself; this note is here so an
# operator reading the installer does not reach for Stop-Process by habit.

# The exit code carries the LIVENESS verdict, not merely "the script ran". A
# provisioning step that treats 0 as success therefore fails loudly when the
# task was registered but cannot be established to fire, which is precisely the
# condition that went unnoticed for twenty-four hours.
exit $livenessExit
