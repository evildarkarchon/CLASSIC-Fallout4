<#
.SYNOPSIS
    Runs one bounded native GUI Crash Log Scan Run consumer receipt instance.

.DESCRIPTION
    Prepares a fresh obligations-only plan, invokes the approved GUI build
    wrapper with exact CTest selection, captures bounded diagnostics, and
    always runs instance-scoped receipt validation after the wrapper attempt.
#>

[CmdletBinding()]
param(
    [ValidateSet("msvc", "clang-cl")]
    [string]$Compiler = "msvc"
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

    $TemporaryPath = "$Path.tmp"
    try {
        $Payload = $Document | ConvertTo-Json -Depth 12
        [System.IO.File]::WriteAllText($TemporaryPath, "$Payload`n", $Utf8NoBom)
        [System.IO.File]::Move($TemporaryPath, $Path)
    }
    catch {
        if (Test-Path -LiteralPath $TemporaryPath) {
            Remove-Item -LiteralPath $TemporaryPath -Force
        }
        throw
    }
}

try {
    Set-Location -LiteralPath $RepoRoot

    $PreparationScript = Join-Path $RepoRoot "tools/binding_compliance/conformance/adapters/prepare_consumer_conformance.py"
    $PreparationOutput = @(
        & python $PreparationScript `
            --repo-root $RepoRoot `
            --participant gui `
            --execution-instance "windows-$Compiler"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "GUI consumer conformance preparation failed: $($PreparationOutput -join [Environment]::NewLine)"
    }
    if ($PreparationOutput.Count -eq 0) {
        throw "GUI consumer conformance preparation returned no invocation document."
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
    # PowerShell's native -File binding consumes only one argv item for an array parameter. Use an
    # encoded child command so CTest receives --output-junit and its path as two CTestArgs values.
    $ChildCommand = @'
& $env:CLASSIC_CONSUMER_CONFORMANCE_GUI_WRAPPER `
    -Test `
    -CTestName classic-gui-consumer-conformance `
    -Compiler $env:CLASSIC_CONSUMER_CONFORMANCE_COMPILER `
    -CTestArgs @('--output-junit', $env:CLASSIC_CONSUMER_CONFORMANCE_JUNIT)
exit $LASTEXITCODE
'@
    $EncodedChildCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($ChildCommand))
    $WrapperArguments = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        $EncodedChildCommand
    )
    $RecordedCommand = @(
        "pwsh",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "& classic-gui/build_gui.ps1 -Test -CTestName classic-gui-consumer-conformance -Compiler $Compiler -CTestArgs @('--output-junit', '$JunitPath')"
    )

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
        $StartInfo.Environment["CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN"] = $RunPlanPath
        $StartInfo.Environment["CLASSIC_CONSUMER_CONFORMANCE_OUTPUT"] = $ReceiptPath
        $StartInfo.Environment["CLASSIC_CONSUMER_CONFORMANCE_GUI_WRAPPER"] =
            (Join-Path $RepoRoot "classic-gui/build_gui.ps1")
        $StartInfo.Environment["CLASSIC_CONSUMER_CONFORMANCE_COMPILER"] = $Compiler
        $StartInfo.Environment["CLASSIC_CONSUMER_CONFORMANCE_JUNIT"] = $JunitPath

        $Process = [System.Diagnostics.Process]::new()
        $Process.StartInfo = $StartInfo
        try {
            if (-not $Process.Start()) {
                throw "The approved GUI wrapper process did not start."
            }
            $ProcessStarted = $true
            # Drain both pipes while the native build runs so neither can deadlock the timeout.
            $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
            $StderrTask = $Process.StandardError.ReadToEndAsync()
            if (-not $Process.WaitForExit($TimeoutMilliseconds)) {
                $TimedOut = $true
                # Kill the complete owned tree before validation so no late receipt can appear.
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
                participantId = "gui"
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
            Write-Error "GUI consumer attempt finalization failed: $FinalizationError" -ErrorAction Continue
        }
        finally {
            # Every launcher outcome reaches the same current instance-scoped validator.
            & python tools/binding_compliance/check_compliance.py `
                --repo-root . `
                --profile conformance `
                --participant gui `
                --execution-instance "windows-$Compiler" `
                --receipt $ReceiptPath `
                --junit $JunitPath `
                --attempt $AttemptPath `
                --output-dir $ArtifactDir
            $ValidationExitCode = $LASTEXITCODE
        }
    }

    Write-Host "GUI consumer conformance artifacts: $ArtifactDir"
    if ($FinalizationError -or $LaunchError -or $TimedOut -or $ExitCode -ne 0 -or $ValidationExitCode -ne 0) {
        exit 1
    }
    exit 0
}
finally {
    Set-Location -LiteralPath $OriginalDirectory
}
