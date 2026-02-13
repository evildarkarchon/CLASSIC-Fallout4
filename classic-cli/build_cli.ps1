<#
.SYNOPSIS
    Build the CLASSIC C++ CLI scanner.

.DESCRIPTION
    Builds the C++ CLI application using CMake + Ninja + Corrosion.
    Corrosion automatically builds the Rust static library (classic-cpp-bridge)
    as part of the CMake build process. Requires VS Dev Shell (auto-detected).

.PARAMETER Clean
    Remove build directory before building.

.EXAMPLE
    .\build_cli.ps1
    .\build_cli.ps1 -Clean
#>

[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Verify VCPKG_ROOT is set
if (-not $env:VCPKG_ROOT) {
    Write-Error "VCPKG_ROOT environment variable is not set. Install vcpkg and set VCPKG_ROOT."
    exit 1
}

# ── Ensure VS Dev Shell environment (needed for Ninja + MSVC) ─────
# Check if cl.exe is already in PATH (i.e., we're in a VS Dev Shell)
$clFound = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $clFound) {
    Write-Host "Initializing VS Dev Shell..." -ForegroundColor Yellow
    $vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -property installationPath 2>$null
    if (-not $vsPath) {
        # Fallback: try without vswhere
        $vsPath = "C:\Program Files\Microsoft Visual Studio\18\Community"
    }
    $devShell = Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1"
    if (Test-Path $devShell) {
        & $devShell -Arch amd64 -SkipAutomaticLocation | Out-Null
    } else {
        Write-Error "Could not find VS Dev Shell. Run this script from a Developer PowerShell."
        exit 1
    }
}

# ── Step 1: CMake configure ─────────────────────────────────────────
Write-Host "`n=== Configuring CMake (Ninja) ===" -ForegroundColor Cyan

$buildDir = Join-Path $ScriptDir "build"

if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

$cmakeArgs = @("--preset", "default")

Push-Location $ScriptDir
try {
    Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    # ── Step 2: CMake build ─────────────────────────────────────────
    Write-Host "`n=== Building C++ CLI (Corrosion handles Rust build) ===" -ForegroundColor Cyan

    # Corrosion builds the Rust crate with PROFILE release and compiles
    # the CXX bridge glue code, so a single cmake --build is all that's needed.
    $buildArgs = @("--build", "build")

    Write-Host "cmake $($buildArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake build failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    Write-Host "`n=== Build complete ===" -ForegroundColor Green

    $exePath = Join-Path $buildDir "classic-cli.exe"
    if (Test-Path $exePath) {
        Write-Host "Output: $exePath" -ForegroundColor Cyan
    }
} finally {
    Pop-Location
}
