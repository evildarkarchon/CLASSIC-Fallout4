<#
.SYNOPSIS
    Generates workspace-wide or per-crate Rust test coverage reports.

.DESCRIPTION
    Uses cargo-llvm-cov to run tests with LLVM instrumentation and produce
    HTML, JSON, and lcov coverage reports. Excludes generated code (Slint
    bindings, build artifacts) from metrics.

    Two-phase approach: runs tests once with --no-report, then generates
    all three report formats from the collected profiling data.

    PyO3 binding crates are excluded from the test run (they require the
    Python DLL at runtime) but their source is still included in reports
    if any coverage data is available.

.PARAMETER Package
    Optional. A specific crate name (e.g., classic-scanlog-core) to measure
    coverage for. Without this parameter, runs workspace-wide coverage.

.PARAMETER Clean
    Optional switch. If set, runs cargo llvm-cov clean before measurement
    to ensure fresh profiling data.

.EXAMPLE
    # Workspace-wide coverage
    ./coverage_report.ps1

    # Per-crate coverage
    ./coverage_report.ps1 -Package classic-scanlog-core

    # Clean run
    ./coverage_report.ps1 -Clean
#>

param(
    [string]$Package,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

# Exclusion regex for reports: excludes Slint generated code, build artifacts
$excludeRegex = "(target[/\\]|build[/\\]|\.slint)"

# PyO3 binding crates to exclude from test run (require Python DLL)
$pyO3Crates = @(
    "classic-shared-py",
    "classic-yaml-py",
    "classic-database-py",
    "classic-file-io-py",
    "classic-scanlog-py",
    "classic-config-py",
    "classic-scangame-py",
    "classic-registry-py",
    "classic-perf-py",
    "classic-settings-py",
    "classic-message-py",
    "classic-path-py",
    "classic-constants-py",
    "classic-version-py",
    "classic-resource-py",
    "classic-xse-py",
    "classic-web-py",
    "classic-update-py"
)

# Output paths
# Note: cargo llvm-cov report --html creates an html/ subdirectory inside --output-dir
$htmlDir = "target/llvm-cov"
$jsonPath = "target/llvm-cov/coverage.json"
$lcovPath = "target/llvm-cov/lcov.info"

# Ensure output directory exists
$null = New-Item -Path "target/llvm-cov" -ItemType Directory -Force

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CLASSIC Rust Coverage Report" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($Clean) {
    Write-Host "[1/5] Cleaning previous profiling data..." -ForegroundColor Yellow
    cargo llvm-cov clean --workspace
    Write-Host "  Done." -ForegroundColor Green
} else {
    Write-Host "[1/5] Skipping clean (use -Clean for fresh data)" -ForegroundColor DarkGray
}

# Phase 1: Run tests and collect profiling data
# Note: --ignore-filename-regex is a report-only flag, not used with --no-report
if ($Package) {
    Write-Host "[2/5] Running tests for package: $Package" -ForegroundColor Yellow
    Write-Host "  Collecting profiling data..." -ForegroundColor DarkGray

    $testArgs = @(
        "llvm-cov", "--no-report",
        "--package", $Package
    )

    # Enable gui-bridge feature for classic-shared-core (Pitfall 6)
    if ($Package -eq "classic-shared-core") {
        $testArgs += "--features"
        $testArgs += "gui-bridge"
    }

    $testArgs += "--ignore-run-fail"

    cargo @testArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Some tests may have failed for $Package, but coverage data was collected." -ForegroundColor Yellow
    }
} else {
    Write-Host "[2/5] Running workspace-wide tests..." -ForegroundColor Yellow
    Write-Host "  Collecting profiling data (this may take a few minutes)..." -ForegroundColor DarkGray
    Write-Host "  Excluding $($pyO3Crates.Count) PyO3 binding crates from test run." -ForegroundColor DarkGray

    # Build exclusion arguments for PyO3 crates
    $excludeArgs = @()
    foreach ($crate in $pyO3Crates) {
        $excludeArgs += "--exclude"
        $excludeArgs += $crate
    }

    # --ignore-run-fail: collect coverage data even if some tests fail
    # (e.g., flaky tests due to global state contamination)
    cargo llvm-cov --no-report `
        --workspace `
        --features gui-bridge `
        --ignore-run-fail `
        @excludeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Some tests may have failed, but coverage data was collected." -ForegroundColor Yellow
    }
}

Write-Host "  Tests complete. Generating reports..." -ForegroundColor Green
Write-Host ""

# Phase 2a: Generate HTML report
Write-Host "[3/5] Generating HTML report..." -ForegroundColor Yellow
cargo llvm-cov report --html `
    --output-dir $htmlDir `
    --ignore-filename-regex $excludeRegex
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: HTML report generation failed" -ForegroundColor Red
} else {
    Write-Host "  HTML: $htmlDir/html/index.html" -ForegroundColor Green
}

# Phase 2b: Generate JSON report (for per-crate analysis)
Write-Host "[4/5] Generating JSON report..." -ForegroundColor Yellow
cargo llvm-cov report --json `
    --output-path $jsonPath `
    --ignore-filename-regex $excludeRegex
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: JSON report generation failed" -ForegroundColor Red
} else {
    Write-Host "  JSON: $jsonPath" -ForegroundColor Green
}

# Phase 2c: Generate lcov report (for CI integration)
Write-Host "[5/5] Generating lcov report..." -ForegroundColor Yellow
cargo llvm-cov report --lcov `
    --output-path $lcovPath `
    --ignore-filename-regex $excludeRegex
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: lcov report generation failed" -ForegroundColor Red
} else {
    Write-Host "  lcov: $lcovPath" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Coverage Reports Generated" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output locations:" -ForegroundColor White
Write-Host "  HTML:  $htmlDir/html/index.html" -ForegroundColor White
Write-Host "  JSON:  $jsonPath" -ForegroundColor White
Write-Host "  lcov:  $lcovPath" -ForegroundColor White
Write-Host ""

# Extract and display overall coverage from JSON
if (Test-Path $jsonPath) {
    try {
        $json = Get-Content $jsonPath -Raw | ConvertFrom-Json
        $totals = $json.data[0].totals
        $linesCovered = $totals.lines.covered
        $linesTotal = $totals.lines.count
        if ($linesTotal -gt 0) {
            $pct = [math]::Round(($linesCovered / $linesTotal) * 100, 1)
            Write-Host "Overall line coverage: $linesCovered / $linesTotal ($pct%)" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "Could not parse coverage summary from JSON." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Run coverage_summary.ps1 for per-crate breakdown." -ForegroundColor DarkGray
