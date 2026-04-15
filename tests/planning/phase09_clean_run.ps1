[CmdletBinding(SupportsShouldProcess)]
param()

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$LegacyTarget = Join-Path $RepoRoot "ClassicLib-rs/target"
$LegacyTargetBackup = Join-Path $RepoRoot "ClassicLib-rs/target.phase9-backup"
$NodeBindingsRoot = Join-Path $RepoRoot "node-bindings/classic-node"
$ProofCargoTarget = Join-Path $RepoRoot "target.phase09-proof"

$CleanupTargets = @(
    (Join-Path $RepoRoot "target"),
    $ProofCargoTarget,
    (Join-Path $RepoRoot "python-bindings/.venv"),
    (Join-Path $RepoRoot "node-bindings/classic-node/node_modules"),
    (Join-Path $RepoRoot "node-bindings/classic-node/dist"),
    (Join-Path $RepoRoot "python-bindings/parity-artifacts"),
    (Join-Path $RepoRoot "node-bindings/classic-node/parity-artifacts"),
    (Join-Path $RepoRoot "cpp-bindings/classic-cpp-bridge/parity-artifacts")
)

$ProofSteps = @(
    @{ Command = "cargo locate-project --workspace --message-format plain"; WorkingDirectory = $RepoRoot },
    @{ Command = "cargo metadata --format-version 1 --no-deps"; WorkingDirectory = $RepoRoot },
    @{ Command = "uv venv python-bindings/.venv"; WorkingDirectory = $RepoRoot },
    @{ Command = "uv pip install --python python-bindings/.venv/Scripts/python.exe -r python-bindings/requirements-ci.txt"; WorkingDirectory = $RepoRoot },
    @{ Command = "python tools/python_api_parity/check_parity_gate.py --repo-root ."; WorkingDirectory = $RepoRoot },
    @{ Command = "python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings"; WorkingDirectory = $RepoRoot },
    # Prove the repo-root Python wrapper remains usable after clean-state bootstrap and wrapper replay.
    @{ Command = "pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -BuildOnly"; WorkingDirectory = $RepoRoot },
    @{ Command = "bun install"; WorkingDirectory = $NodeBindingsRoot },
    @{ Command = "bun run build"; WorkingDirectory = $NodeBindingsRoot },
    @{ Command = "bun run parity:gate"; WorkingDirectory = $NodeBindingsRoot },
    @{ Command = "bun run dts:freshness:check"; WorkingDirectory = $NodeBindingsRoot },
    @{ Command = "python tools/cxx_api_parity/check_parity_gate.py --repo-root ."; WorkingDirectory = $RepoRoot },
    @{ Command = "pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package"; WorkingDirectory = $RepoRoot },
    @{ Command = "python -m pytest tests/planning/test_phase09_validation.py -q"; WorkingDirectory = $RepoRoot }
)

$FilesystemRetryCount = 30
$FilesystemRetryDelaySeconds = 2

function Convert-ToRepoRelativePath {
    param([string]$Path)

    if ($Path.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $Path.Substring($RepoRoot.Length + 1).Replace('\\', '/')
    }

    return $Path.Replace('\\', '/')
}

function Get-LegacyGeneratedSnapshot {
    $legacyRoot = Join-Path $RepoRoot "ClassicLib-rs"
    if (-not (Test-Path $legacyRoot)) {
        return @()
    }

    $snapshot = New-Object System.Collections.Generic.List[string]
    $legacyTargetPath = Join-Path $legacyRoot "target"
    if (Test-Path $legacyTargetPath) {
        $snapshot.Add((Convert-ToRepoRelativePath $legacyTargetPath))
    }

    Get-ChildItem -Path $legacyRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('.venv', 'node_modules', 'dist', 'parity-artifacts') } |
        ForEach-Object { $snapshot.Add((Convert-ToRepoRelativePath $_.FullName)) }

    Get-ChildItem -Path $legacyRoot -Recurse -Force -File -Filter '*.node' -ErrorAction SilentlyContinue |
        ForEach-Object { $snapshot.Add((Convert-ToRepoRelativePath $_.FullName)) }

    return @($snapshot | Sort-Object -Unique)
}

function Remove-GeneratedPath {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    $relativePath = Convert-ToRepoRelativePath $Path
    if ($PSCmdlet.ShouldProcess($relativePath, "Remove generated output")) {
        Invoke-WithFilesystemRetry -Action "remove $relativePath" -ScriptBlock {
            Remove-Item -Path $Path -Recurse -Force
        }
    }
}

function Remove-GeneratedPathWithLockFallback {
    param([string]$Path)

    try {
        Remove-GeneratedPath -Path $Path
    }
    catch {
        $relativePath = Convert-ToRepoRelativePath $Path
        Write-Warning "Continuing clean proof with isolated CARGO_TARGET_DIR because '$relativePath' is locked by another process: $($_.Exception.Message)"
    }
}

function Invoke-WithFilesystemRetry {
    param(
        [string]$Action,
        [scriptblock]$ScriptBlock
    )

    $attempt = 0
    while ($true) {
        try {
            & $ScriptBlock
            return
        }
        catch {
            $attempt += 1
            if ($attempt -ge $FilesystemRetryCount) {
                throw
            }

            Write-Warning "Retrying filesystem action '$Action' after transient lock ($attempt/$FilesystemRetryCount): $($_.Exception.Message)"
            Start-Sleep -Seconds $FilesystemRetryDelaySeconds
        }
    }
}

function Remove-NodeAddonOutputs {
    if (-not (Test-Path $NodeBindingsRoot)) {
        return
    }

    Get-ChildItem -Path $NodeBindingsRoot -Recurse -Force -File -Filter '*.node' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $relativePath = Convert-ToRepoRelativePath $_.FullName
            if ($PSCmdlet.ShouldProcess($relativePath, "Remove built Node addon output")) {
                Remove-Item -Path $_.FullName -Force
            }
        }
}

function Invoke-RepoCommand {
    param(
        [string]$Command,
        [string]$WorkingDirectory = $RepoRoot
    )

    $workingLabel = if ($WorkingDirectory -eq $RepoRoot) {
        "."
    }
    else {
        Convert-ToRepoRelativePath $WorkingDirectory
    }
    $commandLabel = if ($workingLabel -eq ".") {
        $Command
    }
    else {
        "$Command (cwd: $workingLabel)"
    }

    if (-not $PSCmdlet.ShouldProcess($commandLabel, "Run Phase 9 proof command")) {
        return
    }

    Push-Location $WorkingDirectory
    try {
        Invoke-Expression $Command
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $Command"
        }
    }
    finally {
        Pop-Location
    }
}

if ((Test-Path $LegacyTargetBackup) -and -not (Test-Path $LegacyTarget)) {
    $relativeBackupTarget = Convert-ToRepoRelativePath $LegacyTargetBackup
    if ($PSCmdlet.ShouldProcess($relativeBackupTarget, "Restore stale pre-run legacy target backup")) {
        Invoke-WithFilesystemRetry -Action "restore stale $relativeBackupTarget" -ScriptBlock {
            Rename-Item -Path $LegacyTargetBackup -NewName ([System.IO.Path]::GetFileName($LegacyTarget))
        }
    }
}

if (Test-Path $LegacyTargetBackup) {
    throw "Refusing to overwrite existing backup target directory: $LegacyTargetBackup"
}

$RenamedLegacyTarget = $false
$PreProofLegacyState = @(Get-LegacyGeneratedSnapshot)

try {
    $OriginalCargoTargetDir = $env:CARGO_TARGET_DIR
    $OriginalCargoBuildJobs = $env:CARGO_BUILD_JOBS
    $env:CARGO_TARGET_DIR = $ProofCargoTarget
    $env:CARGO_BUILD_JOBS = "1"

    if (Test-Path $LegacyTarget) {
        $relativeLegacyTarget = Convert-ToRepoRelativePath $LegacyTarget
        $relativeBackupTarget = Convert-ToRepoRelativePath $LegacyTargetBackup
        if ($PSCmdlet.ShouldProcess($relativeLegacyTarget, "Quarantine to $relativeBackupTarget")) {
            Invoke-WithFilesystemRetry -Action "quarantine $relativeLegacyTarget" -ScriptBlock {
                Rename-Item -Path $LegacyTarget -NewName ([System.IO.Path]::GetFileName($LegacyTargetBackup))
            }
            $RenamedLegacyTarget = $true
        }
    }

    Remove-GeneratedPathWithLockFallback -Path (Join-Path $RepoRoot "target")
    foreach ($cleanupTarget in $CleanupTargets | Where-Object { $_ -ne (Join-Path $RepoRoot "target") }) {
        Remove-GeneratedPath -Path $cleanupTarget
    }

    Remove-NodeAddonOutputs

    foreach ($proofStep in $ProofSteps) {
        Invoke-RepoCommand -Command $proofStep.Command -WorkingDirectory $proofStep.WorkingDirectory
    }

    $PostProofLegacyState = @(Get-LegacyGeneratedSnapshot)
    $NewLegacyResidue = Compare-Object -ReferenceObject $PreProofLegacyState -DifferenceObject $PostProofLegacyState -PassThru |
        Where-Object { $_ -in $PostProofLegacyState }

    if ($NewLegacyResidue) {
        $paths = ($NewLegacyResidue | Sort-Object -Unique) -join ", "
        throw "Phase 9 proof recreated generated residue under ClassicLib-rs: $paths"
    }
}
finally {
    if (Test-Path $ProofCargoTarget) {
        Remove-GeneratedPathWithLockFallback -Path $ProofCargoTarget
    }

    if ($null -eq $OriginalCargoTargetDir) {
        Remove-Item Env:CARGO_TARGET_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:CARGO_TARGET_DIR = $OriginalCargoTargetDir
    }

    if ($null -eq $OriginalCargoBuildJobs) {
        Remove-Item Env:CARGO_BUILD_JOBS -ErrorAction SilentlyContinue
    }
    else {
        $env:CARGO_BUILD_JOBS = $OriginalCargoBuildJobs
    }

    if ($RenamedLegacyTarget -and (Test-Path $LegacyTargetBackup)) {
        $relativeBackupTarget = Convert-ToRepoRelativePath $LegacyTargetBackup
        if ($PSCmdlet.ShouldProcess($relativeBackupTarget, "Restore quarantined legacy target")) {
            Invoke-WithFilesystemRetry -Action "restore $relativeBackupTarget" -ScriptBlock {
                Rename-Item -Path $LegacyTargetBackup -NewName ([System.IO.Path]::GetFileName($LegacyTarget))
            }
        }
    }
}
