<#
.SYNOPSIS
    Build the CLASSIC C++ CLI scanner.

.DESCRIPTION
    Builds the C++ CLI application using CMake + Ninja + Corrosion.
    Corrosion automatically builds the Rust static library (classic-cpp-bridge)
    as part of the CMake build process. Requires VS Dev Shell (auto-detected).

.PARAMETER Clean
    Remove build directory before building.

.PARAMETER Test
    Run CTest (Catch2 unit tests) and integration tests after building.

.PARAMETER Debug
    Build using the CMake debug preset (build-debug directory).

.PARAMETER Install
    Run cmake --install to create a deployable layout.

.PARAMETER Package
    Run CPack to produce a distributable ZIP archive.
    Implies -Install.

.EXAMPLE
    .\build_cli.ps1
    .\build_cli.ps1 -Clean
    .\build_cli.ps1 -Test
    .\build_cli.ps1 -Debug
    .\build_cli.ps1 -Debug -Install
    .\build_cli.ps1 -Clean -Test -Install
    .\build_cli.ps1 -Package
#>

param(
    [switch]$Clean,
    [switch]$Test,
    [switch]$Debug,
    [switch]$Install,
    [switch]$Package
)

$ErrorActionPreference = "Stop"

# -Package implies -Install
if ($Package) { $Install = $true }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-Tool([string]$ToolName) {
    return Get-Command $ToolName -ErrorAction SilentlyContinue
}

# Verify VCPKG_ROOT is set
if (-not $env:VCPKG_ROOT) {
    Write-Error "VCPKG_ROOT environment variable is not set. Install vcpkg and set VCPKG_ROOT."
    exit 1
}

# ── Ensure VS Dev Shell environment (needed for Ninja + MSVC) ─────
# Check if cl.exe is already in PATH (i.e., we're in a VS Dev Shell)
$clFound = Get-Tool "cl.exe"
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
    }
    else {
        Write-Error "Could not find VS Dev Shell. Run this script from a Developer PowerShell."
        exit 1
    }
}

# Validate required toolchain components before CMake configure.
$clFound = Get-Tool "cl.exe"
$ninjaFound = Get-Tool "ninja"
if (-not $clFound -or -not $ninjaFound) {
    if (-not $clFound) {
        Write-Host "Missing required tool: cl.exe" -ForegroundColor Red
    }
    if (-not $ninjaFound) {
        Write-Host "Missing required tool: ninja" -ForegroundColor Red
    }
    Write-Error "Build prerequisites are missing. Run from Developer PowerShell for Visual Studio and ensure Visual Studio C++ workload + Ninja/CMake components are installed."
    exit 1
}

# ── Step 1: Clean (optional) ─────────────────────────────────────
$buildPreset = if ($Debug) { "debug" } else { "default" }
$buildDirName = if ($Debug) { "build-debug" } else { "build" }
$buildDir = Join-Path $ScriptDir $buildDirName

if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

# ── Step 2: CMake configure ─────────────────────────────────────
Write-Host "`n=== Configuring CMake (Ninja) ===" -ForegroundColor Cyan

$cmakeArgs = @("--preset", $buildPreset)

Push-Location $ScriptDir
try {
    Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    # ── Step 3: CMake build ──────────────────────────────────────
    Write-Host "`n=== Building C++ CLI (Corrosion handles Rust build) ===" -ForegroundColor Cyan

    # Corrosion builds the Rust crate with PROFILE release and compiles
    # the CXX bridge glue code, so a single cmake --build is all that's needed.
    $buildArgs = @("--build", $buildDirName)

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

    # ── Step 4: Tests (optional) ─────────────────────────────────
    if ($Test) {
        # Catch2 unit tests via CTest
        Write-Host "`n=== Running Catch2 unit tests (CTest) ===" -ForegroundColor Cyan
        & ctest --test-dir $buildDirName --output-on-failure
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Unit tests failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Host "Unit tests passed." -ForegroundColor Green

        # Integration tests
        $integrationScript = Join-Path $ScriptDir "test_cli.ps1"
        if (Test-Path $integrationScript) {
            Write-Host "`n=== Running integration tests ===" -ForegroundColor Cyan
            & $integrationScript -BuildDir $buildDirName
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Integration tests failed with exit code $LASTEXITCODE"
                exit $LASTEXITCODE
            }
        }
    }

    # ── Step 5: Install (optional) ───────────────────────────────
    if ($Install) {
        $installDirName = if ($Debug) { "install-debug" } else { "install" }
        $installDir = Join-Path $ScriptDir $installDirName
        Write-Host "`n=== Installing to $installDir ===" -ForegroundColor Cyan
        & cmake --install $buildDirName --prefix $installDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Install failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Host "Installed to: $installDir" -ForegroundColor Green
    }

    # ── Step 6: Package (optional) ──────────────────────────────────
    if ($Package) {
        $cpackConfig = Join-Path $buildDir "CPackConfig.cmake"
        $packageDir = Join-Path $buildDir "packages"
        Write-Host "`n=== Packaging with CPack (ZIP) ===" -ForegroundColor Cyan
        & cpack --config $cpackConfig -B $packageDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CPack failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        $zipFile = Get-ChildItem -Path $packageDir -Filter "*.zip" |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($zipFile) {
            Write-Host "Package: $($zipFile.FullName)" -ForegroundColor Green
        }
    }
}
finally {
    Pop-Location
}
