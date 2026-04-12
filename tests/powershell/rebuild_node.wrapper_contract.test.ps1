param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot "../.." "rebuild_node.ps1")
)

$ErrorActionPreference = "Stop"

$resolvedScriptPath = (Resolve-Path -Path $ScriptPath).Path
$scriptText = Get-Content -Path $resolvedScriptPath -Raw

if ($scriptText -notmatch 'rebuild_rust\.ps1' -or $scriptText -notmatch '-Target\s+node') {
    throw "Expected rebuild_node.ps1 to delegate to rebuild_rust.ps1 -Target node."
}

foreach ($forbidden in @('bun run build', 'bun run build:debug', 'cargo clean -p classic-node', 'node_modules')) {
    if ($scriptText -match [regex]::Escape($forbidden)) {
        throw "Expected rebuild_node.ps1 to avoid maintaining standalone Node rebuild logic ('$forbidden')."
    }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("classic-phase08-node-wrapper-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot | Out-Null

try {
    Copy-Item -Path $resolvedScriptPath -Destination (Join-Path $tempRoot "rebuild_node.ps1")
    @'
param(
    [string]$Target,
    [switch]$Clean,
    [switch]$DebugBuild
)

$payload = [ordered]@{
    Target = $Target
    Clean = [bool]$Clean
    DebugBuild = [bool]$DebugBuild
}

$payload | ConvertTo-Json -Compress | Set-Content -Path (Join-Path $PSScriptRoot "delegation.json") -Encoding utf8
'@ | Set-Content -Path (Join-Path $tempRoot "rebuild_rust.ps1") -Encoding utf8

    & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tempRoot "rebuild_node.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Expected rebuild_node.ps1 release delegation to succeed."
    }

    $releasePayload = Get-Content -Path (Join-Path $tempRoot "delegation.json") -Raw | ConvertFrom-Json
    if ($releasePayload.Target -ne 'node' -or $releasePayload.Clean -ne $false -or $releasePayload.DebugBuild -ne $false) {
        throw "Expected release wrapper invocation to delegate exactly Target=node, Clean=false, DebugBuild=false."
    }

    & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tempRoot "rebuild_node.ps1") -Clean -Debug
    if ($LASTEXITCODE -ne 0) {
        throw "Expected rebuild_node.ps1 debug delegation to succeed."
    }

    $debugPayload = Get-Content -Path (Join-Path $tempRoot "delegation.json") -Raw | ConvertFrom-Json
    if ($debugPayload.Target -ne 'node' -or $debugPayload.Clean -ne $true -or $debugPayload.DebugBuild -ne $true) {
        throw "Expected debug wrapper invocation to delegate exactly Target=node, Clean=true, DebugBuild=true."
    }
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item -Path $tempRoot -Recurse -Force
    }
}

Write-Host "PASS: rebuild_node.ps1 stays a thin wrapper over rebuild_rust.ps1 -Target node."
