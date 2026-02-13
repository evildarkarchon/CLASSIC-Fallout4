<#
.SYNOPSIS
    Captures combined Python+Rust stack traces using py-spy.

.DESCRIPTION
    This script provides a convenient interface for running py-spy to profile
    Python applications with Rust extensions, capturing combined stack traces
    that show both Python and native Rust function calls.

    Modes:
    - quick (default): Fast iteration during development (10s duration)
    - thorough: Comprehensive profiling for analysis (60s duration)

    The --native flag (enabled by default) captures native Rust frames,
    providing a complete view of the call stack through PyO3 bindings.

.PARAMETER Mode
    Profiling mode: 'quick' (default) or 'thorough'.
    Controls profiling duration.

.PARAMETER EntryPoint
    Python entry point to profile.
    Default: CLASSIC_Interface.py

.PARAMETER Native
    Include native Rust frames in the profile (default: enabled).
    This shows combined Python+Rust stack traces.

.PARAMETER NoNative
    Disable native frame capture (Python-only stacks).

.PARAMETER Output
    Custom output path for the profile.
    Default: target/profiling/pyspy/pyspy-{timestamp}.{ext}

.PARAMETER Format
    Output format: 'flamegraph' (default), 'speedscope', 'raw'.
    - flamegraph: Interactive SVG file
    - speedscope: JSON format for speedscope.app
    - raw: Text-based raw output

.PARAMETER Duration
    Override the default profiling duration in seconds.
    Default: 10s (quick) or 60s (thorough)

.PARAMETER Rate
    Sampling rate in Hz. Default: 100.

.PARAMETER SubProcesses
    Profile subprocesses as well.

.PARAMETER ProcessId
Attach to an existing process by PID instead of launching a new one.

.PARAMETER Open
    Open the generated output in the default application after profiling.

.PARAMETER Args
    Additional arguments to pass to the Python script.

.EXAMPLE
    .\run_pyspy.ps1
    # Profile CLASSIC_Interface.py in quick mode with native frames

.EXAMPLE
    .\run_pyspy.ps1 -Mode thorough
    # Profile for 60 seconds with thorough settings

.EXAMPLE
    .\run_pyspy.ps1 -EntryPoint CLASSIC_ScanLogs.py -Args "--help"
    # Profile CLI entry point with arguments

.EXAMPLE
    .\run_pyspy.ps1 -Format speedscope -Open
    # Generate speedscope-compatible output and open it

.EXAMPLE
    .\run_pyspy.ps1 -NoNative
    # Profile Python-only stacks (no Rust frames)

.EXAMPLE
.\run_pyspy.ps1 -ProcessId 12345 -Duration 30
# Attach to running process for 30 seconds

.NOTES
    Requirements:
    - py-spy: pip install py-spy (or cargo install py-spy)
    - Administrator/elevated privileges required on Windows
    - Python virtual environment should be active

    On Windows, py-spy requires Administrator privileges to attach to processes
    and read process memory for native frame capture.

    Output is stored in target/profiling/pyspy/ (gitignored).
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet('quick', 'thorough')]
    [string]$Mode = 'quick',

    [Parameter()]
    [string]$EntryPoint = 'CLASSIC_Interface.py',

    [Parameter()]
    [switch]$Native,

    [Parameter()]
    [switch]$NoNative,

    [Parameter()]
    [string]$Output,

    [Parameter()]
    [ValidateSet('flamegraph', 'speedscope', 'raw')]
    [string]$Format = 'flamegraph',

    [Parameter()]
    [int]$Duration,

    [Parameter()]
    [int]$Rate = 100,

    [Parameter()]
    [switch]$SubProcesses,

    [Parameter()]
    [int]$ProcessId,

    [Parameter()]
    [switch]$Open,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

# Find project root
$projectRoot = $null
$searchPaths = @(
    (Join-Path $PSScriptRoot "../.."),
    (Get-Location)
)

foreach ($path in $searchPaths) {
    $testPath = Resolve-Path $path -ErrorAction SilentlyContinue
    if ($testPath -and (Test-Path (Join-Path $testPath "CLASSIC_Interface.py"))) {
        $projectRoot = $testPath
        break
    }
}

if (-not $projectRoot) {
    Write-Error "Could not find project root (CLASSIC_Interface.py). Run this script from the project root."
    exit 1
}

# Check for py-spy
$pyspyPath = Get-Command py-spy -ErrorAction SilentlyContinue
if (-not $pyspyPath) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " py-spy not installed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install with one of:" -ForegroundColor Yellow
    Write-Host "  pip install py-spy" -ForegroundColor DarkGray
    Write-Host "  cargo install py-spy" -ForegroundColor DarkGray
    Write-Host "  uv tool install py-spy" -ForegroundColor DarkGray
    Write-Host ""
    exit 1
}

# Check for Administrator privileges on Windows
$isAdmin = $false
if ($PSVersionTable.Platform -ne 'Unix') {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CLASSIC py-spy Profiler" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not $isAdmin -and $PSVersionTable.Platform -ne 'Unix') {
    Write-Host "[Warning] Not running as Administrator" -ForegroundColor Yellow
    Write-Host "         py-spy may fail to capture native frames" -ForegroundColor DarkGray
    Write-Host "         Rerun from an elevated PowerShell prompt" -ForegroundColor DarkGray
    Write-Host ""
}

# Set mode-based defaults
if ($Mode -eq 'quick') {
    $defaultDuration = 10
    Write-Host "[Config] Mode: quick" -ForegroundColor Yellow
    Write-Host "         Duration: 10s, Rate: ${Rate} Hz" -ForegroundColor DarkGray
}
else {
    $defaultDuration = 60
    Write-Host "[Config] Mode: thorough" -ForegroundColor Yellow
    Write-Host "         Duration: 60s, Rate: ${Rate} Hz" -ForegroundColor DarkGray
}

# Apply duration override
$actualDuration = if ($Duration) { $Duration } else { $defaultDuration }

if ($Duration) {
    Write-Host "[Config] Duration override: ${actualDuration}s" -ForegroundColor Yellow
}

# Determine native mode
$useNative = $true
if ($NoNative) {
    $useNative = $false
    Write-Host "[Config] Native frames: disabled (Python-only)" -ForegroundColor Yellow
}
elseif ($Native) {
    # Explicit -Native flag (redundant but supported)
    $useNative = $true
    Write-Host "[Config] Native frames: enabled (combined Python+Rust)" -ForegroundColor Yellow
}
else {
    Write-Host "[Config] Native frames: enabled (default)" -ForegroundColor DarkGray
}

# Create output directory
$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$outputDir = Join-Path $projectRoot "ClassicLib-rs/target/profiling/pyspy"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    Write-Host "[Setup] Created output directory: $outputDir" -ForegroundColor DarkGray
}

# Determine output extension based on format
$extension = switch ($Format) {
    'flamegraph' { 'svg' }
    'speedscope' { 'json' }
    'raw' { 'txt' }
}

# Determine output path
if (-not $Output) {
    $nativeLabel = if ($useNative) { '-native' } else { '' }
    $Output = Join-Path $outputDir "pyspy-$timestamp$nativeLabel.$extension"
}

Write-Host "[Output] $Output" -ForegroundColor Yellow
Write-Host "[Format] $Format" -ForegroundColor DarkGray

# Build the py-spy command
$pyspyArgs = @("record")

# Output format
$pyspyArgs += @("-o", $Output)
$pyspyArgs += @("-f", $Format)

# Sampling rate
$pyspyArgs += @("-r", $Rate)

# Duration
$pyspyArgs += @("-d", $actualDuration)

# Native mode
if ($useNative) {
    $pyspyArgs += "--native"
}

# Subprocesses
if ($SubProcesses) {
    $pyspyArgs += "--subprocesses"
    Write-Host "[Config] Including subprocesses" -ForegroundColor DarkGray
}

# Target specification
if ($ProcessId) {
    $pyspyArgs += @("-p", $ProcessId)
    Write-Host "[Config] Attaching to PID: $ProcessId" -ForegroundColor Yellow
}
else {
    # Find Python executable
    $pythonPath = $null
    $venvPython = Join-Path $projectRoot ".venv/Scripts/python.exe"
    if (Test-Path $venvPython) {
        $pythonPath = $venvPython
    }
    else {
        $pythonPath = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    }

    if (-not $pythonPath) {
        Write-Error "Could not find Python executable. Ensure .venv is set up."
        exit 1
    }

    $entryPointPath = Join-Path $projectRoot $EntryPoint
    if (-not (Test-Path $entryPointPath)) {
        Write-Error "Entry point not found: $entryPointPath"
        exit 1
    }

    $pyspyArgs += "--"
    $pyspyArgs += $pythonPath
    $pyspyArgs += $entryPointPath

    if ($Args) {
        $pyspyArgs += $Args
    }

    Write-Host "[Config] Entry point: $EntryPoint" -ForegroundColor Yellow
    Write-Host "[Python] $pythonPath" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[Command] py-spy $($pyspyArgs -join ' ')" -ForegroundColor DarkGray
Write-Host "[Directory] $projectRoot" -ForegroundColor DarkGray
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

if (-not $ProcessId) {
    Write-Host "[Info] Profiling will start when the application launches" -ForegroundColor DarkGray
    Write-Host "[Info] Use Ctrl+C to stop early" -ForegroundColor DarkGray
    Write-Host ""
}

# Run py-spy
$startTime = Get-Date
Push-Location $projectRoot
try {
    & py-spy $pyspyArgs
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
    Write-Host "[Done] Profile captured successfully" -ForegroundColor Green
    Write-Host "[Output] $Output" -ForegroundColor Green

    # Show file size
    if (Test-Path $Output) {
        $fileSize = (Get-Item $Output).Length
        $fileSizeKB = [math]::Round($fileSize / 1024, 1)
        Write-Host "[Size] ${fileSizeKB} KB" -ForegroundColor DarkGray
    }

    if ($Open) {
        Write-Host "[Opening] Launching default application..." -ForegroundColor Yellow
        if ($Format -eq 'speedscope') {
            Write-Host "[Tip] Open https://speedscope.app and load the JSON file" -ForegroundColor DarkGray
        }
        Start-Process $Output
    }
}
else {
    Write-Host "[Error] py-spy failed with exit code $exitCode" -ForegroundColor Red

    if (-not $isAdmin -and $PSVersionTable.Platform -ne 'Unix') {
        Write-Host ""
        Write-Host "This error may be due to missing Administrator privileges." -ForegroundColor Yellow
        Write-Host "Try running PowerShell as Administrator." -ForegroundColor Yellow
    }
}

Write-Host "[Duration] $($duration.ToString('hh\:mm\:ss\.fff'))" -ForegroundColor DarkGray
Write-Host ""

exit $exitCode
