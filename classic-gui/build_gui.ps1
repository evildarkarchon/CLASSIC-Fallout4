<#
.SYNOPSIS
    Build the CLASSIC C++ Qt 6 GUI application.

.DESCRIPTION
    Builds the Qt 6 GUI using CMake + Ninja + Corrosion.
    Corrosion automatically builds the Rust static library (classic-cpp-bridge)
    as part of the CMake build process. Requires VS Dev Shell (auto-detected).

    Qt 6 must be installed and its path configured in CMakePresets.json
    (default: C:\Qt\6.10.2\msvc2022_64) or via CMAKE_PREFIX_PATH.

.PARAMETER Clean
    Remove build directory before building.

.PARAMETER Test
    Run CTest after building (if tests are available).

.PARAMETER Debug
    Build using a debug preset (build-debug directory).

.PARAMETER Install
    Run cmake --install to create a deployable layout with windeployqt.

.PARAMETER Package
    Run CPack to produce a distributable ZIP archive.
    Implies -Install (windeployqt must run first so Qt DLLs are included).

.PARAMETER Preset
    CMake preset name. Default: "default".

.EXAMPLE
    .\build_gui.ps1
    .\build_gui.ps1 -Clean
    .\build_gui.ps1 -Test
    .\build_gui.ps1 -Debug
    .\build_gui.ps1 -Debug -Install
    .\build_gui.ps1 -Install
    .\build_gui.ps1 -Package
    .\build_gui.ps1 -Clean -Package
#>

param(
    [switch]$Clean,
    [switch]$Test,
    [switch]$Debug,
    [switch]$Install,
    [switch]$Package,
    [string]$Preset = "default",
    [int]$TestTimeoutSec = 600
)

$ErrorActionPreference = "Stop"

# -Package implies -Install (windeployqt must populate the install dir first)
if ($Package) { $Install = $true }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$effectivePreset = $Preset

if ($Debug) {
    switch ($Preset) {
        "default" { $effectivePreset = "debug" }
        "ci" { $effectivePreset = "ci-debug" }
        "debug" { $effectivePreset = "debug" }
        "ci-debug" { $effectivePreset = "ci-debug" }
        default {
            Write-Error "Debug mode supports -Preset default, ci, debug, or ci-debug. Received: '$Preset'."
            exit 1
        }
    }
}

$isDebugPreset = $effectivePreset -in @("debug", "ci-debug")
$buildDirName = if ($isDebugPreset) { "build-debug" } else { "build" }
$buildDir = Join-Path $ScriptDir $buildDirName

# ── Ensure VS Dev Shell environment (needed for Ninja + MSVC) ─────
$clFound = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $clFound) {
    Write-Host "Initializing VS Dev Shell..." -ForegroundColor Yellow
    $vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -property installationPath 2>$null
    if (-not $vsPath) {
        # Fallback: known VS 2026 location
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

# ── Verify Ninja is available ────────────────────────────────────
$ninjaFound = Get-Command ninja.exe -ErrorAction SilentlyContinue
if (-not $ninjaFound) {
    Write-Error "Ninja not found in PATH. Install Ninja or run from a VS Dev Shell that includes it."
    exit 1
}

# ── Step 1: Clean (optional) ─────────────────────────────────────
if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

# ── Step 2: CMake configure ─────────────────────────────────────
Write-Host "`n=== Configuring CMake (Ninja + Qt 6) ===" -ForegroundColor Cyan

Push-Location $ScriptDir
try {
    $cmakeArgs = @("--preset", $effectivePreset)
    Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    # ── Step 3: CMake build ──────────────────────────────────────
    Write-Host "`n=== Building Qt 6 GUI (Corrosion handles Rust build) ===" -ForegroundColor Cyan

    $buildArgs = @("--build", $buildDirName)
    Write-Host "cmake $($buildArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake build failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    Write-Host "`n=== Build complete ===" -ForegroundColor Green

    $exePath = Join-Path $buildDir "CLASSIC.exe"
    if (Test-Path $exePath) {
        Write-Host "Output: $exePath" -ForegroundColor Cyan
    }

    # ── Step 4: Tests (optional) ─────────────────────────────────
    if ($Test) {
        if ($TestTimeoutSec -le 0) {
            Write-Error "Test timeout must be greater than zero. Received: $TestTimeoutSec"
            exit 1
        }

        Write-Host "`n=== Running CTest ===" -ForegroundColor Cyan
        & ctest --test-dir $buildDirName -N -V --no-tests=error
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CTest discovery failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }

        & ctest --test-dir $buildDirName --output-on-failure --timeout $TestTimeoutSec --no-tests=error
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Tests failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Host "Tests passed." -ForegroundColor Green
    }

    # ── Step 5: Install (optional) ───────────────────────────────
    if ($Install) {
        $installDirName = if ($isDebugPreset) { "install-debug" } else { "install" }
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
} finally {
    Pop-Location
}
