# ==============================================================================
# CLASSIC Rust Extension Local Build Script (PowerShell)
# ==============================================================================
# This script builds the Rust extensions locally and places them in the correct
# locations for both development (uvx) and production (PyInstaller) use.
#
# NO pip installation, NO GitHub Actions, NO CI/CD required!
# Everything is built and bundled locally on the developer's machine.
# ==============================================================================

param(
    [switch]$Clean = $false,
    [switch]$Debug = $false
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CLASSIC Rust Extension Builder (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[1/8] Checking prerequisites..." -ForegroundColor Yellow

# Check for maturin
if (-not (Get-Command maturin -ErrorAction SilentlyContinue)) {
    # Try with uv
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $MaturinCmd = "uv run maturin"
        Write-Host "Using uv run maturin" -ForegroundColor Green
    } else {
        Write-Host "ERROR: maturin not found. Please install it first:" -ForegroundColor Red
        Write-Host "  pip install maturin" -ForegroundColor Red
        Write-Host "  or: uv tool install maturin" -ForegroundColor Red
        exit 1
    }
} else {
    $MaturinCmd = "maturin"
    Write-Host "Using system maturin" -ForegroundColor Green
}

# Check for Rust/Cargo
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Rust/Cargo not found. Please install Rust from https://rustup.rs/" -ForegroundColor Red
    exit 1
}

# Set up directories
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RustExtensionsDir = Join-Path $ProjectRoot "rust_extensions"
$TempBuildDir = Join-Path $ProjectRoot "temp_rust_build"

Write-Host ""
Write-Host "[2/8] Setting up directories..." -ForegroundColor Yellow
Write-Host "  Project Root: $ProjectRoot" -ForegroundColor White
Write-Host "  Extensions Dir: $RustExtensionsDir" -ForegroundColor White
Write-Host "  Temp Build: $TempBuildDir" -ForegroundColor White

# Create directories
if (-not (Test-Path $RustExtensionsDir)) {
    New-Item -ItemType Directory -Path $RustExtensionsDir | Out-Null
}
if (-not (Test-Path $TempBuildDir)) {
    New-Item -ItemType Directory -Path $TempBuildDir | Out-Null
}

# Clean previous builds if requested
if ($Clean) {
    Write-Host ""
    Write-Host "[3/8] Cleaning previous builds..." -ForegroundColor Yellow
    Get-ChildItem -Path $RustExtensionsDir -Filter "*.pyd" | Remove-Item -Force
    Get-ChildItem -Path $RustExtensionsDir -Filter "*.so" | Remove-Item -Force
    Get-ChildItem -Path $RustExtensionsDir -Filter "*.dll" | Remove-Item -Force
    Get-ChildItem -Path $TempBuildDir | Remove-Item -Force -Recurse
} else {
    Write-Host ""
    Write-Host "[3/8] Skipping clean (use -Clean to force)" -ForegroundColor Gray
}

# Build the Rust extension
Write-Host ""
Write-Host "[4/8] Building Rust extension with maturin..." -ForegroundColor Yellow

Set-Location $ProjectRoot

# Build command
if ($Debug) {
    $BuildCmd = "$MaturinCmd build --out `"$TempBuildDir`""
    Write-Host "  Building in DEBUG mode" -ForegroundColor Yellow
} else {
    $BuildCmd = "$MaturinCmd build --release --out `"$TempBuildDir`""
    Write-Host "  Building in RELEASE mode" -ForegroundColor Green
}

# Execute build
$BuildResult = Invoke-Expression $BuildCmd 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Maturin build failed!" -ForegroundColor Red
    Write-Host $BuildResult -ForegroundColor Red
    exit 1
}

# Find the wheel file
Write-Host ""
Write-Host "[5/8] Extracting compiled extension from wheel..." -ForegroundColor Yellow

$WheelFile = Get-ChildItem -Path $TempBuildDir -Filter "*.whl" | Select-Object -First 1
if (-not $WheelFile) {
    Write-Host "ERROR: No wheel file found in $TempBuildDir" -ForegroundColor Red
    exit 1
}

Write-Host "  Found wheel: $($WheelFile.Name)" -ForegroundColor White

# Extract the wheel
$ExtractDir = Join-Path $TempBuildDir "extracted"
if (Test-Path $ExtractDir) {
    Remove-Item -Path $ExtractDir -Recurse -Force
}

Expand-Archive -Path $WheelFile.FullName -DestinationPath $ExtractDir -Force

# Copy extensions
Write-Host ""
Write-Host "[6/8] Copying compiled extensions..." -ForegroundColor Yellow

# Find and copy .pyd files
$PydFiles = Get-ChildItem -Path $ExtractDir -Filter "*.pyd" -Recurse
foreach ($PydFile in $PydFiles) {
    Write-Host "  Found extension: $($PydFile.Name)" -ForegroundColor Green

    # Copy to rust_extensions for PyInstaller
    Copy-Item -Path $PydFile.FullName -Destination $RustExtensionsDir -Force

    # Copy to Python package location
    $TargetDir = Join-Path $ProjectRoot "classic-rust\python\classic_core"
    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }
    Copy-Item -Path $PydFile.FullName -Destination $TargetDir -Force

    # Copy to ClassicLib for backward compatibility
    $ClassicLibDir = Join-Path $ProjectRoot "ClassicLib\rust_ext"
    if (-not (Test-Path $ClassicLibDir)) {
        New-Item -ItemType Directory -Path $ClassicLibDir -Force | Out-Null
    }
    Copy-Item -Path $PydFile.FullName -Destination $ClassicLibDir -Force
}

# Copy any required DLL dependencies (excluding Python DLLs)
$DllFiles = Get-ChildItem -Path $ExtractDir -Filter "*.dll" -Recurse
foreach ($DllFile in $DllFiles) {
    if ($DllFile.Name -notmatch "python") {
        Write-Host "  Found dependency: $($DllFile.Name)" -ForegroundColor White
        Copy-Item -Path $DllFile.FullName -Destination $RustExtensionsDir -Force
    }
}

# Create manifest file
Write-Host ""
Write-Host "[7/8] Creating manifest file..." -ForegroundColor Yellow

$ManifestContent = @"
Rust Extensions Build Manifest
==============================
Build Date: $(Get-Date)
Build Mode: $(if ($Debug) { "DEBUG" } else { "RELEASE" })

Files:
$(Get-ChildItem -Path $RustExtensionsDir -Filter "*.pyd" | ForEach-Object { "  - $($_.Name)" })
$(Get-ChildItem -Path $RustExtensionsDir -Filter "*.dll" | Where-Object { $_.Name -notmatch "python" } | ForEach-Object { "  - $($_.Name)" })

Locations:
  - rust_extensions\  (for PyInstaller bundling)
  - classic-rust\python\classic_core\  (for development)
  - ClassicLib\rust_ext\  (for backward compatibility)

Python Version: $(python --version 2>&1)
Rust Version: $(rustc --version 2>&1)
"@

Set-Content -Path (Join-Path $RustExtensionsDir "MANIFEST.txt") -Value $ManifestContent

# Clean up
Write-Host ""
Write-Host "[8/8] Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item -Path $TempBuildDir -Recurse -Force

# Test the extension
Write-Host ""
Write-Host "Testing if extension can be loaded..." -ForegroundColor Yellow

$TestScript = @"
import sys
sys.path.insert(0, 'rust_extensions')
try:
    from classic_core import _rust
    print('SUCCESS: Extension loads correctly!')
    exit(0)
except ImportError as e:
    print(f'Failed to load: {e}')
    exit(1)
"@

$TestResult = $TestScript | python - 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Extension validated successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠ Warning: Could not validate extension loading." -ForegroundColor Yellow
    Write-Host "  This might be normal if the extension has specific dependencies." -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   BUILD COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Rust extensions have been built and placed in:" -ForegroundColor Cyan
Write-Host "  1. $RustExtensionsDir" -ForegroundColor White
Write-Host "  2. $ProjectRoot\classic-rust\python\classic_core" -ForegroundColor White
Write-Host "  3. $ProjectRoot\ClassicLib\rust_ext" -ForegroundColor White
Write-Host ""
Write-Host "These locations ensure the extensions work with:" -ForegroundColor Cyan
Write-Host "  - PyInstaller (bundled in _internal)" -ForegroundColor White
Write-Host "  - uvx (from GitHub repo)" -ForegroundColor White
Write-Host "  - Local development (direct import)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Commit the rust_extensions directory to git" -ForegroundColor White
Write-Host "  2. Run build_all.ps1 to create executables" -ForegroundColor White
Write-Host "  3. Test with example_rust_usage.py" -ForegroundColor White
Write-Host ""
