$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$LegacyTarget = Join-Path $RepoRoot "ClassicLib-rs/target"
$RenamedLegacyTarget = "$LegacyTarget.phase6-backup"

if (Test-Path $RenamedLegacyTarget) {
    throw "Refusing to overwrite existing backup target directory: $RenamedLegacyTarget"
}

$Commands = @(
    "cargo locate-project --workspace",
    "cargo metadata --format-version 1 --no-deps",
    "cargo fmt --all -- --check",
    "cargo clippy --workspace --all-targets --all-features -- -D warnings",
    "cargo test --workspace --release -- --nocapture",
    "cargo build -p classic-scanlog-core",
    "python -m pytest tests/planning/test_phase06_validation.py -q"
)

$Renamed = $false

try {
    if (Test-Path $LegacyTarget) {
        Rename-Item -Path $LegacyTarget -NewName ([System.IO.Path]::GetFileName($RenamedLegacyTarget))
        $Renamed = $true
    }

    foreach ($Command in $Commands) {
        Push-Location $RepoRoot
        try {
            Invoke-Expression $Command
            if ($LASTEXITCODE -ne 0) {
                throw "Command failed with exit code $LASTEXITCODE: $Command"
            }
        }
        finally {
            Pop-Location
        }
    }
}
finally {
    if ($Renamed -and (Test-Path $RenamedLegacyTarget)) {
        Rename-Item -Path $RenamedLegacyTarget -NewName ([System.IO.Path]::GetFileName($LegacyTarget))
    }
}
