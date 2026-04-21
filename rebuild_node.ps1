<#
.SYNOPSIS
    Delegate CLASSIC Node.js/Bun addon rebuilds to rebuild_rust.ps1.
.DESCRIPTION
    Thin compatibility wrapper that preserves the public rebuild_node.ps1 entrypoint
    while routing all Node rebuild behavior through the canonical repo-root
    rebuild_rust.ps1 -Target node flow.
.PARAMETER Clean
    Perform a clean node rebuild.
.PARAMETER Debug
    Build in debug mode instead of release.
#>
param(
    [switch]$Clean,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

$rebuildRustScript = Join-Path $PSScriptRoot "rebuild_rust.ps1"
if (-not (Test-Path $rebuildRustScript)) {
    Write-Error "Canonical rebuild script not found at '$rebuildRustScript'. Use the repo-root rebuild_rust.ps1 entrypoint."
    exit 1
}

Write-Host "Delegating to rebuild_rust.ps1 -Target node..." -ForegroundColor Cyan
& $rebuildRustScript -Target node -Clean:$Clean -DebugBuild:$Debug
$exitCode = if ($LASTEXITCODE -is [int]) { $LASTEXITCODE } else { 0 }
if ($exitCode -ne 0) {
    exit $exitCode
}
