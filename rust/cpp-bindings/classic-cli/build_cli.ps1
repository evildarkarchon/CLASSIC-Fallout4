<#
.SYNOPSIS
    Build the CLASSIC C++ CLI scanner.

.DESCRIPTION
    Builds the Rust static library (classic-cpp-bridge) then the C++ CLI
    application using CMake with vcpkg integration.

.PARAMETER Release
    Build the Rust static library in release mode (default: debug).
    The C++ build always uses Release config due to MSVC CRT constraints.

.PARAMETER Clean
    Remove build directory before building.

.PARAMETER CargoOnly
    Only build the Rust static library, skip CMake.

.EXAMPLE
    .\build_cli.ps1
    .\build_cli.ps1 -Release
    .\build_cli.ps1 -Clean -Release
#>

[CmdletBinding()]
param(
    [switch]$Release,
    [switch]$Clean,
    [switch]$CargoOnly
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RustRoot = (Resolve-Path "$ScriptDir/../..").Path
$CargoToml = Join-Path $RustRoot "Cargo.toml"

# Verify VCPKG_ROOT is set
if (-not $env:VCPKG_ROOT) {
    Write-Error "VCPKG_ROOT environment variable is not set. Install vcpkg and set VCPKG_ROOT."
    exit 1
}

# ── Step 1: Build Rust static library ───────────────────────────────
Write-Host "`n=== Building Rust static library ===" -ForegroundColor Cyan

$cargoArgs = @("build", "-p", "classic-cpp-bridge", "--manifest-path", $CargoToml)
if ($Release) {
    $cargoArgs += "--release"
}

Write-Host "cargo $($cargoArgs -join ' ')" -ForegroundColor DarkGray
& cargo @cargoArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cargo build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Rust build complete." -ForegroundColor Green

if ($CargoOnly) {
    Write-Host "CargoOnly flag set, skipping CMake build." -ForegroundColor Yellow
    exit 0
}

# ── Step 2: CMake configure ─────────────────────────────────────────
Write-Host "`n=== Configuring CMake ===" -ForegroundColor Cyan

$buildDir = Join-Path $ScriptDir "build"

if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

# CMAKE_BUILD_TYPE is ignored by MSVC multi-config generators.
# The actual config (Release) is selected at build time via --config.
$cmakeArgs = @("--preset", "default")

Push-Location $ScriptDir
try {
    Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    # ── Step 3: CMake build ─────────────────────────────────────────
    Write-Host "`n=== Building C++ CLI ===" -ForegroundColor Cyan

    # NOTE: Always use --config Release for MSVC builds.
    # cxx-build compiles C++ bridge glue with /MD (release CRT) regardless of
    # Rust profile, so Debug builds cause LNK2038 CRT mismatch errors.
    $buildArgs = @("--build", "build", "--config", "Release")

    Write-Host "cmake $($buildArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake build failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    Write-Host "`n=== Build complete ===" -ForegroundColor Green

    # Show output location
    $exeName = "classic-cli.exe"
    $possiblePaths = @(
        (Join-Path $buildDir "Debug" $exeName),
        (Join-Path $buildDir "Release" $exeName),
        (Join-Path $buildDir $exeName)
    )

    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            Write-Host "Output: $path" -ForegroundColor Cyan
            break
        }
    }
} finally {
    Pop-Location
}
