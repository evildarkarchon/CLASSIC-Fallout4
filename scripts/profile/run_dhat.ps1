<#
.SYNOPSIS
    Runs dhat heap profiling for Rust code.

.DESCRIPTION
    Builds and runs a Rust binary/test with dhat heap profiling enabled.
    Outputs heap allocation data to target/profiling/dhat/ directory.

    dhat is a heap profiling tool that tracks allocations and helps identify:
    - Memory allocation hot spots
    - Peak memory usage
    - Allocation patterns and frequencies

    After profiling, use the online dhat viewer to analyze results:
    https://nnethercote.github.io/dh_view/dh_view.html

.PARAMETER Crate
    The crate to profile (e.g., classic-yaml-core, classic-settings-core).

.PARAMETER Test
    Run tests instead of the binary.

.PARAMETER TestFilter
    Filter tests by name when using -Test (optional).

.PARAMETER Bench
    Run benchmarks with dhat feature enabled.

.PARAMETER Output
    Custom output directory for dhat files.
    Default: target/profiling/dhat/

.EXAMPLE
    .\run_dhat.ps1 -Crate classic-yaml-core -Test
    # Profile yaml-core tests with dhat

.EXAMPLE
    .\run_dhat.ps1 -Crate classic-settings-core -Test -TestFilter "test_load"
    # Profile specific test

.EXAMPLE
    .\run_dhat.ps1 -Crate classic-yaml-core -Bench
    # Profile benchmarks

.NOTES
    Requires the crate to have dhat-heap feature enabled:
    [features]
    dhat-heap = ["dep:dhat"]

    And a global allocator in test/bench code:
    #[cfg(feature = "dhat-heap")]
    #[global_allocator]
    static ALLOC: dhat::Alloc = dhat::Alloc;
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Crate to profile")]
    [string]$Crate,

    [Parameter(HelpMessage = "Run tests instead of binary")]
    [switch]$Test,

    [Parameter(HelpMessage = "Filter tests by name")]
    [string]$TestFilter,

    [Parameter(HelpMessage = "Run benchmarks")]
    [switch]$Bench,

    [Parameter(HelpMessage = "Custom output directory")]
    [string]$Output
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CLASSIC dhat Heap Profiler" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Resolve script and project paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Get-Item "$scriptDir/../..").FullName
$rustDir = Join-Path $projectRoot "ClassicLib-rs"

# Setup output directory
$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$outputDir = if ($Output) {
    if ([System.IO.Path]::IsPathRooted($Output)) { $Output }
    else { Join-Path $projectRoot $Output }
} else {
    Join-Path $projectRoot "target/profiling/dhat"
}

if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

Write-Host "[Config] Crate: $Crate" -ForegroundColor Yellow
Write-Host "[Config] Output dir: $outputDir" -ForegroundColor Yellow

# Set DHAT output file via environment variable
$dhatFile = Join-Path $outputDir "dhat-heap-$Crate-$timestamp.json"
$env:DHAT_OUTPUT_FILE = $dhatFile
Write-Host "[Config] DHAT output: $dhatFile" -ForegroundColor Yellow

# Build cargo command
$cargoArgs = @()

if ($Test) {
    $cargoArgs += @("test", "-p", $Crate, "--features", "dhat-heap", "--release")
    Write-Host "[Config] Running tests" -ForegroundColor Yellow

    if ($TestFilter) {
        $cargoArgs += @("--", $TestFilter)
        Write-Host "[Config] Test filter: $TestFilter" -ForegroundColor Yellow
    }
} elseif ($Bench) {
    $cargoArgs += @("bench", "-p", $Crate, "--features", "dhat-heap")
    Write-Host "[Config] Running benchmarks" -ForegroundColor Yellow
} else {
    $cargoArgs += @("run", "-p", $Crate, "--features", "dhat-heap", "--release")
    Write-Host "[Config] Running binary" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[Command] cargo $($cargoArgs -join ' ')" -ForegroundColor DarkGray
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# Run with dhat
$startTime = Get-Date
Push-Location $rustDir
try {
    & cargo @cargoArgs
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
$endTime = Get-Date
$elapsed = $endTime - $startTime

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "[Done] dhat profiling complete" -ForegroundColor Green
    Write-Host "[Duration] $($elapsed.ToString('hh\:mm\:ss\.fff'))" -ForegroundColor DarkGray

    # Check if dhat file was created
    if (Test-Path $dhatFile) {
        $fileSize = (Get-Item $dhatFile).Length
        $fileSizeFormatted = if ($fileSize -gt 1MB) {
            "{0:N2} MB" -f ($fileSize / 1MB)
        } elseif ($fileSize -gt 1KB) {
            "{0:N2} KB" -f ($fileSize / 1KB)
        } else {
            "$fileSize bytes"
        }
        Write-Host "[Output] $dhatFile ($fileSizeFormatted)" -ForegroundColor Green
        Write-Host ""
        Write-Host "View results at:" -ForegroundColor Cyan
        Write-Host "  https://nnethercote.github.io/dh_view/dh_view.html" -ForegroundColor White
        Write-Host ""
        Write-Host "Upload the JSON file to analyze heap allocations." -ForegroundColor DarkGray
    } else {
        Write-Host "[Warning] DHAT output file not found." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "The crate may not have dhat properly enabled. Ensure:" -ForegroundColor DarkGray
        Write-Host "  1. Cargo.toml has: [features] dhat-heap = [\"dep:dhat\"]" -ForegroundColor DarkGray
        Write-Host "  2. Test/main has the global allocator:" -ForegroundColor DarkGray
        Write-Host '     #[cfg(feature = "dhat-heap")]' -ForegroundColor DarkGray
        Write-Host '     #[global_allocator]' -ForegroundColor DarkGray
        Write-Host '     static ALLOC: dhat::Alloc = dhat::Alloc;' -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  3. Test code creates a dhat::Profiler:" -ForegroundColor DarkGray
        Write-Host '     let _profiler = dhat::Profiler::new_heap();' -ForegroundColor DarkGray
    }
} else {
    Write-Host "[Error] dhat profiling failed with exit code $exitCode" -ForegroundColor Red
    exit 1
}

Write-Host ""
