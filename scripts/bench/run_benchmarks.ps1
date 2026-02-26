<#
.SYNOPSIS
    Runs Criterion benchmarks with repeatable suite targeting.

.DESCRIPTION
    Wrapper around `cargo bench` with consistent mode handling and baseline options.
    Supports running either all workspace benchmarks or the Rust DB baseline suite.

    Modes:
    - quick (default): sample_size=50, measurement_time=3s
    - thorough: sample_size=200, measurement_time=10s

.PARAMETER Mode
    Benchmark mode: quick (default) or thorough.

.PARAMETER SaveBaseline
    Save benchmark outputs as a named Criterion baseline.

.PARAMETER BaselineName
    Baseline name used with -SaveBaseline or -Compare.
    If omitted with -SaveBaseline, a timestamped name is generated.

.PARAMETER Compare
    Run benchmarks and compare against an existing Criterion baseline.

.PARAMETER Suite
    Benchmark suite to run:
    - all (default): cargo bench across the workspace
    - rust-db-baseline: targeted DB baseline benches only

.PARAMETER Crate
    Optional crate override. When set, runs only that crate's benchmarks.

.PARAMETER Filter
    Optional benchmark filter passed after `--`.

.PARAMETER List
    List benchmarks instead of running measurements.

.EXAMPLE
    .\scripts\bench\run_benchmarks.ps1 -Suite rust-db-baseline -Mode quick

.EXAMPLE
    .\scripts\bench\run_benchmarks.ps1 -Suite rust-db-baseline -Mode thorough -SaveBaseline -BaselineName "db-baseline-main"

.EXAMPLE
    .\scripts\bench\run_benchmarks.ps1 -Suite rust-db-baseline -Mode thorough -Compare -BaselineName "db-baseline-main"
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet('quick', 'thorough')]
    [string]$Mode = 'quick',

    [Parameter()]
    [switch]$SaveBaseline,

    [Parameter()]
    [string]$BaselineName,

    [Parameter()]
    [switch]$Compare,

    [Parameter()]
    [ValidateSet('all', 'rust-db-baseline')]
    [string]$Suite = 'all',

    [Parameter()]
    [string]$Crate,

    [Parameter()]
    [string]$Filter,

    [Parameter()]
    [switch]$List
)

$ErrorActionPreference = 'Stop'

if ($SaveBaseline -and $Compare) {
    Write-Error 'Use either -SaveBaseline or -Compare, not both.'
    exit 1
}

if ($Compare -and [string]::IsNullOrWhiteSpace($BaselineName)) {
    Write-Error '-Compare requires -BaselineName.'
    exit 1
}

if ($SaveBaseline -and [string]::IsNullOrWhiteSpace($BaselineName)) {
    $BaselineName = "baseline-$(Get-Date -Format 'yyyy-MM-dd-HHmmss')"
}

# Resolve ClassicLib-rs from script location first, then fallback to CWD.
$rustDirCandidates = @(
    (Join-Path $PSScriptRoot "../../ClassicLib-rs"),
    (Join-Path (Get-Location) "ClassicLib-rs"),
    (Get-Location)
)

$rustDir = $null
foreach ($candidate in $rustDirCandidates) {
    $resolved = Resolve-Path $candidate -ErrorAction SilentlyContinue
    if ($resolved -and (Test-Path (Join-Path $resolved "Cargo.toml"))) {
        $rustDir = $resolved.Path
        break
    }
}

if (-not $rustDir) {
    Write-Error "Could not locate ClassicLib-rs/Cargo.toml."
    exit 1
}

function Build-BenchArgs {
    param(
        [string[]]$TargetArgs
    )

    $commandArgs = @('bench')
    if ($TargetArgs -and $TargetArgs.Count -gt 0) {
        $commandArgs += $TargetArgs
    }

    if ($SaveBaseline) {
        $commandArgs += @('--', '--save-baseline', $BaselineName)
    }
    elseif ($Compare) {
        $commandArgs += @('--', '--baseline', $BaselineName)
    }

    if ($Filter) {
        if ($commandArgs -notcontains '--') {
            $commandArgs += '--'
        }
        $commandArgs += $Filter
    }

    if ($List) {
        if ($commandArgs -notcontains '--') {
            $commandArgs += '--'
        }
        $commandArgs += '--list'
    }

    return $commandArgs
}

$targets = @()
if ($Crate) {
    $targets += @{
        Label = "crate:$Crate"
        Args  = @('-p', $Crate)
    }
}
elseif ($Suite -eq 'rust-db-baseline') {
    $targets += @{
        Label = 'classic-database-core/database_benchmarks'
        Args  = @('-p', 'classic-database-core', '--bench', 'database_benchmarks')
    }
    $targets += @{
        Label = 'classic-scanlog-core/scanlog_benchmarks'
        Args  = @('-p', 'classic-scanlog-core', '--bench', 'scanlog_benchmarks')
    }
}
else {
    $targets += @{
        Label = 'workspace-all'
        Args  = @()
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CLASSIC Benchmark Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[Config] Mode: $Mode" -ForegroundColor Yellow
Write-Host "[Config] Suite: $Suite" -ForegroundColor Yellow
if ($Crate) {
    Write-Host "[Config] Crate override: $Crate" -ForegroundColor Yellow
}
if ($Filter) {
    Write-Host "[Config] Filter: $Filter" -ForegroundColor Yellow
}
if ($SaveBaseline) {
    Write-Host "[Config] Save baseline: $BaselineName" -ForegroundColor Yellow
}
if ($Compare) {
    Write-Host "[Config] Compare baseline: $BaselineName" -ForegroundColor Yellow
}
if ($List) {
    Write-Host "[Config] List only: enabled" -ForegroundColor Yellow
}
Write-Host "[Directory] $rustDir" -ForegroundColor DarkGray
Write-Host ""

$env:BENCH_MODE = $Mode
$start = Get-Date
$exitCode = 0

Push-Location $rustDir
try {
    foreach ($target in $targets) {
        $benchArgs = Build-BenchArgs -TargetArgs $target.Args
        Write-Host "----------------------------------------" -ForegroundColor Cyan
        Write-Host "[Target] $($target.Label)" -ForegroundColor Cyan
        Write-Host "[Command] cargo $($benchArgs -join ' ')" -ForegroundColor DarkGray
        Write-Host ""

        & cargo @benchArgs
        if ($LASTEXITCODE -ne 0) {
            $exitCode = $LASTEXITCODE
            break
        }
    }
}
finally {
    Pop-Location
    $env:BENCH_MODE = $null
}

$duration = (Get-Date) - $start
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "[Done] Benchmarks completed successfully" -ForegroundColor Green
    if ($SaveBaseline) {
        Write-Host "[Baseline] Saved as: $BaselineName" -ForegroundColor Green
        Write-Host "[Location] $rustDir/target/criterion/$BaselineName" -ForegroundColor DarkGray
    }
}
else {
    Write-Host "[Error] Benchmarks failed (exit code $exitCode)" -ForegroundColor Red
}
Write-Host "[Duration] $($duration.ToString('hh\:mm\:ss\.fff'))" -ForegroundColor DarkGray
Write-Host ""

exit $exitCode
