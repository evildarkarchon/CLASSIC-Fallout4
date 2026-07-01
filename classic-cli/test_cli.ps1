<#
.SYNOPSIS
    Integration tests for the CLASSIC C++ CLI scanner.

.DESCRIPTION
    Runs automated tests against the built classic-cli.exe binary, verifying
    help/version output, crash log scanning, report generation, and error handling.
    Uses temp directory isolation per test with cleanup in finally blocks.

    Scan tests create an isolated workspace with a controlled "CLASSIC Data/"
    layout so the CLI can load YAML config without picking up stray crash logs
    from the real project's "Crash Logs/" directory or the user's documents XSE
    folder.

.EXAMPLE
    .\test_cli.ps1
    .\test_cli.ps1 -BuildDir build-debug
    .\test_cli.ps1 -TestDataDir "D:\fixtures\classic-logs"
    .\test_cli.ps1 -MaxLogs 10
    .\test_cli.ps1 -TestName help,version
    .\test_cli.ps1 -TestName "help, version"
    .\test_cli.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [string]$BuildDir = "build",
    [string]$TestDataDir,
    [string[]]$TestName = @(),
    [ValidateRange(0, 500)]
    [int]$MaxLogs = 25
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath = Join-Path $ScriptDir "$BuildDir\classic-cli.exe"
# Project root where "CLASSIC Data/" lives (needed for YAML config loading)
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$ClassicDataDir = Join-Path $ProjectRoot "CLASSIC Data"
$LegacyTestDataDir = Join-Path $ScriptDir "test_data"
$SubmoduleTestDataDir = Join-Path $ProjectRoot "sample_logs\FO4"
$AvailableScenarioNames = @(
    "help",
    "version",
    "single-scan",
    "multi-scan",
    "max-concurrent",
    "empty-dir",
    "invalid-game",
    "report-content"
)
$WorkspaceScenarioNames = @("single-scan", "multi-scan", "max-concurrent", "empty-dir", "report-content")
$TestDataScenarioNames = @("single-scan", "multi-scan", "max-concurrent", "report-content")

<#
.SYNOPSIS
    Normalizes selected integration scenario names from arrays or comma-separated strings.
#>
function ConvertTo-TestNameList {
    param([string[]]$TestNames)

    $normalized = @()
    foreach ($testName in $TestNames) {
        if ($null -eq $testName) {
            continue
        }

        foreach ($candidate in ($testName -split ",")) {
            $trimmed = $candidate.Trim()
            if ($trimmed) {
                $normalized += $trimmed
            }
        }
    }

    return $normalized
}

$TestName = @(ConvertTo-TestNameList -TestNames $TestName)

if ($TestName.Count -gt 0) {
    $unknownScenarioNames = @($TestName | Where-Object { $_ -notin $AvailableScenarioNames } | Select-Object -Unique)
    if ($unknownScenarioNames.Count -gt 0) {
        Write-Host "ERROR: Unknown integration test name(s): $($unknownScenarioNames -join ', ')" -ForegroundColor Red
        Write-Host "Available integration test names: $($AvailableScenarioNames -join ', ')" -ForegroundColor Yellow
        exit 1
    }
}

$SelectedScenarioNames = if ($TestName.Count -gt 0) { $TestName } else { $AvailableScenarioNames }
$NeedsWorkspace = @($SelectedScenarioNames | Where-Object { $_ -in $WorkspaceScenarioNames }).Count -gt 0
$NeedsTestData = @($SelectedScenarioNames | Where-Object { $_ -in $TestDataScenarioNames }).Count -gt 0

# ── Preflight checks ─────────────────────────────────────────────

if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: classic-cli.exe not found at: $ExePath" -ForegroundColor Red
    Write-Host "Run build_cli.ps1 first." -ForegroundColor Yellow
    exit 1
}

if ($NeedsWorkspace -and -not (Test-Path $ClassicDataDir)) {
    Write-Host "ERROR: CLASSIC Data directory not found at: $ClassicDataDir" -ForegroundColor Red
    exit 1
}

function Should-RunScenario {
    param([string]$ScenarioName)

    return $TestName.Count -eq 0 -or $ScenarioName -in $TestName
}

function Resolve-TestData {
    param(
        [string]$ExplicitDir,
        [string]$LegacyDir,
        [string]$SubmoduleDir
    )

    $candidates = @()
    if ($ExplicitDir) {
        $candidates += @{ Label = "explicit -TestDataDir"; Path = $ExplicitDir }
    }
    $candidates += @{ Label = "legacy classic-cli/test_data"; Path = $LegacyDir }
    $candidates += @{ Label = "sample_logs submodule"; Path = $SubmoduleDir }

    $diagnostics = @()

    foreach ($candidate in $candidates) {
        $path = $candidate.Path
        if (-not (Test-Path $path)) {
            $diagnostics += "  - $($candidate.Label): missing ($path)"
            continue
        }

        $logs = Get-ChildItem -Path $path -Filter "crash-*.log" -File -ErrorAction SilentlyContinue |
        Sort-Object Name
        if ($logs.Count -eq 0) {
            $diagnostics += "  - $($candidate.Label): no crash-*.log files ($path)"
            continue
        }

        return @{
            Path  = (Resolve-Path $path).Path
            Label = $candidate.Label
            Logs  = $logs
        }
    }

    return @{
        Path        = $null
        Label       = $null
        Logs        = @()
        Diagnostics = $diagnostics
    }
}

$AllTestLogs = @()
$TestLogs = @()

if ($NeedsTestData) {
    $resolvedTestData = Resolve-TestData -ExplicitDir $TestDataDir -LegacyDir $LegacyTestDataDir -SubmoduleDir $SubmoduleTestDataDir
    if (-not $resolvedTestData.Path) {
        Write-Host "ERROR: Could not find integration test data." -ForegroundColor Red
        foreach ($line in $resolvedTestData.Diagnostics) {
            Write-Host $line -ForegroundColor Yellow
        }
        Write-Host "Tip: initialize submodules (git submodule update --init --recursive) or pass -TestDataDir." -ForegroundColor Yellow
        exit 1
    }

    $TestDataDir = $resolvedTestData.Path
    $AllTestLogs = $resolvedTestData.Logs
    $TestLogs = if ($MaxLogs -gt 0 -and $AllTestLogs.Count -gt $MaxLogs) {
        $AllTestLogs | Select-Object -First $MaxLogs
    }
    else {
        $AllTestLogs
    }
}

Write-Host "`n=== CLASSIC CLI Integration Tests ===" -ForegroundColor Cyan
Write-Host "Executable:   $ExePath" -ForegroundColor DarkGray
Write-Host "Scenarios:    $($SelectedScenarioNames -join ', ')" -ForegroundColor DarkGray
if ($NeedsTestData) {
    Write-Host "Test data:    $TestDataDir ($($AllTestLogs.Count) logs, source: $($resolvedTestData.Label))" -ForegroundColor DarkGray
}
else {
    Write-Host "Test data:    not required for selected scenarios" -ForegroundColor DarkGray
}
if ($NeedsTestData -and $MaxLogs -gt 0 -and $AllTestLogs.Count -gt $MaxLogs) {
    Write-Host "Log limit:    Using first $($TestLogs.Count) logs (sorted by filename) due to -MaxLogs $MaxLogs" -ForegroundColor DarkGray
}
Write-Host "Project root: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# ── Test infrastructure ───────────────────────────────────────────

$script:Passed = 0
$script:Failed = 0
$script:TestNames = @()

function New-TestTempDir {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) "classic-cli-test-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    return $tmp
}

function New-ScanWorkspace {
    param([System.IO.FileInfo[]]$XseLogs = @())

    <#
    .SYNOPSIS
        Creates an isolated workspace directory with controlled CLASSIC Data/
        Local.yaml and a stub CLASSIC Ignore.yaml.
        The scanner uses CWD to find "CLASSIC Data/" for YAML config, and also
        searches CWD's "Crash Logs/" for log files. By using a clean workspace
        as CWD, we ensure only our test logs (via --scan-path) are found.
        CLASSIC Data subdirectories are junctioned to the repo data, while
        Local.yaml points at a temp XSE fixture folder so --scan-path tests do
        not depend on ambient user documents state.
        CLASSIC Ignore.yaml is normally created dynamically on first launch;
        the stub here satisfies the YAML loader's existence check.
    #>
    $ws = New-TestTempDir
    $workspaceDataDir = Join-Path $ws "CLASSIC Data"
    New-Item -ItemType Directory -Path $workspaceDataDir -Force | Out-Null

    Get-ChildItem -LiteralPath $ClassicDataDir -Force |
    Where-Object { $_.Name -ne "CLASSIC Fallout4 Local.yaml" } |
    ForEach-Object {
        $targetPath = Join-Path $workspaceDataDir $_.Name
        if ($_.PSIsContainer) {
            New-Item -ItemType Junction -Path $targetPath -Target $_.FullName | Out-Null
        }
        else {
            Copy-Item -LiteralPath $_.FullName -Destination $targetPath -Force
        }
    }

    $xseFixtureDir = Join-Path $ws "Fixture XSE"
    New-Item -ItemType Directory -Path $xseFixtureDir -Force | Out-Null
    foreach ($xseLog in $XseLogs) {
        Copy-Item -LiteralPath $xseLog.FullName -Destination $xseFixtureDir -Force
    }

    $xseYamlPath = $xseFixtureDir -replace '\\', '/'
    @"
Game_Info:
  Docs_Folder_XSE: $xseYamlPath
"@ | Set-Content -Path (Join-Path $workspaceDataDir "CLASSIC Fallout4 Local.yaml") -Encoding UTF8

    # Create minimal CLASSIC Ignore.yaml stub (normally generated on first launch)
    @"
CLASSIC_Ignore_Fallout4:
  - Example Plugin.esp
CLASSIC_Ignore_SkyrimSE:
  - Example Plugin.esp
"@ | Set-Content -Path (Join-Path $ws "CLASSIC Ignore.yaml") -Encoding UTF8
    return $ws
}

function Remove-TestTempDir {
    param([string]$Path)
    if ($Path -and (Test-Path $Path)) {
        Remove-Item -Recurse -Force $Path -ErrorAction SilentlyContinue
    }
}

function Run-Cli {
    param(
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $ExePath
    $psi.Arguments = ($Arguments -join ' ')
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    if ($WorkingDirectory) {
        $psi.WorkingDirectory = $WorkingDirectory
    }

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()

    return @{
        ExitCode = $proc.ExitCode
        Stdout   = $stdout
        Stderr   = $stderr
        Output   = $stdout + $stderr
    }
}

function Test-Pass {
    param([string]$Name)
    $script:Passed++
    $script:TestNames += @{ Name = $Name; Result = "PASS" }
    Write-Host "  PASS  $Name" -ForegroundColor Green
}

function Test-Fail {
    param([string]$Name, [string]$Reason)
    $script:Failed++
    $script:TestNames += @{ Name = $Name; Result = "FAIL" }
    Write-Host "  FAIL  $Name" -ForegroundColor Red
    Write-Host "        Reason: $Reason" -ForegroundColor Yellow
}

# ── Test 1: --help flag ───────────────────────────────────────────

if (Should-RunScenario "help") {
    Write-Host "Test 1: --help flag" -ForegroundColor Cyan
    try {
        $r = Run-Cli -Arguments @("--help")

        if ($r.ExitCode -ne 0) {
            Test-Fail "help-exit-code" "Expected exit code 0, got $($r.ExitCode)"
        }
        else {
            Test-Pass "help-exit-code"
        }

        $helpChecks = @("--game", "--scan-path", "--game-version")
        foreach ($token in $helpChecks) {
            if ($r.Output -match [regex]::Escape($token)) {
                Test-Pass "help-contains-$token"
            }
            else {
                Test-Fail "help-contains-$token" "Output does not contain '$token'"
            }
        }
    }
    catch {
        Test-Fail "help-flag" "Exception: $_"
    }
}

# ── Test 2: --version flag ────────────────────────────────────────

if (Should-RunScenario "version") {
    Write-Host "Test 2: --version flag" -ForegroundColor Cyan
    try {
        $r = Run-Cli -Arguments @("--version")

        if ($r.ExitCode -ne 0) {
            Test-Fail "version-exit-code" "Expected exit code 0, got $($r.ExitCode)"
        }
        else {
            Test-Pass "version-exit-code"
        }

        if ($r.Output -match "CLASSIC CLI Scanner") {
            Test-Pass "version-contains-banner"
        }
        else {
            Test-Fail "version-contains-banner" "Output does not contain 'CLASSIC CLI Scanner'"
        }
    }
    catch {
        Test-Fail "version-flag" "Exception: $_"
    }
}

# ── Test 3: Single crash log scan ────────────────────────────────

if (Should-RunScenario "single-scan") {
    Write-Host "Test 3: Single crash log scan" -ForegroundColor Cyan
    $workspace = $null
    $tmpDir = $null
    try {
        $firstLog = $TestLogs[0]
        $workspace = New-ScanWorkspace -XseLogs @($firstLog)
        $tmpDir = New-TestTempDir
        Copy-Item $firstLog.FullName -Destination $tmpDir

        $r = Run-Cli -Arguments @("--scan-path", $tmpDir, "--game-version", "auto") -WorkingDirectory $workspace

        if ($r.ExitCode -ne 0) {
            Test-Fail "single-scan-exit-code" "Expected exit code 0, got $($r.ExitCode). Stderr: $($r.Stderr)"
        }
        else {
            Test-Pass "single-scan-exit-code"
        }

        $expectedCount = 2
        if ($r.Output -match "Found $expectedCount crash logs") {
            Test-Pass "single-scan-found-count"
        }
        else {
            Test-Fail "single-scan-found-count" "Output does not contain 'Found $expectedCount crash logs'"
        }

        $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
        if ($autoscans.Count -eq 1) {
            Test-Pass "single-scan-report-generated"
        }
        else {
            Test-Fail "single-scan-report-generated" "Expected 1 AUTOSCAN.md, found $($autoscans.Count)"
        }
    }
    catch {
        Test-Fail "single-scan" "Exception: $_"
    }
    finally {
        Remove-TestTempDir $tmpDir
        Remove-TestTempDir $workspace
    }
}

# ── Test 4: Multi-log scan ───────────────────────────────────────

if (Should-RunScenario "multi-scan") {
    Write-Host "Test 4: Multi-log scan" -ForegroundColor Cyan
    $workspace = $null
    $tmpDir = $null
    try {
        $workspace = New-ScanWorkspace -XseLogs @($TestLogs[0])
        $tmpDir = New-TestTempDir
        foreach ($log in $TestLogs) {
            Copy-Item $log.FullName -Destination $tmpDir
        }

        $r = Run-Cli -Arguments @("--scan-path", $tmpDir, "--game-version", "auto") -WorkingDirectory $workspace

        if ($r.ExitCode -ne 0) {
            Test-Fail "multi-scan-exit-code" "Expected exit code 0, got $($r.ExitCode). Stderr: $($r.Stderr)"
        }
        else {
            Test-Pass "multi-scan-exit-code"
        }

        $expectedFoundCount = $TestLogs.Count + 1
        if ($r.Output -match "Found $expectedFoundCount crash logs") {
            Test-Pass "multi-scan-found-count"
        }
        else {
            Test-Fail "multi-scan-found-count" "Output does not contain 'Found $expectedFoundCount crash logs'"
        }

        $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
        $expectedCustomReports = $TestLogs.Count
        if ($autoscans.Count -eq $expectedCustomReports) {
            Test-Pass "multi-scan-reports-generated"
        }
        else {
            Test-Fail "multi-scan-reports-generated" "Expected $expectedCustomReports AUTOSCAN.md files, found $($autoscans.Count)"
        }
    }
    catch {
        Test-Fail "multi-scan" "Exception: $_"
    }
    finally {
        Remove-TestTempDir $tmpDir
        Remove-TestTempDir $workspace
    }
}

# ── Test 5: --max-concurrent 1 (single concurrent scan) ───────────

if (Should-RunScenario "max-concurrent") {
    Write-Host "Test 5: --max-concurrent 1" -ForegroundColor Cyan
    $workspace = $null
    $tmpDir = $null
    try {
        $workspace = New-ScanWorkspace
        $tmpDir = New-TestTempDir
        $firstLog = $TestLogs[0]
        Copy-Item $firstLog.FullName -Destination $tmpDir

        $r = Run-Cli -Arguments @("--scan-path", $tmpDir, "--game-version", "auto", "--max-concurrent", "1") -WorkingDirectory $workspace

        if ($r.Output -match "\b1 concurrent scan\b") {
            Test-Pass "max-concurrent-singular"
        }
        else {
            Test-Fail "max-concurrent-singular" "Output does not contain '1 concurrent scan' (singular)"
        }

        $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
        if ($autoscans.Count -ge 1) {
            Test-Pass "max-concurrent-report-generated"
        }
        else {
            Test-Fail "max-concurrent-report-generated" "No AUTOSCAN.md generated"
        }
    }
    catch {
        Test-Fail "max-concurrent" "Exception: $_"
    }
    finally {
        Remove-TestTempDir $tmpDir
        Remove-TestTempDir $workspace
    }
}

# ── Test 6: No crash logs found ──────────────────────────────────

if (Should-RunScenario "empty-dir") {
    Write-Host "Test 6: No crash logs found (empty dir)" -ForegroundColor Cyan
    $workspace = $null
    $tmpDir = $null
    try {
        $workspace = New-ScanWorkspace
        $tmpDir = New-TestTempDir

        $r = Run-Cli -Arguments @("--scan-path", $tmpDir, "--game-version", "auto") -WorkingDirectory $workspace

        if ($r.ExitCode -ne 0) {
            Test-Fail "empty-dir-exit-code" "Expected exit code 0, got $($r.ExitCode)"
        }
        else {
            Test-Pass "empty-dir-exit-code"
        }

        if ($r.Output -match "No crash logs found") {
            Test-Pass "empty-dir-message"
        }
        else {
            Test-Fail "empty-dir-message" "Output does not contain 'No crash logs found'"
        }
    }
    catch {
        Test-Fail "empty-dir" "Exception: $_"
    }
    finally {
        Remove-TestTempDir $tmpDir
        Remove-TestTempDir $workspace
    }
}

# ── Test 7: Invalid --game value ─────────────────────────────────

if (Should-RunScenario "invalid-game") {
    Write-Host "Test 7: Invalid --game value" -ForegroundColor Cyan
    try {
        $r = Run-Cli -Arguments @("--game", "InvalidGame")

        # CLI11 IsMember validator rejects invalid values with a non-zero exit
        if ($r.ExitCode -ne 0) {
            Test-Pass "invalid-game-rejected"
        }
        else {
            Test-Fail "invalid-game-rejected" "Expected non-zero exit code for invalid game, got 0"
        }
    }
    catch {
        Test-Fail "invalid-game" "Exception: $_"
    }
}

# ── Test 8: AUTOSCAN report content validation ────────────────────

if (Should-RunScenario "report-content") {
    Write-Host "Test 8: AUTOSCAN report content validation" -ForegroundColor Cyan
    $workspace = $null
    $tmpDir = $null
    try {
        $workspace = New-ScanWorkspace
        $tmpDir = New-TestTempDir
        $firstLog = $TestLogs[0]
        Copy-Item $firstLog.FullName -Destination $tmpDir

        $r = Run-Cli -Arguments @("--scan-path", $tmpDir, "--game-version", "auto") -WorkingDirectory $workspace

        $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
        if ($autoscans.Count -eq 0) {
            Test-Fail "report-content" "No AUTOSCAN.md generated to validate"
        }
        else {
            $content = Get-Content -Path $autoscans[0].FullName -Raw -Encoding UTF8

            $sections = @("AUTOSCAN REPORT", "Error Information", "End of Report")
            foreach ($section in $sections) {
                if ($content -match [regex]::Escape($section)) {
                    Test-Pass "report-contains-$($section -replace ' ', '-')"
                }
                else {
                    Test-Fail "report-contains-$($section -replace ' ', '-')" "Report does not contain '$section'"
                }
            }

            # Regression guard: Rust report lines already contain explicit newlines.
            # C++ join paths must not append extra separators that inflate blank lines.
            $spacingGuards = @(
                @{
                    Name    = "report-spacing-header"
                    Pattern = "\*\*AUTOSCAN REPORT GENERATED BY[^\r\n]*\*\*\r?\n\r?\n\r?\n>"
                    Reason  = "Header has excessive blank lines before viewing notice"
                },
                @{
                    Name    = "report-spacing-error-information"
                    Pattern = "### Error Information\r?\n\r?\n\r?\n\*\*Main Error:\*\*"
                    Reason  = "Error Information section has excessive blank lines before Main Error"
                },
                @{
                    Name    = "report-spacing-known-suspects"
                    Pattern = "### Checking for Known Crash Messages, Errors and Suspects\r?\n\r?\n\r?\n\S"
                    Reason  = "Known Crash Messages/Suspects section has excessive blank lines after heading"
                },
                @{
                    Name    = "report-spacing-important-mods"
                    Pattern = "### Checking for Important Mods\r?\n\r?\n\r?\n\S"
                    Reason  = "Important Mods section has excessive blank lines after heading"
                }
            )

            foreach ($guard in $spacingGuards) {
                if ($content -match $guard.Pattern) {
                    Test-Fail $guard.Name $guard.Reason
                }
                else {
                    Test-Pass $guard.Name
                }
            }
        }
    }
    catch {
        Test-Fail "report-content" "Exception: $_"
    }
    finally {
        Remove-TestTempDir $tmpDir
        Remove-TestTempDir $workspace
    }
}

# ── Summary ───────────────────────────────────────────────────────

$total = $script:Passed + $script:Failed
Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "  Total:  $total" -ForegroundColor White
Write-Host "  Passed: $($script:Passed)" -ForegroundColor Green
if ($script:Failed -gt 0) {
    Write-Host "  Failed: $($script:Failed)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Failed tests:" -ForegroundColor Red
    foreach ($t in $script:TestNames) {
        if ($t.Result -eq "FAIL") {
            Write-Host "    - $($t.Name)" -ForegroundColor Red
        }
    }
}
else {
    Write-Host "  Failed: 0" -ForegroundColor Green
}

Write-Host ""
if ($script:Failed -gt 0) {
    Write-Host "RESULT: SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}
else {
    Write-Host "RESULT: ALL TESTS PASSED" -ForegroundColor Green
    exit 0
}
