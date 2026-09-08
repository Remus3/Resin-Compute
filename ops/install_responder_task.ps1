# install_responder_task.ps1 - register ResinCompute-Responder for ONE window.
#
# Usage, from the repo root:
#
#     powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -WhatIfOnly
#     powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 `
#         -WindowOpens '2026-09-07T19:00:00' -WindowCloses '2026-09-07T21:00:00'
#
#     powershell -ExecutionPolicy Bypass -File .\ops\install_responder_task.ps1 -Remove
#
# ---------------------------------------------------------------------------
# ASCII-ONLY RULE, and it is mechanical rather than stylistic. Windows
# PowerShell 5.1 ParseFile ANSI-decodes a .ps1 carrying no BOM, so a UTF-8
# em-dash inside a DOUBLE-QUOTED string decodes into a smart quote, the
# tokenizer treats it as a string terminator, and the parse fails far from the
# real cause naming the wrong line. Prefer SINGLE-quoted strings: they do not
# interpolate, so a stray character cannot start an expansion.
# ---------------------------------------------------------------------------
#
# THIS SCRIPT IS THE ARMING ACT. Registering this task is what turns a built
# responder into a running one, and the responder itself refuses to act unless
# invoked with --arm, which only this task supplies. Two independent stops on
# the window - the trigger's EndBoundary and the responder's own check - because
# a kill switch that exists in one place is one bug away from absent.
#
# -Remove is the kill switch and it is deliberately the simplest path in this
# file. An operator ending a trial should not have to read anything.

[CmdletBinding()]
param(
    [string] $InstallRoot,

    # pythonw and not python: a scheduled task started with python.exe flashes a
    # console window on every fire.
    [string] $PythonwExe,

    [string] $TaskUser,

    [string] $TaskName = 'ResinCompute-Responder',

    # The AGREED window. Both operators hold a kill switch; this is the half
    # that stops the scheduler even if nobody is watching.
    [string] $WindowOpens,
    [string] $WindowCloses,

    # Print what would be registered and exit without touching the scheduler.
    [switch] $WhatIfOnly,

    # Unregister the task. The kill switch.
    [switch] $Remove
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step {
    param([string] $Message)
    Write-Host ('[responder] ' + $Message)
}

function Resolve-ConsolePython {
    # The TASK runs under pythonw.exe so it does not flash a console on every
    # fire. The liveness CHECKER is the opposite case - it is run here, once,
    # interactively, and its report has to reach the operator's screen, so it
    # needs console python.exe. Returns $null rather than throwing: an absent
    # interpreter must degrade into an honest UNVERIFIED, never into a silent
    # fallback that prints a state string as if it had answered.
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

# --- The kill switch runs before anything else needs resolving -------------

if ($Remove) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        Write-Step ('not registered, nothing to remove: ' + $TaskName)
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Step ('UNREGISTERED: ' + $TaskName)
    exit 0
}

# --- Resolve the install root ----------------------------------------------

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $InstallRoot = Split-Path -Parent $scriptDir
}
$InstallRoot = (Resolve-Path -LiteralPath $InstallRoot).Path

if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot 'tools/moon_sync_responder.py'))) {
    throw ('InstallRoot does not carry the responder: ' + $InstallRoot)
}

# --- Resolve pythonw.exe ---------------------------------------------------

if ([string]::IsNullOrWhiteSpace($PythonwExe)) {
    $candidate = Get-Command -Name 'pythonw.exe' -ErrorAction SilentlyContinue
    if ($null -eq $candidate) {
        throw 'pythonw.exe not found on PATH - pass -PythonwExe explicitly'
    }
    $PythonwExe = $candidate.Source
}
if (-not (Test-Path -LiteralPath $PythonwExe)) {
    throw ('pythonw.exe does not exist: ' + $PythonwExe)
}

if ([string]::IsNullOrWhiteSpace($TaskUser)) {
    $TaskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
}

# --- The window is REQUIRED, and it is required for a reason ---------------
#
# A responder registered with no window is a responder with no agreed end, and
# the trial's whole premise is that both operators hold a stop. Defaulting this
# to "now plus something" would be choosing a bound nobody agreed to, which is
# the objection RSC raised on the channel about undisclosed bounds.

if ([string]::IsNullOrWhiteSpace($WindowOpens) -or [string]::IsNullOrWhiteSpace($WindowCloses)) {
    throw 'both -WindowOpens and -WindowCloses are required - a trial with no agreed end is not a trial'
}

$opens = [datetime]::Parse($WindowOpens)
$closes = [datetime]::Parse($WindowCloses)
if ($closes -le $opens) {
    throw ('the window closes before it opens: ' + $WindowOpens + ' .. ' + $WindowCloses)
}

$startBoundary = $opens.ToString('yyyy-MM-ddTHH:mm:ss')
$endBoundary = $closes.ToString('yyyy-MM-ddTHH:mm:ss')

# A Repetition carrying StopAtDurationEnd must also carry a Duration, and the
# only sane Duration is the window itself. Minutes rather than hours so a window
# that is not a whole number of hours still registers.
$totalMinutes = [int][math]::Ceiling(($closes - $opens).TotalMinutes)
$repeatDuration = 'PT' + $totalMinutes + 'M'

# --- Substitute and register -----------------------------------------------

$xmlPath = Join-Path $InstallRoot 'ops/ResinCompute-Responder.xml'
if (-not (Test-Path -LiteralPath $xmlPath)) {
    throw ('task definition missing: ' + $xmlPath)
}

$xml = Get-Content -LiteralPath $xmlPath -Raw

# THE DECLARATION MUST SAY UTF-16, AND THE FILE ON DISK MUST STAY ASCII.
#
# Register-ScheduledTask takes the XML as a .NET STRING, which is UTF-16 in
# memory. A string whose declaration says encoding="UTF-8" makes the parser
# refuse with "The task XML is malformed. (1,40)::ERROR: unable to switch" -
# an error naming the XML declaration and nothing about the task.
#
# ops/ResinCompute-Supervisor.xml carries a comment arguing the opposite: that
# because the API takes text, the on-disk encoding is ours to choose. The first
# half is right and the conclusion is wrong, and this cost two failed
# registrations to find. That task is not registered on this machine, so the
# claim had never been tested. Measured 2026-09-07.
#
# The file stays 7-bit ASCII per the repo rule; only the string handed to the
# API is relabelled.
$xml = $xml -replace '^\s*<\?xml[^>]*\?>', '<?xml version="1.0" encoding="UTF-16"?>' 
$xml = $xml.Replace('__PYTHONW_EXE__', $PythonwExe)
$xml = $xml.Replace('__INSTALL_ROOT__', $InstallRoot)
$xml = $xml.Replace('__TASK_USER__', $TaskUser)
$xml = $xml.Replace('__START_BOUNDARY__', $startBoundary)
$xml = $xml.Replace('__END_BOUNDARY__', $endBoundary)
$xml = $xml.Replace('__REPEAT_DURATION__', $repeatDuration)

if ($xml -match '__[A-Z_]+__') {
    throw ('a placeholder was left unsubstituted: ' + $Matches[0])
}

Write-Step ('install root : ' + $InstallRoot)
Write-Step ('interpreter  : ' + $PythonwExe)
Write-Step ('task user    : ' + $TaskUser)
Write-Step ('window opens : ' + $startBoundary)
Write-Step ('window closes: ' + $endBoundary)
Write-Step ('cadence      : every 5 minutes for ' + $repeatDuration + ', stopping at the window end')
Write-Step  'kill switch  : -Remove, or Disable-ScheduledTask'

if ($WhatIfOnly) {
    Write-Step 'WhatIfOnly - nothing was registered'
    exit 0
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    Write-Step ('replacing existing task: ' + $TaskName)
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Xml $xml -User $TaskUser | Out-Null
Write-Step ('REGISTERED: ' + $TaskName)

$check = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $check) {
    throw 'registration reported success but the task is not present'
}
Write-Step ('present in the scheduler store: ' + $TaskName)

# --- Liveness, which is NOT the same question as State ---------------------
#
# A scheduled task reports State Ready and last result 0 FOREVER once every
# trigger on it has expired. There is no state value meaning "expired".
# Measured on this machine 2026-09-08: this very task read Ready with its
# EndBoundary twenty-four hours in the past, NextRunTime EMPTY, and not one
# invocation-log line since. It will never fire again. A session read that
# Ready and wrote "Ready on a 5-minute tick" into the hand-off, wrong by a day.
#
# So State is printed below as CONTEXT and never as the verdict. The verdict
# comes from ops/check_task_liveness.py, whose command-line contract is fixed:
# it exits 0 IF AND ONLY IF the task is positively established to fire again.
# Every non-zero exit means NOT ESTABLISHED - the values are deliberately not
# enumerated here, so that checker can add new ones without lying through this
# script.

Write-Step ('context only, not a verdict - reported state is ' + $check.State)

$livenessChecker = Join-Path $InstallRoot 'ops\check_task_liveness.py'
$consolePython = Resolve-ConsolePython

if (-not (Test-Path -LiteralPath $livenessChecker)) {
    Write-Step 'LIVENESS UNVERIFIED - ops/check_task_liveness.py is absent, and a state string does not answer the question.'
    Write-Step 'The task is REGISTERED. Whether it will ever fire is UNKNOWN from this script.'
    exit 3
}
if ($null -eq $consolePython) {
    Write-Step 'LIVENESS UNVERIFIED - no console python.exe was found to run the liveness checker.'
    Write-Step 'The task is REGISTERED. Whether it will ever fire is UNKNOWN from this script.'
    exit 3
}

Write-Step ('running the liveness checker: ' + $consolePython + ' ' + $livenessChecker + ' ' + $TaskName)
& $consolePython $livenessChecker $TaskName
$livenessExit = $LASTEXITCODE

if ($livenessExit -eq 0) {
    Write-Step 'LIVENESS ESTABLISHED - the checker exited 0, so this task is positively established to fire again.'
} else {
    Write-Step ('LIVENESS NOT ESTABLISHED - the checker exited ' + $livenessExit + '. The task is registered, but it is NOT established that it will fire again. Read the checker report above.')
}
exit $livenessExit
