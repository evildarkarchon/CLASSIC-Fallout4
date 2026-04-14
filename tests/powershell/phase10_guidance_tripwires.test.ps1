param()

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")

$ScriptTargets = @(
    Join-Path $RepoRoot "rebuild_rust.ps1"
    Join-Path $RepoRoot "rebuild_node.ps1"
    Join-Path $RepoRoot "classic-cli/build_cli.ps1"
    Join-Path $RepoRoot "classic-gui/build_gui.ps1"
    Join-Path $RepoRoot "classic-cli/test_cli.ps1"
)

$ForbiddenPhrases = @(
    "ClassicLib-rs/Cargo.toml"
    "--manifest-path ClassicLib-rs/Cargo.toml"
    "ClassicLib-rs/python-bindings/.venv"
    "ClassicLib-rs/node-bindings/classic-node"
    "working-directory: ClassicLib-rs"
)

function Assert-ParsesWithoutErrors {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$parseErrors
    )

    if ($parseErrors -and $parseErrors.Count -gt 0) {
        $messages = $parseErrors | ForEach-Object { $_.Message }
        throw "Script has parse errors: $Path :: $($messages -join '; ')"
    }
}

foreach ($scriptPath in $ScriptTargets) {
    $resolvedScriptPath = Resolve-Path -Path $scriptPath
    Assert-ParsesWithoutErrors -Path $resolvedScriptPath.Path

    $scriptText = Get-Content -Path $resolvedScriptPath.Path -Raw
    foreach ($phrase in $ForbiddenPhrases) {
        if ($scriptText.Contains($phrase)) {
            throw "Found forbidden stale-root guidance in $($resolvedScriptPath.Path): '$phrase'"
        }
    }
}

Write-Host "PASS: Phase 10 wrapper-script stale-root tripwires parsed and scanned."
