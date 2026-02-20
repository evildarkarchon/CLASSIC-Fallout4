<#
.SYNOPSIS
    Integration tests for the CLASSIC C++ CLI scanner.

.DESCRIPTION
    Runs automated tests against the built classic-cli.exe binary, verifying
    help/version output, crash log scanning, report generation, and error handling.
    Uses temp directory isolation per test with cleanup in finally blocks.

    Scan tests create an isolated workspace with a junction to "CLASSIC Data/"
    so the CLI can load YAML config without picking up stray crash logs from the
    real project's "Crash Logs/" directory.

.EXAMPLE
    .\test_cli.ps1
    .\test_cli.ps1 -BuildDir build-debug
    .\test_cli.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [string]$BuildDir = "build"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath = Join-Path $ScriptDir "$BuildDir\classic-cli.exe"
$TestDataDir = Join-Path $ScriptDir "test_data"
# Project root where "CLASSIC Data/" lives (needed for YAML config loading)
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$ClassicDataDir = Join-Path $ProjectRoot "CLASSIC Data"

# ── Preflight checks ─────────────────────────────────────────────

if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: classic-cli.exe not found at: $ExePath" -ForegroundColor Red
    Write-Host "Run build_cli.ps1 first." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $TestDataDir)) {
    Write-Host "ERROR: test_data directory not found at: $TestDataDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ClassicDataDir)) {
    Write-Host "ERROR: CLASSIC Data directory not found at: $ClassicDataDir" -ForegroundColor Red
    exit 1
}

$TestLogs = Get-ChildItem -Path $TestDataDir -Filter "crash-*.log"
if ($TestLogs.Count -eq 0) {
    Write-Host "ERROR: No test crash logs found in: $TestDataDir" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== CLASSIC CLI Integration Tests ===" -ForegroundColor Cyan
Write-Host "Executable:   $ExePath" -ForegroundColor DarkGray
Write-Host "Test data:    $TestDataDir ($($TestLogs.Count) logs)" -ForegroundColor DarkGray
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
    <#
    .SYNOPSIS
        Creates an isolated workspace directory with a junction to CLASSIC Data/
        and a stub CLASSIC Ignore.yaml.
        The scanner uses CWD to find "CLASSIC Data/" for YAML config, and also
        searches CWD's "Crash Logs/" for log files. By using a clean workspace
        as CWD, we ensure only our test logs (via --scan-path) are found.
        CLASSIC Ignore.yaml is normally created dynamically on first launch;
        the stub here satisfies the YAML loader's existence check.
    #>
    $ws = New-TestTempDir
    New-Item -ItemType Junction -Path (Join-Path $ws "CLASSIC Data") -Target $ClassicDataDir | Out-Null
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

Write-Host "Test 1: --help flag" -ForegroundColor Cyan
try {
    $r = Run-Cli -Arguments @("--help")

    if ($r.ExitCode -ne 0) {
        Test-Fail "help-exit-code" "Expected exit code 0, got $($r.ExitCode)"
    } else {
        Test-Pass "help-exit-code"
    }

    $helpChecks = @("--game", "--scan-path", "--vr")
    foreach ($token in $helpChecks) {
        if ($r.Output -match [regex]::Escape($token)) {
            Test-Pass "help-contains-$token"
        } else {
            Test-Fail "help-contains-$token" "Output does not contain '$token'"
        }
    }
} catch {
    Test-Fail "help-flag" "Exception: $_"
}

# ── Test 2: --version flag ────────────────────────────────────────

Write-Host "Test 2: --version flag" -ForegroundColor Cyan
try {
    $r = Run-Cli -Arguments @("--version")

    if ($r.ExitCode -ne 0) {
        Test-Fail "version-exit-code" "Expected exit code 0, got $($r.ExitCode)"
    } else {
        Test-Pass "version-exit-code"
    }

    if ($r.Output -match "CLASSIC CLI Scanner") {
        Test-Pass "version-contains-banner"
    } else {
        Test-Fail "version-contains-banner" "Output does not contain 'CLASSIC CLI Scanner'"
    }
} catch {
    Test-Fail "version-flag" "Exception: $_"
}

# ── Test 3: Single crash log scan ────────────────────────────────

Write-Host "Test 3: Single crash log scan" -ForegroundColor Cyan
$workspace = $null
$tmpDir = $null
try {
    $workspace = New-ScanWorkspace
    $tmpDir = New-TestTempDir
    $firstLog = $TestLogs[0]
    Copy-Item $firstLog.FullName -Destination $tmpDir

    $r = Run-Cli -Arguments @("--scan-path", $tmpDir) -WorkingDirectory $workspace

    if ($r.ExitCode -ne 0) {
        Test-Fail "single-scan-exit-code" "Expected exit code 0, got $($r.ExitCode). Stderr: $($r.Stderr)"
    } else {
        Test-Pass "single-scan-exit-code"
    }

    if ($r.Output -match "Found 1 crash log") {
        Test-Pass "single-scan-found-count"
    } else {
        Test-Fail "single-scan-found-count" "Output does not contain 'Found 1 crash log'"
    }

    $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
    if ($autoscans.Count -eq 1) {
        Test-Pass "single-scan-report-generated"
    } else {
        Test-Fail "single-scan-report-generated" "Expected 1 AUTOSCAN.md, found $($autoscans.Count)"
    }
} catch {
    Test-Fail "single-scan" "Exception: $_"
} finally {
    Remove-TestTempDir $tmpDir
    Remove-TestTempDir $workspace
}

# ── Test 4: Multi-log scan ───────────────────────────────────────

Write-Host "Test 4: Multi-log scan" -ForegroundColor Cyan
$workspace = $null
$tmpDir = $null
try {
    $workspace = New-ScanWorkspace
    $tmpDir = New-TestTempDir
    foreach ($log in $TestLogs) {
        Copy-Item $log.FullName -Destination $tmpDir
    }

    $r = Run-Cli -Arguments @("--scan-path", $tmpDir) -WorkingDirectory $workspace

    if ($r.ExitCode -ne 0) {
        Test-Fail "multi-scan-exit-code" "Expected exit code 0, got $($r.ExitCode). Stderr: $($r.Stderr)"
    } else {
        Test-Pass "multi-scan-exit-code"
    }

    $expectedCount = $TestLogs.Count
    if ($r.Output -match "Found $expectedCount crash logs") {
        Test-Pass "multi-scan-found-count"
    } else {
        Test-Fail "multi-scan-found-count" "Output does not contain 'Found $expectedCount crash logs'"
    }

    $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
    if ($autoscans.Count -eq $expectedCount) {
        Test-Pass "multi-scan-reports-generated"
    } else {
        Test-Fail "multi-scan-reports-generated" "Expected $expectedCount AUTOSCAN.md files, found $($autoscans.Count)"
    }
} catch {
    Test-Fail "multi-scan" "Exception: $_"
} finally {
    Remove-TestTempDir $tmpDir
    Remove-TestTempDir $workspace
}

# ── Test 5: --max-concurrent 1 (single-threaded) ─────────────────

Write-Host "Test 5: --max-concurrent 1" -ForegroundColor Cyan
$workspace = $null
$tmpDir = $null
try {
    $workspace = New-ScanWorkspace
    $tmpDir = New-TestTempDir
    $firstLog = $TestLogs[0]
    Copy-Item $firstLog.FullName -Destination $tmpDir

    $r = Run-Cli -Arguments @("--scan-path", $tmpDir, "--max-concurrent", "1") -WorkingDirectory $workspace

    if ($r.Output -match "1 worker thread[^s]") {
        Test-Pass "max-concurrent-singular"
    } elseif ($r.Output -match "1 worker thread\s*$") {
        Test-Pass "max-concurrent-singular"
    } else {
        Test-Fail "max-concurrent-singular" "Output does not contain '1 worker thread' (singular)"
    }

    $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
    if ($autoscans.Count -ge 1) {
        Test-Pass "max-concurrent-report-generated"
    } else {
        Test-Fail "max-concurrent-report-generated" "No AUTOSCAN.md generated"
    }
} catch {
    Test-Fail "max-concurrent" "Exception: $_"
} finally {
    Remove-TestTempDir $tmpDir
    Remove-TestTempDir $workspace
}

# ── Test 6: No crash logs found ──────────────────────────────────

Write-Host "Test 6: No crash logs found (empty dir)" -ForegroundColor Cyan
$workspace = $null
$tmpDir = $null
try {
    $workspace = New-ScanWorkspace
    $tmpDir = New-TestTempDir

    $r = Run-Cli -Arguments @("--scan-path", $tmpDir) -WorkingDirectory $workspace

    if ($r.ExitCode -ne 0) {
        Test-Fail "empty-dir-exit-code" "Expected exit code 0, got $($r.ExitCode)"
    } else {
        Test-Pass "empty-dir-exit-code"
    }

    if ($r.Output -match "No crash logs found") {
        Test-Pass "empty-dir-message"
    } else {
        Test-Fail "empty-dir-message" "Output does not contain 'No crash logs found'"
    }
} catch {
    Test-Fail "empty-dir" "Exception: $_"
} finally {
    Remove-TestTempDir $tmpDir
    Remove-TestTempDir $workspace
}

# ── Test 7: Invalid --game value ─────────────────────────────────

Write-Host "Test 7: Invalid --game value" -ForegroundColor Cyan
try {
    $r = Run-Cli -Arguments @("--game", "InvalidGame")

    # CLI11 IsMember validator rejects invalid values with a non-zero exit
    if ($r.ExitCode -ne 0) {
        Test-Pass "invalid-game-rejected"
    } else {
        Test-Fail "invalid-game-rejected" "Expected non-zero exit code for invalid game, got 0"
    }
} catch {
    Test-Fail "invalid-game" "Exception: $_"
}

# ── Test 8: AUTOSCAN report content validation ────────────────────

Write-Host "Test 8: AUTOSCAN report content validation" -ForegroundColor Cyan
$workspace = $null
$tmpDir = $null
try {
    $workspace = New-ScanWorkspace
    $tmpDir = New-TestTempDir
    $firstLog = $TestLogs[0]
    Copy-Item $firstLog.FullName -Destination $tmpDir

    $r = Run-Cli -Arguments @("--scan-path", $tmpDir) -WorkingDirectory $workspace

    $autoscans = Get-ChildItem -Path $tmpDir -Filter "*-AUTOSCAN.md" -ErrorAction SilentlyContinue
    if ($autoscans.Count -eq 0) {
        Test-Fail "report-content" "No AUTOSCAN.md generated to validate"
    } else {
        $content = Get-Content -Path $autoscans[0].FullName -Raw -Encoding UTF8

        $sections = @("AUTOSCAN REPORT", "Error Information", "End of Report")
        foreach ($section in $sections) {
            if ($content -match [regex]::Escape($section)) {
                Test-Pass "report-contains-$($section -replace ' ', '-')"
            } else {
                Test-Fail "report-contains-$($section -replace ' ', '-')" "Report does not contain '$section'"
            }
        }

        # Regression guard: Rust report lines already contain explicit newlines.
        # C++ join paths must not append extra separators that inflate blank lines.
        $spacingGuards = @(
            @{
                Name = "report-spacing-header"
                Pattern = "\*\*AUTOSCAN REPORT GENERATED BY[^\r\n]*\*\*\r?\n\r?\n\r?\n>"
                Reason = "Header has excessive blank lines before viewing notice"
            },
            @{
                Name = "report-spacing-error-information"
                Pattern = "### Error Information\r?\n\r?\n\r?\n\*\*Main Error:\*\*"
                Reason = "Error Information section has excessive blank lines before Main Error"
            },
            @{
                Name = "report-spacing-known-suspects"
                Pattern = "### Checking for Known Crash Messages, Errors and Suspects\r?\n\r?\n\r?\n\S"
                Reason = "Known Crash Messages/Suspects section has excessive blank lines after heading"
            },
            @{
                Name = "report-spacing-important-mods"
                Pattern = "### Checking for Important Mods\r?\n\r?\n\r?\n\S"
                Reason = "Important Mods section has excessive blank lines after heading"
            }
        )

        foreach ($guard in $spacingGuards) {
            if ($content -match $guard.Pattern) {
                Test-Fail $guard.Name $guard.Reason
            } else {
                Test-Pass $guard.Name
            }
        }
    }
} catch {
    Test-Fail "report-content" "Exception: $_"
} finally {
    Remove-TestTempDir $tmpDir
    Remove-TestTempDir $workspace
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
} else {
    Write-Host "  Failed: 0" -ForegroundColor Green
}

Write-Host ""
if ($script:Failed -gt 0) {
    Write-Host "RESULT: SOME TESTS FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "RESULT: ALL TESTS PASSED" -ForegroundColor Green
    exit 0
}
