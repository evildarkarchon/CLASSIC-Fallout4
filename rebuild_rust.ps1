<#
.SYNOPSIS
    General-purpose Rust rebuild script for CLASSIC.

.DESCRIPTION
    Rebuilds the CLASSIC Rust workspace (cargo build --workspace), optionally
    filtered to specific crates.

.PARAMETER Target
    Rebuild scope:
      - workspace : Build full Rust workspace via cargo (default)

.PARAMETER Crates
    Optional positional filters mapped to cargo package filters (`cargo build -p <crate>`).

.PARAMETER Clean
    Perform clean rebuild behavior for selected targets.

.PARAMETER DebugBuild
    Use debug-oriented build commands (omit `--release`).

.EXAMPLE
    ./rebuild_rust.ps1
    # Default: rebuild Rust workspace

.EXAMPLE
    ./rebuild_rust.ps1 classic_yaml
    # Default workspace target with package filter equivalent to `cargo build -p classic_yaml`

.EXAMPLE
    ./rebuild_rust.ps1 -Target workspace classic-scanlog-core
    # Rebuild only specific Rust workspace crate(s)

.EXAMPLE
    ./rebuild_rust.ps1 -Target workspace -Clean
    # Clean + rebuild Rust workspace

.EXAMPLE
    ./rebuild_rust.ps1 -Clean
    # Clean + rebuild entire Rust workspace
#>

param (
    [Parameter(ValueFromRemainingArguments = $true, Position = 0)]
    [string[]]$Crates,

    [Parameter(Mandatory = $false)]
    [ValidateSet("workspace")]
    [string]$Target = "workspace",

    [Parameter(Mandatory = $false)]
    [switch]$Clean,

    [Parameter(Mandatory = $false)]
    [switch]$DebugBuild
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$WorkspaceRootManifest = Join-Path $ProjectRoot "Cargo.toml"

function Assert-LastExitCode {
    param (
        [string]$CommandLabel
    )

    if ($LASTEXITCODE -ne 0) {
        Write-Error "$CommandLabel failed with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
}

function Invoke-RustWorkspaceRebuild {
    param (
        [switch]$CleanBuild,
        [switch]$DebugBuild,
        [string[]]$CrateFilters
    )

    if (-not (Test-Path $WorkspaceRootManifest)) {
        Write-Error "Rust workspace manifest not found: $WorkspaceRootManifest"
        exit 1
    }

    if ($CleanBuild) {
        Write-Host "🧹 Cleaning Rust workspace..." -ForegroundColor Cyan
        Push-Location $ProjectRoot
        try {
            & cargo clean
            Assert-LastExitCode -CommandLabel "cargo clean"
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host "ℹ️  Skipping workspace clean step (use -Clean to force)" -ForegroundColor Gray
    }

    $cargoArgs = @("build")
    if ($CrateFilters -and $CrateFilters.Count -gt 0) {
        Write-Host "Using workspace crate filters: $($CrateFilters -join ', ')" -ForegroundColor Cyan
        foreach ($crate in $CrateFilters) {
            $cargoArgs += @("-p", $crate)
        }
    }
    else {
        $cargoArgs += "--workspace"
    }
    if (-not $DebugBuild) {
        $cargoArgs += "--release"
    }

    Write-Host "🔨 Building Rust workspace..." -ForegroundColor Yellow
    Write-Host "cargo $($cargoArgs -join ' ')" -ForegroundColor DarkGray
    Push-Location $ProjectRoot
    try {
        & cargo @cargoArgs
        Assert-LastExitCode -CommandLabel "cargo build --workspace"
    }
    finally {
        Pop-Location
    }

    Write-Host "✨ Rust workspace rebuild complete!" -ForegroundColor Green
}

Write-Host "CLASSIC Rust rebuild script" -ForegroundColor Cyan
Write-Host "Target: $Target" -ForegroundColor Cyan

switch ($Target) {
    "workspace" {
        Invoke-RustWorkspaceRebuild -CleanBuild:$Clean -DebugBuild:$DebugBuild -CrateFilters $Crates
    }
}

Write-Host "✨ Rebuild target '$Target' complete." -ForegroundColor Green
