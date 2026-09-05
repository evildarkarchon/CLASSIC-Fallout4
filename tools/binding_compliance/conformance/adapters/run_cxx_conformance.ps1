<#
.SYNOPSIS
    Runs one bounded native CXX semantic family conformance instance.

.DESCRIPTION
    Prepares a fresh input-only plan, invokes only the approved CLI build wrapper
    with the exact CTest selection, captures bounded diagnostics, and always runs
    instance-scoped receipt validation after the wrapper attempt.
#>

[CmdletBinding()]
param(
    [ValidateSet("msvc", "clang-cl")]
    [string]$Compiler = "msvc",
    [ValidateSet("crash-log-scan-run", "user-settings")]
    [string]$Family = "crash-log-scan-run",
    [string]$ArtifactRoot = "tools/binding_compliance/artifacts"
)

$ErrorActionPreference = "Stop"
$TimeoutMilliseconds = 15 * 60 * 1000
$OriginalDirectory = Get-Location
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

<#
.SYNOPSIS
    Returns a lowercase SHA-256 digest for one captured diagnostic file.
#>
function Get-FileSha256 {
    param([Parameter(Mandatory)][string]$Path)

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

<#
.SYNOPSIS
    Publishes one diagnostic JSON document without exposing partial bytes.
#>
function Write-AtomicJson {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][object]$Document
    )

    $temporaryPath = "$Path.tmp"
    try {
        $payload = $Document | ConvertTo-Json -Depth 12
        [System.IO.File]::WriteAllText($temporaryPath, "$payload`n", $Utf8NoBom)
        [System.IO.File]::Move($temporaryPath, $Path)
    }
    catch {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
        throw
    }
}

try {
    Set-Location -LiteralPath $RepoRoot

    $PreparationScript = Join-Path $RepoRoot "tools/binding_compliance/conformance/adapters/prepare_cxx_conformance.py"
    $PreparationOutput = @(& python $PreparationScript --repo-root $RepoRoot --compiler $Compiler --family $Family --artifact-root $ArtifactRoot)
    if ($LASTEXITCODE -ne 0) {
        throw "CXX conformance preparation failed: $($PreparationOutput -join [Environment]::NewLine)"
    }
    if ($PreparationOutput.Count -eq 0) {
        throw "CXX conformance preparation returned no invocation document."
    }
    $Prepared = $PreparationOutput[-1] | ConvertFrom-Json

    $ArtifactDir = [System.IO.Path]::GetFullPath([string]$Prepared.artifactDir)
    $RunPlanPath = [System.IO.Path]::GetFullPath([string]$Prepared.runPlanPath)
    $ReceiptPath = [System.IO.Path]::GetFullPath([string]$Prepared.receiptPath)
    $JunitPath = Join-Path $ArtifactDir "ctest.junit.xml"
    $AttemptPath = Join-Path $ArtifactDir "attempt.json"
    $StdoutPath = Join-Path $ArtifactDir "stdout.log"
    $StderrPath = Join-Path $ArtifactDir "stderr.log"

    $PwshPath = (Get-Command pwsh -ErrorAction Stop).Source
    $WrapperArguments = @(
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "classic-cli/build_cli.ps1",
        "-Test",
        "-CTestName",
        "classic-cxx-conformance",
        "-Compiler",
        $Compiler,
        "-CTestArgs",
        "--output-junit",
        $JunitPath
    )
    $RecordedCommand = @("pwsh") + $WrapperArguments

    $ExitCode = $null
    $TimedOut = $false
    $LaunchError = $null
    $StandardOutput = ""
    $StandardError = ""
    $FinalizationError = $null
    $ValidationExitCode = 1
    $Process = $null
    $ProcessStarted = $false
    $StdoutTask = $null
    $StderrTask = $null

    try {
        $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $StartInfo.FileName = $PwshPath
        $StartInfo.WorkingDirectory = $RepoRoot
        $StartInfo.UseShellExecute = $false
        $StartInfo.CreateNoWindow = $true
        $StartInfo.RedirectStandardOutput = $true
        $StartInfo.RedirectStandardError = $true
        foreach ($Argument in $WrapperArguments) {
            [void]$StartInfo.ArgumentList.Add($Argument)
        }
        $StartInfo.Environment["CLASSIC_CONFORMANCE_RUN_PLAN"] = $RunPlanPath
        $StartInfo.Environment["CLASSIC_CONFORMANCE_OUTPUT"] = $ReceiptPath

        $Process = [System.Diagnostics.Process]::new()
        $Process.StartInfo = $StartInfo
        try {
            if (-not $Process.Start()) {
                throw "The approved CLI wrapper process did not start."
            }
            $ProcessStarted = $true
            # Drain both streams asynchronously so a verbose native build cannot
            # fill one OS pipe and deadlock before the launcher's timeout.
            $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
            $StderrTask = $Process.StandardError.ReadToEndAsync()
            if (-not $Process.WaitForExit($TimeoutMilliseconds)) {
                $TimedOut = $true
                # Kill the complete owned tree before receipt validation; otherwise
                # a descendant could publish stale evidence after report finalization.
                $Process.Kill($true)
                $Process.WaitForExit()
            }
            if (-not $TimedOut) {
                $ExitCode = $Process.ExitCode
            }
        }
        catch {
            $LaunchError = $_.Exception.Message
            if ($ProcessStarted -and -not $Process.HasExited) {
                $Process.Kill($true)
                $Process.WaitForExit()
            }
        }
        finally {
            if ($StdoutTask) {
                $StandardOutput = $StdoutTask.GetAwaiter().GetResult()
            }
            if ($StderrTask) {
                $StandardError = $StderrTask.GetAwaiter().GetResult()
            }
            if ($Process) {
                $Process.Dispose()
            }
        }
    }
    finally {
        try {
            [System.IO.File]::WriteAllText($StdoutPath, $StandardOutput, $Utf8NoBom)
            [System.IO.File]::WriteAllText($StderrPath, $StandardError, $Utf8NoBom)
            $Attempt = [ordered]@{
                schemaVersion = 1
                participantId = "cxx"
                executionInstanceId = [string]$Prepared.executionInstanceId
                invocationId = [string]$Prepared.invocationId
                sourceIdentity = [string]$Prepared.sourceIdentity
                command = $RecordedCommand
                workingDirectory = $RepoRoot
                compiler = $Compiler
                exitCode = $ExitCode
                timedOut = $TimedOut
                launchError = $LaunchError
                receipt = [ordered]@{
                    path = $ReceiptPath
                    produced = Test-Path -LiteralPath $ReceiptPath -PathType Leaf
                }
                junit = [ordered]@{
                    path = $JunitPath
                    produced = Test-Path -LiteralPath $JunitPath -PathType Leaf
                }
                stdout = [ordered]@{
                    path = $StdoutPath
                    sha256 = Get-FileSha256 -Path $StdoutPath
                }
                stderr = [ordered]@{
                    path = $StderrPath
                    sha256 = Get-FileSha256 -Path $StderrPath
                }
            }
            Write-AtomicJson -Path $AttemptPath -Document $Attempt
        }
        catch {
            $FinalizationError = $_.Exception.Message
            Write-Error "CXX conformance attempt finalization failed: $FinalizationError" -ErrorAction Continue
        }
        finally {
            # Receipt validation is deliberately nested under the attempt finally:
            # success, failure, spawn error, timeout, and even diagnostic-write
            # trouble all reach the same current instance-scoped report path.
            & python tools/binding_compliance/check_compliance.py `
                --repo-root . `
                --profile conformance `
                --participant cxx `
                --execution-instance "windows-$Compiler" `
                --receipt $ReceiptPath `
                --junit $JunitPath `
                --attempt $AttemptPath `
                --output-dir $ArtifactDir
            $ValidationExitCode = $LASTEXITCODE
        }
    }

    Write-Host "CXX conformance artifacts: $ArtifactDir"
    if ($FinalizationError -or $LaunchError -or $TimedOut -or $ExitCode -ne 0 -or $ValidationExitCode -ne 0) {
        exit 1
    }
    exit 0
}
finally {
    Set-Location -LiteralPath $OriginalDirectory
}
