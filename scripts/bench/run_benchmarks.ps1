<#
.SYNOPSIS
    Runs Criterion benchmarks with configurable modes and baseline management.

.DESCRIPTION
    This script provides a convenient interface for running Cargo benchmarks
    with environment-controlled mode switching and baseline comparison support.

    Modes:
    - quick (default): Fast iteration during development (50 samples, 3s measurement)
    - thorough: Comprehensive measurement for baselines (200 samples, 10s measurement)

.PARAMETER Mode
    Benchmark mode: 'quick' (default) or 'thorough'.
    Sets the BENCH_MODE environment variable.

.PARAMETER SaveBaseline
    Save benchmark results as a baseline for future comparison.
    Uses timestamp-based naming by default.

.PARAMETER BaselineName
    Custom name for the baseline. If not specified with -SaveBaseline,
    uses format: baseline-yyyy-MM-dd-HHmmss

.PARAMETER Compare
    Compare current results against a named baseline.
    Requires -BaselineName to specify which baseline to compare against.

.PARAMETER Crate
    Run benchmarks for a specific crate only.
    Example: -Crate classic-yaml-core

.PARAMETER Filter
    Filter benchmarks by name pattern.
    Example: -Filter "parse_yaml"

.PARAMETER List
    List available benchmarks without running them.

.EXAMPLE
    .\run_benchmarks.ps1
    # Runs all benchmarks in quick mode

.EXAMPLE
    .\run_benchmarks.ps1 -Mode thorough
    # Runs all benchmarks in thorough mode (more samples, longer measurement)

.EXAMPLE
    .\run_benchmarks.ps1 -SaveBaseline
    # Runs benchmarks and saves baseline with timestamp name

.EXAMPLE
    .\run_benchmarks.ps1 -SaveBaseline -BaselineName "pre-optimization"
    # Runs benchmarks and saves with custom baseline name

.EXAMPLE
    .\run_benchmarks.ps1 -Compare -BaselineName "pre-optimization"
    # Runs benchmarks and compares against the named baseline

.EXAMPLE
    .\run_benchmarks.ps1 -Mode thorough -SaveBaseline -Crate classic-yaml-core
    # Thorough benchmark of specific crate, saving baseline

.EXAMPLE
    .\run_benchmarks.ps1 -List
    # Lists available benchmarks without running them

.NOTES
    This script should be run from the project root directory.
    Benchmark results are stored in ClassicLib-rs/target/criterion/ (gitignored).
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
    [string]$Crate,

    [Parameter()]
    [string]$Filter,

    [Parameter()]
    [switch]$List
)

# Ensure we're in the project root or can find the rust directory
$rustDir = $null
$searchPaths = @(
    (Join-Path $PSScriptRoot "../../ClassicLib-rs"),
    (Join-Path (Get-Location) "ClassicLib-rs"),
    (Get-Location)
)

foreach ($path in $searchPaths) {
    $testPath = Resolve-Path $path -ErrorAction SilentlyContinue
    if ($testPath -and (Test-Path (Join-Path $testPath "Cargo.toml"))) {
        $rustDir = $testPath
        break
    }
}

if (-not $rustDir) {
    Write-Error "Could not find ClassicLib-rs/ directory with Cargo.toml. Run this script from the project root."
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CLASSIC Benchmark Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set BENCH_MODE environment variable
$env:BENCH_MODE = $Mode
Write-Host "[Config] Mode: $Mode" -ForegroundColor Yellow

if ($Mode -eq 'quick') {
    Write-Host "         Sample size: 50, Measurement time: 3s" -ForegroundColor DarkGray
} else {
    Write-Host "         Sample size: 200, Measurement time: 10s" -ForegroundColor DarkGray
}

# Build the cargo bench command
$benchArgs = @("bench")

# Handle baseline options
if ($SaveBaseline) {
    if (-not $BaselineName) {
        $BaselineName = "baseline-$(Get-Date -Format 'yyyy-MM-dd-HHmmss')"
    }
    $benchArgs += @("--", "--save-baseline", $BaselineName)
    Write-Host "[Config] Saving baseline: $BaselineName" -ForegroundColor Yellow
}
elseif ($Compare) {
    if (-not $BaselineName) {
        Write-Error "-Compare requires -BaselineName to specify which baseline to compare against."
        exit 1
    }
    $benchArgs += @("--", "--baseline", $BaselineName)
    Write-Host "[Config] Comparing against baseline: $BaselineName" -ForegroundColor Yellow
}

# Handle crate-specific benchmarks
if ($Crate) {
    # Insert -p before the -- separator
    $dashIndex = [Array]::IndexOf($benchArgs, "--")
    if ($dashIndex -ge 0) {
        $benchArgs = $benchArgs[0..($dashIndex-1)] + @("-p", $Crate) + $benchArgs[$dashIndex..($benchArgs.Length-1)]
    } else {
        $benchArgs += @("-p", $Crate)
    }
    Write-Host "[Config] Crate: $Crate" -ForegroundColor Yellow
}

# Handle filter
if ($Filter) {
    # Filter goes after -- separator
    if ($benchArgs -notcontains "--") {
        $benchArgs += "--"
    }
    $benchArgs += $Filter
    Write-Host "[Config] Filter: $Filter" -ForegroundColor Yellow
}

# Handle list mode
if ($List) {
    if ($benchArgs -notcontains "--") {
        $benchArgs += "--"
    }
    $benchArgs += "--list"
    Write-Host "[Config] Listing benchmarks only" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[Command] cargo $($benchArgs -join ' ')" -ForegroundColor DarkGray
Write-Host "[Directory] $rustDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# Run cargo bench
$startTime = Get-Date
Push-Location $rustDir
try {
    & cargo $benchArgs
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "[Done] Benchmarks completed successfully" -ForegroundColor Green
} else {
    Write-Host "[Error] Benchmarks failed with exit code $exitCode" -ForegroundColor Red
}

Write-Host "[Duration] $($duration.ToString('hh\:mm\:ss\.fff'))" -ForegroundColor DarkGray

if ($SaveBaseline) {
    Write-Host "[Baseline] Saved as: $BaselineName" -ForegroundColor Green
    Write-Host "[Location] $rustDir/target/criterion/$BaselineName" -ForegroundColor DarkGray
}

Write-Host ""

exit $exitCode
