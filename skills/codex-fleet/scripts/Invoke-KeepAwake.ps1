<#
.SYNOPSIS
    Windows equivalent of macOS `caffeinate -i` — keeps the machine awake while a fleet runs.

.DESCRIPTION
    Idle sleep can interrupt a mid-flight `codex exec` lane: you get a few KB
    of output and zero edits, with no error anywhere. macOS solves this by wrapping each spawn
    in `caffeinate -i`. Windows has no such binary, so this script holds the block instead.

    It sets ES_CONTINUOUS | ES_SYSTEM_REQUIRED via SetThreadExecutionState and keeps it for its
    own lifetime. Start it ONCE in the background before spawning lanes, rather than wrapping
    each lane — the flag is thread-scoped, so a wrapper would release it as soon as the
    wrapped command exits.

    It does NOT prevent explicit sleep or lid-close sleep, keep the display on, and it does NOT change any persistent power setting.
    When the process exits — timeout, Ctrl+C, or kill — Windows reverts to normal immediately.

.PARAMETER Minutes
    How long to hold the sleep block. Default 60, maximum 480 (8 hours).

.EXAMPLE
    pwsh -NoProfile -File skills/codex-fleet/scripts/Invoke-KeepAwake.ps1 -Minutes 90 &

    Start from Git Bash before spawning a fleet. Prints the PID; kill it when the fleet is done.

.EXAMPLE
    Start-Process pwsh -ArgumentList '-NoProfile','-File','skills/codex-fleet/scripts/Invoke-KeepAwake.ps1','-Minutes','120' -WindowStyle Hidden

    Same thing from a PowerShell prompt.

.OUTPUTS
    KEEPAWAKE_ON until=<timestamp> minutes=<n> pid=<pid>
    KEEPAWAKE_OFF reason=timeout
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 480)]
    [int]$Minutes = 60
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This helper requires Windows and PowerShell 7+.' }

Add-Type -Namespace CodexFleet -Name Power -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@

# Decimal literals: PowerShell parses 0x80000000 as Int32 and overflows to -2147483648.
$ES_CONTINUOUS      = [uint32]2147483648   # 0x80000000
$ES_SYSTEM_REQUIRED = [uint32]1            # 0x00000001

$previous = [CodexFleet.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)
if ($previous -eq 0) {
    Write-Error 'Could not set the sleep block (SetThreadExecutionState returned 0).'
    exit 1
}

$until = (Get-Date).AddMinutes($Minutes)
Write-Output "KEEPAWAKE_ON until=$($until.ToString('yyyy-MM-dd HH:mm:ss')) minutes=$Minutes pid=$PID"
try {
    while ((Get-Date) -lt $until) { Start-Sleep -Seconds 15 }
    Write-Output 'KEEPAWAKE_OFF reason=timeout'
}
finally {
    [CodexFleet.Power]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
}
