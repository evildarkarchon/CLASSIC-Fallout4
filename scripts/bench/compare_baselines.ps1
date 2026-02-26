<#
.SYNOPSIS
    Compare Criterion baseline vs current run per scenario.

.DESCRIPTION
    Produces per-scenario absolute and relative deltas from Criterion `estimates.json`
    files. By default this script first runs a candidate benchmark pass against
    the provided baseline using `run_benchmarks.ps1`, then reads:

    - `<scenario>/new/estimates.json` (candidate)
    - `<scenario>/<baseline>/estimates.json` (reference)

    for each discovered scenario under `ClassicLib-rs/target/criterion`.

.PARAMETER Baseline
    Baseline name to compare against (required).

.PARAMETER Mode
    quick (default) or thorough benchmark mode for candidate run.

.PARAMETER Suite
    Benchmark suite to run before comparison.

.PARAMETER WarningThreshold
    Regression percentage threshold for warning classification (default: 5).

.PARAMETER FailThreshold
    Regression percentage threshold for fail classification (default: 10).

.PARAMETER ExportJson
    Optional path to export comparison report JSON.

.PARAMETER ScenarioFilter
    Optional regex filter applied to scenario IDs.

.PARAMETER BenchFilter
    Optional benchmark filter passed to `run_benchmarks.ps1` when candidate
    execution is enabled.

.PARAMETER NoRun
    Skip candidate benchmark execution and compare existing artifacts only.

.PARAMETER FailOnRegression
    Return non-zero exit code if one or more scenarios classify as fail.

.EXAMPLE
    .\scripts\bench\compare_baselines.ps1 -Baseline "db-baseline-main"

.EXAMPLE
    .\scripts\bench\compare_baselines.ps1 -Baseline "db-baseline-main" -Mode thorough -Suite rust-db-baseline -ExportJson .\target\db-delta.json
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Baseline,

    [Parameter()]
    [ValidateSet('quick', 'thorough')]
    [string]$Mode = 'quick',

    [Parameter()]
    [ValidateSet('all', 'rust-db-baseline')]
    [string]$Suite = 'rust-db-baseline',

    [Parameter()]
    [double]$WarningThreshold = 5,

    [Parameter()]
    [double]$FailThreshold = 10,

    [Parameter()]
    [string]$ExportJson,

    [Parameter()]
    [string]$ScenarioFilter,

    [Parameter()]
    [string]$BenchFilter,

    [Parameter()]
    [switch]$NoRun,

    [Parameter()]
    [switch]$FailOnRegression
)

$ErrorActionPreference = 'Stop'

if ($WarningThreshold -lt 0 -or $FailThreshold -lt 0) {
    Write-Error 'Threshold values must be non-negative.'
    exit 1
}
if ($FailThreshold -lt $WarningThreshold) {
    Write-Error 'FailThreshold must be greater than or equal to WarningThreshold.'
    exit 1
}

function Get-ScenarioId {
    param(
        [string]$CriterionDir,
        [string]$NewEstimatesPath
    )

    $newDir = Split-Path $NewEstimatesPath -Parent
    $scenarioDir = Split-Path $newDir -Parent
    $relative = [System.IO.Path]::GetRelativePath($CriterionDir, $scenarioDir)
    return $relative -replace '\\', '/'
}

function Get-MeanNs {
    param($EstimateObject)
    return [double]$EstimateObject.mean.point_estimate
}

function Get-DeltaClassification {
    param(
        [double]$DeltaPercent,
        [double]$WarningThreshold,
        [double]$FailThreshold
    )

    if ($DeltaPercent -gt $FailThreshold) {
        return 'fail'
    }
    if ($DeltaPercent -gt $WarningThreshold) {
        return 'warning'
    }
    if ($DeltaPercent -lt - $WarningThreshold) {
        return 'improved'
    }
    return 'within_threshold'
}

function Format-Ns {
    param([double]$Value)
    if ($Value -lt 1000) { return ('{0:N2} ns' -f $Value) }
    if ($Value -lt 1000000) { return ('{0:N2} us' -f ($Value / 1000.0)) }
    if ($Value -lt 1000000000) { return ('{0:N2} ms' -f ($Value / 1000000.0)) }
    return ('{0:N2} s' -f ($Value / 1000000000.0))
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$rustDir = Join-Path $repoRoot "ClassicLib-rs"
$criterionDir = Join-Path $rustDir "target/criterion"
$runnerScript = Join-Path $PSScriptRoot "run_benchmarks.ps1"

if (-not $NoRun) {
    Write-Host "Running candidate benchmarks before comparison..." -ForegroundColor Cyan
    if ($BenchFilter) {
        & $runnerScript -Mode $Mode -Compare -BaselineName $Baseline -Suite $Suite -Filter $BenchFilter
    }
    else {
        & $runnerScript -Mode $Mode -Compare -BaselineName $Baseline -Suite $Suite
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Candidate benchmark run failed with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path $criterionDir)) {
    Write-Error "Criterion directory not found: $criterionDir"
    exit 1
}

$newEstimateFiles = Get-ChildItem -Path $criterionDir -Recurse -Filter estimates.json |
Where-Object { $_.FullName -like "*\new\estimates.json" }

if (-not $newEstimateFiles) {
    Write-Error "No candidate estimates found under $criterionDir"
    exit 1
}

$results = @()
foreach ($newFile in $newEstimateFiles) {
    $scenarioId = Get-ScenarioId -CriterionDir $criterionDir -NewEstimatesPath $newFile.FullName

    if ($ScenarioFilter -and ($scenarioId -notmatch $ScenarioFilter)) {
        continue
    }

    $scenarioDir = Split-Path (Split-Path $newFile.FullName -Parent) -Parent
    $baselineFile = Join-Path $scenarioDir "$Baseline/estimates.json"
    if (-not (Test-Path $baselineFile)) {
        continue
    }

    $currentEstimate = Get-Content -Path $newFile.FullName -Raw | ConvertFrom-Json
    $baselineEstimate = Get-Content -Path $baselineFile -Raw | ConvertFrom-Json

    $currentMean = Get-MeanNs -EstimateObject $currentEstimate
    $baselineMean = Get-MeanNs -EstimateObject $baselineEstimate
    if ($baselineMean -eq 0) {
        continue
    }

    $deltaNs = $currentMean - $baselineMean
    $deltaPercent = ($deltaNs / $baselineMean) * 100.0
    $classification = Get-DeltaClassification -DeltaPercent $deltaPercent -WarningThreshold $WarningThreshold -FailThreshold $FailThreshold

    $results += [PSCustomObject]@{
        scenario_id      = $scenarioId
        baseline_mean_ns = $baselineMean
        current_mean_ns  = $currentMean
        delta_ns         = $deltaNs
        delta_percent    = $deltaPercent
        classification   = $classification
    }
}

$results = $results | Sort-Object scenario_id
if (-not $results -or $results.Count -eq 0) {
    Write-Error "No comparable scenarios found for baseline '$Baseline'."
    exit 1
}

Write-Host ""
Write-Host "Benchmark Comparison: baseline='$Baseline' mode='$Mode' suite='$Suite'" -ForegroundColor Cyan
Write-Host "Thresholds: warning>${WarningThreshold}% fail>${FailThreshold}%" -ForegroundColor Yellow
Write-Host ("=" * 100) -ForegroundColor DarkGray

foreach ($row in $results) {
    $deltaSign = if ($row.delta_percent -ge 0) { "+" } else { "" }
    $deltaText = "{0}{1:N2}%" -f $deltaSign, $row.delta_percent

    $color = switch ($row.classification) {
        'fail' { 'Red' }
        'warning' { 'Yellow' }
        'improved' { 'Green' }
        default { 'Gray' }
    }

    Write-Host ("[{0}] {1}" -f $row.classification.ToUpper(), $row.scenario_id) -ForegroundColor $color
    Write-Host ("  baseline={0} current={1} delta={2} ({3})" -f (Format-Ns $row.baseline_mean_ns), (Format-Ns $row.current_mean_ns), (Format-Ns $row.delta_ns), $deltaText)
}

$failCount = ($results | Where-Object { $_.classification -eq 'fail' }).Count
$warnCount = ($results | Where-Object { $_.classification -eq 'warning' }).Count
$improvedCount = ($results | Where-Object { $_.classification -eq 'improved' }).Count
$stableCount = ($results | Where-Object { $_.classification -eq 'within_threshold' }).Count

Write-Host ("-" * 100) -ForegroundColor DarkGray
Write-Host "Summary: total=$($results.Count) fail=$failCount warning=$warnCount improved=$improvedCount within_threshold=$stableCount"

if ($ExportJson) {
    $report = [PSCustomObject]@{
        generated_at_utc  = (Get-Date).ToUniversalTime().ToString("o")
        baseline_name     = $Baseline
        candidate_name    = 'new'
        bench_mode        = $Mode
        suite             = $Suite
        bench_filter      = $BenchFilter
        warning_threshold = $WarningThreshold
        fail_threshold    = $FailThreshold
        scenarios         = $results
    }
    $report | ConvertTo-Json -Depth 10 | Set-Content -Path $ExportJson -Encoding UTF8
    Write-Host "Exported comparison JSON: $ExportJson" -ForegroundColor Green
}

if ($FailOnRegression -and $failCount -gt 0) {
    exit 2
}

exit 0
