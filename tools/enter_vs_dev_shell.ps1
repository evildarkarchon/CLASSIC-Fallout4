<#
.SYNOPSIS
    Run a command or open an interactive PowerShell inside the Visual Studio Dev Shell.

.DESCRIPTION
    Initializes the Visual Studio Developer Shell environment in-process using
    Launch-VsDevShell.ps1. This is useful for Windows-local workflows that need
    the MSVC toolchain, such as `napi build`, CMake/Ninja builds, or other tasks
    that rely on `cl.exe` and the correct linker being first on PATH.

    If -Command is provided, the command runs after the Dev Shell is initialized.
    If -Interactive is provided, a nested `pwsh -NoExit` session is opened with
    the initialized environment and requested working directory.

.PARAMETER Command
    Optional command string to execute after the Dev Shell is initialized.

.PARAMETER WorkingDirectory
    Optional working directory for the command or interactive shell.

.PARAMETER Arch
    Target Visual Studio toolchain architecture.

.PARAMETER Interactive
    Open a nested interactive PowerShell session after initialization.

.EXAMPLE
    pwsh -ExecutionPolicy Bypass -File tools/enter_vs_dev_shell.ps1 -Interactive

.EXAMPLE
    pwsh -ExecutionPolicy Bypass -File tools/enter_vs_dev_shell.ps1 `
        -WorkingDirectory ClassicLib-rs/node-bindings/classic-node `
        -Command "bun run parity:gate:local"
#>

param(
    [string]$Command,
    [string]$WorkingDirectory = ".",
    [ValidateSet("amd64", "x86", "arm64")]
    [string]$Arch = "amd64",
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"

function Resolve-WorkingDirectory {
    param(
        [Parameter(Mandatory)]
        [string]$PathValue
    )

    try {
        return (Resolve-Path -Path $PathValue -ErrorAction Stop).Path
    }
    catch {
        throw "Working directory '$PathValue' does not exist."
    }
}

function Get-VsInstallPath {
    $vswherePath = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswherePath) {
        $detectedPath = & $vswherePath -latest -property installationPath 2>$null
        if ($detectedPath) {
            return $detectedPath.Trim()
        }
    }

    $fallbacks = @(
        "C:\Program Files\Microsoft Visual Studio\18\Community",
        "C:\Program Files\Microsoft Visual Studio\18\Professional",
        "C:\Program Files\Microsoft Visual Studio\18\Enterprise",
        "C:\Program Files\Microsoft Visual Studio\17\Community",
        "C:\Program Files\Microsoft Visual Studio\17\Professional",
        "C:\Program Files\Microsoft Visual Studio\17\Enterprise"
    )

    foreach ($candidate in $fallbacks) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Could not locate a Visual Studio installation via vswhere.exe or known fallback paths."
}

function Ensure-VsDevShell {
    param(
        [Parameter(Mandatory)]
        [string]$TargetArch
    )

    Write-Host "Initializing VS Dev Shell..." -ForegroundColor Yellow
    $vsInstallPath = Get-VsInstallPath
    $devShellPath = Join-Path $vsInstallPath "Common7\Tools\Launch-VsDevShell.ps1"

    if (-not (Test-Path $devShellPath)) {
        throw "Could not find VS Dev Shell launcher at '$devShellPath'."
    }

    & $devShellPath -Arch $TargetArch -SkipAutomaticLocation | Out-Null

    $clCommand = Get-Command cl.exe -ErrorAction SilentlyContinue
    $linkCommand = Get-Command link.exe -ErrorAction SilentlyContinue

    if (-not $clCommand) {
        throw "VS Dev Shell initialization completed, but cl.exe is still unavailable on PATH."
    }

    if (-not $linkCommand) {
        throw "VS Dev Shell initialization completed, but link.exe is still unavailable on PATH."
    }

    if ($linkCommand.Source -like "*\\Git\\usr\\bin\\link.exe") {
        throw "VS Dev Shell initialization did not move the MSVC linker ahead of Git's link.exe on PATH."
    }
}

$resolvedWorkingDirectory = Resolve-WorkingDirectory -PathValue $WorkingDirectory
Ensure-VsDevShell -TargetArch $Arch

if ($Command) {
    Write-Host "Running in VS Dev Shell: $Command" -ForegroundColor Cyan
    Push-Location $resolvedWorkingDirectory
    try {
        Invoke-Expression $Command
        if (-not $?) {
            exit 1
        }
        if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

if ($Interactive -or -not $Command) {
    $escapedWorkingDirectory = $resolvedWorkingDirectory.Replace("'", "''")
    $startupCommand = "Set-Location -LiteralPath '$escapedWorkingDirectory'"
    Write-Host "Launching interactive PowerShell in VS Dev Shell..." -ForegroundColor Cyan
    & pwsh -NoExit -Command $startupCommand
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
