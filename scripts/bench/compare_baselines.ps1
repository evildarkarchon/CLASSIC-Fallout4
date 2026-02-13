<#
.SYNOPSIS
    Compare benchmark results against a saved baseline.

.DESCRIPTION
    Runs Criterion benchmarks against a specified baseline and displays
    the percentage changes with color coding for regressions and improvements.

    Uses critcmp for detailed comparison if installed, otherwise parses
    Criterion's native comparison output.

.PARAMETER Baseline
    Name of the baseline to compare against (required).
    Example: baseline-2026-02-04-120000

.PARAMETER ExportJson
    Path to export comparison results as JSON.

.PARAMETER Threshold
    Percentage threshold for highlighting changes (default: 10).
    Changes greater than this are marked as regression/improvement.

.PARAMETER BenchName
    Optional filter for specific benchmark name pattern.

.PARAMETER Quick
    Use quick benchmark mode (50 samples instead of 200).

.EXAMPLE
    .\compare_baselines.ps1 -Baseline baseline-2026-02-04-120000

.EXAMPLE
    .\compare_baselines.ps1 -Baseline baseline-2026-02-04-120000 -ExportJson results.json

.EXAMPLE
    .\compare_baselines.ps1 -Baseline baseline-2026-02-04-120000 -Threshold 5 -Quick

.NOTES
    Requires:
    - Rust and Cargo installed
    - Criterion benchmark suite in ClassicLib-rs/ directory
    - Optional: critcmp (cargo install critcmp) for enhanced comparison
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Baseline name to compare against")]
    [string]$Baseline,

    [Parameter(Mandatory = $false, HelpMessage = "Export results to JSON file")]
    [string]$ExportJson,

    [Parameter(Mandatory = $false, HelpMessage = "Percentage threshold for highlighting")]
    [int]$Threshold = 10,

    [Parameter(Mandatory = $false, HelpMessage = "Filter benchmarks by name pattern")]
    [string]$BenchName,

    [Parameter(Mandatory = $false, HelpMessage = "Use quick benchmark mode")]
    [switch]$Quick
)

$ErrorActionPreference = "Stop"

# Colors for output
$ColorReset = "`e[0m"
$ColorRed = "`e[31m"
$ColorGreen = "`e[32m"
$ColorYellow = "`e[33m"
$ColorCyan = "`e[36m"
$ColorBold = "`e[1m"

function Write-ColorLine {
    param(
        [string]$Text,
        [string]$Color = $ColorReset
    )
    Write-Host "${Color}${Text}${ColorReset}"
}

function Test-CritcmpInstalled {
    try {
        $null = Get-Command critcmp -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

function Get-BaselinePath {
    param([string]$BaselineName)

    $criterionDir = Join-Path $PSScriptRoot "../../ClassicLib-rs/target/criterion"
    $baselinePath = Join-Path $criterionDir $BaselineName

    if (Test-Path $baselinePath) {
        return $baselinePath
    }

    return $null
}

function Parse-PercentageChange {
    param([string]$Text)

    # Match patterns like "+5.2%", "-3.1%", "0.0%"
    if ($Text -match '([+-]?\d+\.?\d*)%') {
        return [double]$Matches[1]
    }
    return $null
}

function Format-ChangeText {
    param(
        [double]$Change,
        [int]$Threshold
    )

    $absChange = [Math]::Abs($Change)
    $sign = if ($Change -ge 0) { "+" } else { "" }

    if ($Change -gt $Threshold) {
        # Regression (slower)
        return "${ColorRed}${sign}${Change:F1}% [REGRESSION]${ColorReset}"
    }
    elseif ($Change -lt - $Threshold) {
        # Improvement (faster)
        return "${ColorGreen}${sign}${Change:F1}% [IMPROVED]${ColorReset}"
    }
    else {
        # Within threshold
        return "${ColorYellow}${sign}${Change:F1}% (within threshold)${ColorReset}"
    }
}

function Run-CritcmpComparison {
    param(
        [string]$Baseline,
        [string]$BenchFilter,
        [int]$Threshold,
        [string]$ExportPath
    )

    Write-ColorLine "`nUsing critcmp for detailed comparison..." $ColorCyan

    $critcmpArgs = @($Baseline)

    if ($BenchFilter) {
        $critcmpArgs += "--filter"
        $critcmpArgs += $BenchFilter
    }

    Push-Location (Join-Path $PSScriptRoot "../../rust")
    try {
        $output = & critcmp @critcmpArgs 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            Write-ColorLine "critcmp failed with exit code $exitCode" $ColorRed
            Write-Host $output
            return @()
        }

        # Parse and colorize critcmp output
        $results = @()
        foreach ($line in $output -split "`n") {
            if ($line -match '^\s*(\S+)\s+(\d+\.?\d*\s*\w+)\s+(\d+\.?\d*\s*\w+)\s+([+-]?\d+\.?\d*)%') {
                $benchName = $Matches[1]
                $currentTime = $Matches[2]
                $baselineTime = $Matches[3]
                $change = [double]$Matches[4]

                $results += @{
                    Name          = $benchName
                    Current       = $currentTime
                    Baseline      = $baselineTime
                    ChangePercent = $change
                }

                $changeText = Format-ChangeText -Change $change -Threshold $Threshold
                Write-Host "  ${benchName}:"
                Write-Host "    Current:  $currentTime"
                Write-Host "    Baseline: $baselineTime"
                Write-Host "    Change:   $changeText"
                Write-Host ""
            }
            else {
                # Pass through header lines, etc.
                Write-Host $line
            }
        }

        return $results
    }
    finally {
        Pop-Location
    }
}

function Run-CriterionComparison {
    param(
        [string]$Baseline,
        [string]$BenchFilter,
        [int]$Threshold,
        [bool]$QuickMode
    )

    Write-ColorLine "`nRunning Criterion benchmarks with baseline comparison..." $ColorCyan
    Write-ColorLine "This may take a while depending on benchmark count and mode." $ColorYellow

    $env:BENCH_MODE = if ($QuickMode) { "quick" } else { "thorough" }

    $cargoArgs = @("bench")

    if ($BenchFilter) {
        $cargoArgs += "--bench"
        $cargoArgs += "performance_benchmarks"
        $cargoArgs += "--"
        $cargoArgs += $BenchFilter
    }

    $cargoArgs += "--"
    $cargoArgs += "--baseline"
    $cargoArgs += $Baseline

    Push-Location (Join-Path $PSScriptRoot "../../rust")
    try {
        Write-Host "Running: cargo $($cargoArgs -join ' ')"
        Write-Host ""

        $output = & cargo @cargoArgs 2>&1 | Out-String
        $exitCode = $LASTEXITCODE

        Write-Host $output

        if ($exitCode -ne 0) {
            Write-ColorLine "`nBenchmark run failed with exit code $exitCode" $ColorRed
            return @()
        }

        # Parse Criterion output for comparison results
        $results = @()
        $currentBench = $null

        foreach ($line in $output -split "`n") {
            # Match benchmark name
            if ($line -match '^Benchmarking\s+(.+)$') {
                $currentBench = $Matches[1].Trim()
            }
            # Match comparison line like "Performance has regressed."
            # or "Performance has improved." or "No change in performance"
            elseif ($line -match 'change:\s*\[([+-]?\d+\.?\d*)%\s+([+-]?\d+\.?\d*)%\]') {
                $lowChange = [double]$Matches[1]
                $highChange = [double]$Matches[2]
                $avgChange = ($lowChange + $highChange) / 2

                if ($currentBench) {
                    $results += @{
                        Name          = $currentBench
                        ChangePercent = $avgChange
                        ChangeLow     = $lowChange
                        ChangeHigh    = $highChange
                    }
                }
            }
        }

        return $results
    }
    finally {
        Pop-Location
        $env:BENCH_MODE = $null
    }
}

function Export-ResultsToJson {
    param(
        [array]$Results,
        [string]$Path,
        [string]$Baseline,
        [int]$Threshold
    )

    $export = @{
        timestamp  = (Get-Date -Format "o")
        baseline   = $Baseline
        threshold  = $Threshold
        benchmarks = $Results
        summary    = @{
            total        = $Results.Count
            regressions  = ($Results | Where-Object { $_.ChangePercent -gt $Threshold }).Count
            improvements = ($Results | Where-Object { $_.ChangePercent -lt - $Threshold }).Count
            unchanged    = ($Results | Where-Object { [Math]::Abs($_.ChangePercent) -le $Threshold }).Count
        }
    }

    $export | ConvertTo-Json -Depth 10 | Set-Content -Path $Path -Encoding UTF8
    Write-ColorLine "`nResults exported to: $Path" $ColorGreen
}

# Main execution
Write-ColorLine "Benchmark Comparison: current vs $Baseline" $ColorBold
Write-ColorLine ("=" * 60) $ColorCyan

# Verify baseline exists
$baselinePath = Get-BaselinePath -BaselineName $Baseline
if (-not $baselinePath) {
    Write-ColorLine "Error: Baseline not found: $Baseline" $ColorRed
    Write-Host ""
    Write-Host "Available baselines:"

    $criterionDir = Join-Path $PSScriptRoot "../../ClassicLib-rs/target/criterion"
    if (Test-Path $criterionDir) {
        Get-ChildItem $criterionDir -Directory | Where-Object { $_.Name -match '^baseline-' } | ForEach-Object {
            Write-Host "  $($_.Name)"
        }
    }
    else {
        Write-Host "  (no criterion directory found)"
    }

    exit 1
}

Write-ColorLine "Baseline found: $baselinePath" $ColorGreen
Write-ColorLine "Threshold: ${Threshold}% for regression/improvement marking" $ColorYellow
Write-Host ""

$results = @()

# Use critcmp if available, otherwise fall back to Criterion's native comparison
if (Test-CritcmpInstalled) {
    $results = Run-CritcmpComparison -Baseline $Baseline -BenchFilter $BenchName -Threshold $Threshold -ExportPath $ExportJson
}
else {
    Write-ColorLine "Note: critcmp not installed. Using Criterion's native comparison." $ColorYellow
    Write-ColorLine "For enhanced comparison, install: cargo install critcmp" $ColorYellow
    Write-Host ""

    $results = Run-CriterionComparison -Baseline $Baseline -BenchFilter $BenchName -Threshold $Threshold -QuickMode $Quick
}

# Summary
if ($results.Count -gt 0) {
    Write-Host ""
    Write-ColorLine ("=" * 60) $ColorCyan
    Write-ColorLine "Summary" $ColorBold

    $regressions = $results | Where-Object { $_.ChangePercent -gt $Threshold }
    $improvements = $results | Where-Object { $_.ChangePercent -lt - $Threshold }
    $unchanged = $results | Where-Object { [Math]::Abs($_.ChangePercent) -le $Threshold }

    Write-Host "  Total benchmarks: $($results.Count)"

    if ($regressions.Count -gt 0) {
        Write-ColorLine "  Regressions:      $($regressions.Count)" $ColorRed
    }
    else {
        Write-Host "  Regressions:      0"
    }

    if ($improvements.Count -gt 0) {
        Write-ColorLine "  Improvements:     $($improvements.Count)" $ColorGreen
    }
    else {
        Write-Host "  Improvements:     0"
    }

    Write-Host "  Unchanged:        $($unchanged.Count)"

    # Export to JSON if requested
    if ($ExportJson) {
        Export-ResultsToJson -Results $results -Path $ExportJson -Baseline $Baseline -Threshold $Threshold
    }
}
else {
    Write-ColorLine "`nNo benchmark comparison results available." $ColorYellow
    Write-Host "Make sure benchmarks have been run with the specified baseline."
}
