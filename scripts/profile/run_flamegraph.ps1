<#
.SYNOPSIS
    Generates flamegraph SVG for Rust code performance profiling.

.DESCRIPTION
    This script provides a convenient interface for running cargo-flamegraph
    with configurable modes for quick iteration vs. thorough profiling.

    Modes:
    - quick (default): Fast iteration during development (99 Hz, 10s)
    - thorough: Comprehensive profiling for analysis (997 Hz, 60s)

    On Windows, cargo-flamegraph uses the blondie backend for ETW-based
    sampling. Administrator privileges may be required for some profiling
    scenarios.

.PARAMETER Mode
    Profiling mode: 'quick' (default) or 'thorough'.
    Controls sampling frequency and duration.

.PARAMETER Crate
    Specific crate to profile. If not specified, profiles the default binary.
    Example: -Crate classic-yaml-core

.PARAMETER Bench
    Profile a benchmark instead of the main binary.

.PARAMETER BenchFilter
    Filter benchmarks by name pattern. Only used with -Bench.
    Example: -BenchFilter "parse_yaml"

.PARAMETER Output
    Custom output path for the SVG file.
    Default: target/profiling/flamegraphs/flamegraph-{timestamp}.svg

.PARAMETER Open
    Open the generated SVG in the default browser after generation.

.PARAMETER Frequency
    Override the default sampling frequency (Hz).
    Default: 99 Hz (quick) or 997 Hz (thorough)

.PARAMETER Duration
    Override the default profiling duration in seconds.
    Default: 10s (quick) or 60s (thorough)

.EXAMPLE
    .\run_flamegraph.ps1
    # Generate flamegraph in quick mode for default binary

.EXAMPLE
    .\run_flamegraph.ps1 -Mode thorough
    # Generate flamegraph in thorough mode (more samples, longer duration)

.EXAMPLE
    .\run_flamegraph.ps1 -Bench -BenchFilter "parse"
    # Profile benchmarks matching "parse"

.EXAMPLE
    .\run_flamegraph.ps1 -Crate classic-yaml-core -Open
    # Profile specific crate and open result in browser

.EXAMPLE
    .\run_flamegraph.ps1 -Frequency 499 -Duration 30
    # Custom frequency and duration

.NOTES
    Requirements:
    - cargo-flamegraph: cargo install flamegraph
    - On Windows: Visual Studio with C++ tools (for blondie backend)
    - May require Administrator privileges for ETW tracing

    Output is stored in target/profiling/flamegraphs/ (gitignored).
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet('quick', 'thorough')]
    [string]$Mode = 'quick',

    [Parameter()]
    [string]$Crate,

    [Parameter()]
    [switch]$Bench,

    [Parameter()]
    [string]$BenchFilter,

    [Parameter()]
    [string]$Output,

    [Parameter()]
    [switch]$Open,

    [Parameter()]
    [int]$Frequency,

    [Parameter()]
    [int]$Duration
)

# Ensure we're in the project root or can find the rust directory
$rustDir = $null
$searchPaths = @(
    (Join-Path $PSScriptRoot "../../rust"),
    (Join-Path (Get-Location) "rust"),
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
    Write-Error "Could not find rust/ directory with Cargo.toml. Run this script from the project root."
    exit 1
}

# Check for cargo-flamegraph
$flamegraphInstalled = $null
try {
    $flamegraphInstalled = cargo flamegraph --help 2>$null
} catch {
    # Ignore errors
}

if (-not $flamegraphInstalled) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " cargo-flamegraph not installed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install with: cargo install flamegraph" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "On Windows, you may also need:" -ForegroundColor DarkGray
    Write-Host "  - Visual Studio with C++ tools" -ForegroundColor DarkGray
    Write-Host "  - Administrator privileges for ETW tracing" -ForegroundColor DarkGray
    Write-Host ""
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CLASSIC Flamegraph Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set mode-based defaults
if ($Mode -eq 'quick') {
    $defaultFrequency = 99
    $defaultDuration = 10
    Write-Host "[Config] Mode: quick" -ForegroundColor Yellow
    Write-Host "         Frequency: 99 Hz, Duration: 10s" -ForegroundColor DarkGray
} else {
    $defaultFrequency = 997
    $defaultDuration = 60
    Write-Host "[Config] Mode: thorough" -ForegroundColor Yellow
    Write-Host "         Frequency: 997 Hz, Duration: 60s" -ForegroundColor DarkGray
}

# Apply overrides
$actualFrequency = if ($Frequency) { $Frequency } else { $defaultFrequency }
$actualDuration = if ($Duration) { $Duration } else { $defaultDuration }

if ($Frequency -or $Duration) {
    Write-Host "[Config] Overrides applied:" -ForegroundColor Yellow
    if ($Frequency) { Write-Host "         Frequency: $actualFrequency Hz" -ForegroundColor DarkGray }
    if ($Duration) { Write-Host "         Duration: ${actualDuration}s" -ForegroundColor DarkGray }
}

# Create output directory
$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$outputDir = Join-Path $rustDir "target/profiling/flamegraphs"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    Write-Host "[Setup] Created output directory: $outputDir" -ForegroundColor DarkGray
}

# Determine output path
if (-not $Output) {
    $Output = Join-Path $outputDir "flamegraph-$timestamp.svg"
}

Write-Host "[Output] $Output" -ForegroundColor Yellow

# Build the cargo flamegraph command
$flameArgs = @("flamegraph")

# Add profile for debug symbols
$flameArgs += @("--profile", "release-with-debug")

# Add output path
$flameArgs += @("-o", $Output)

# Add frequency
$flameArgs += @("-F", $actualFrequency)

# Handle crate selection
if ($Crate) {
    $flameArgs += @("-p", $Crate)
    Write-Host "[Config] Crate: $Crate" -ForegroundColor Yellow
}

# Handle benchmark mode
if ($Bench) {
    $flameArgs += "--bench"
    Write-Host "[Config] Profiling benchmarks" -ForegroundColor Yellow

    if ($BenchFilter) {
        $flameArgs += @("--", $BenchFilter)
        Write-Host "[Config] Benchmark filter: $BenchFilter" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[Command] cargo $($flameArgs -join ' ')" -ForegroundColor DarkGray
Write-Host "[Directory] $rustDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# Run cargo flamegraph
$startTime = Get-Date
Push-Location $rustDir
try {
    & cargo $flameArgs
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
    Write-Host "[Done] Flamegraph generated successfully" -ForegroundColor Green
    Write-Host "[Output] $Output" -ForegroundColor Green

    if ($Open) {
        Write-Host "[Opening] Launching browser..." -ForegroundColor Yellow
        Start-Process $Output
    }
} else {
    Write-Host "[Error] Flamegraph generation failed with exit code $exitCode" -ForegroundColor Red

    if ($exitCode -eq 1) {
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "  - Administrator privileges may be required" -ForegroundColor DarkGray
        Write-Host "  - Visual Studio C++ tools may need installation" -ForegroundColor DarkGray
        Write-Host "  - Binary must be built with debug symbols" -ForegroundColor DarkGray
    }
}

Write-Host "[Duration] $($duration.ToString('hh\:mm\:ss\.fff'))" -ForegroundColor DarkGray
Write-Host ""

exit $exitCode
