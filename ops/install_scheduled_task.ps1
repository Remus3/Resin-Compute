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

if ($xml -match '__[A-Z_]+__') {
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
Write-Step ('Verified. State: ' + $check.State)
Write-Step 'Start it now with: Start-ScheduledTask -TaskName ResinCompute-Supervisor'

# NOTE ON STOPPING THE CHILD, inherited hard rule: never use Stop-Process to
# kill the supervised process. Use: taskkill /F /PID <pid>
# ops/supervisor.py implements that path itself; this note is here so an
# operator reading the installer does not reach for Stop-Process by habit.
exit 0
