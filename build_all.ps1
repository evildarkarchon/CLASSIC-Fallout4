# PowerShell build script for CLASSIC-Fallout4 PyInstaller executables
# This script builds all versions with proper data bundling and error handling

param(
    [switch]$BuildTest = $false,
    [switch]$NoClean = $false,
    [string]$UpxDir = "",
    [switch]$NoUpx = $false
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CLASSIC-Fallout4 Build Script (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Determine Python command - check for uv, otherwise use system Python
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $PyInstallerCmd = "uv run pyinstaller"
    $MaturinCmd = "uv run maturin"
    Write-Host "Using uv environment" -ForegroundColor Green
}
else {
    $PyInstallerCmd = "pyinstaller"
    $MaturinCmd = "maturin"
    Write-Host "Using system Python - Note: uv is recommended for this project" -ForegroundColor Yellow
    Write-Host "Install uv from: https://github.com/astral-sh/uv" -ForegroundColor Yellow
}

# Build Rust extensions first (if source available)
if (Test-Path "classic-rust") {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Building Rust extensions..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    # Build the Rust extension from classic-rust directory
    Write-Host "Building release build with maturin..." -ForegroundColor Yellow
    Push-Location classic-rust
    Invoke-Expression "$MaturinCmd build --release --out ../dist-rust 2>&1" | Out-Null
    Pop-Location

    if ($LASTEXITCODE -eq 0) {
        # Extract the built extension from wheel
        Write-Host "Extracting Rust extension from wheel..." -ForegroundColor Yellow
        if (-not (Test-Path "classic_core")) {
            New-Item -ItemType Directory -Path "classic_core" | Out-Null
        }

        # Extract classic_core package from wheel using native PowerShell
        $wheel = Get-ChildItem -Path "dist-rust\*.whl" | Select-Object -First 1
        if ($wheel) {
            $tempDir = "temp_extract"

            # Extract wheel (it's just a zip file)
            Expand-Archive -Path $wheel.FullName -DestinationPath $tempDir -Force

            # Find and copy the entire classic_core directory
            $coreDir = Get-ChildItem -Path $tempDir -Directory -Filter "classic_core" -Recurse | Select-Object -First 1
            if ($coreDir) {
                # Remove old classic_core if it exists
                if (Test-Path "classic_core") {
                    Remove-Item -Path "classic_core" -Recurse -Force
                }
                # Copy the entire directory
                Copy-Item -Path $coreDir.FullName -Destination "classic_core" -Recurse -Force
                Write-Host "Extracted classic_core package with:" -ForegroundColor Green
                Get-ChildItem -Path "classic_core" -File | ForEach-Object {
                    Write-Host "  - $($_.Name)" -ForegroundColor White
                }
            }
            else {
                Write-Host "WARNING: classic_core directory not found in wheel!" -ForegroundColor Red
            }

            # Clean up temp directory
            Remove-Item -Path $tempDir -Recurse -Force
        }
        else {
            Write-Host "WARNING: No wheel file found in dist-rust!" -ForegroundColor Red
        }

        # Create manifest file
        $manifestContent = @"
Rust extensions built on $(Get-Date)

Extensions:
$(Get-ChildItem -Path "classic_core" -Filter "*.pyd" | ForEach-Object { $_.Name })
"@
        Set-Content -Path "classic_core\MANIFEST.txt" -Value $manifestContent

        Write-Host "Rust extensions ready in classic_core/" -ForegroundColor Green
    }
    else {
        Write-Host "WARNING: Rust extension build failed!" -ForegroundColor Red
        Write-Host "Continuing without Rust optimizations..." -ForegroundColor Yellow
    }
    Write-Host ""
}
else {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Rust source not found - checking for pre-built extensions..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    if (Test-Path "classic_core") {
        Write-Host "Found pre-built Rust extensions in classic_core/" -ForegroundColor Green
        Get-ChildItem -Path "classic_core" -Filter "*.pyd" | ForEach-Object {
            Write-Host "  - $($_.Name)" -ForegroundColor White
        }
    }
    else {
        Write-Host "No Rust extensions available - using pure Python" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Clean previous builds if requested
if (-not $NoClean) {
    Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path "dist") { Remove-Item -Path "dist" -Recurse -Force }
    if (Test-Path "build") { Remove-Item -Path "build" -Recurse -Force }
    Write-Host ""
}

# Prepare PyInstaller arguments
$PyInstallerArgs = @("--clean")
if ($NoUpx) {
    Write-Host "Building without UPX compression" -ForegroundColor Yellow
}
elseif ($UpxDir) {
    $PyInstallerArgs += "--upx-dir", $UpxDir
    Write-Host "Using UPX from: $UpxDir" -ForegroundColor Green
}

# Function to build a spec file
function Build-Spec {
    param(
        [string]$SpecFile,
        [string]$Description
    )

    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Building $Description..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    $buildArgs = $PyInstallerArgs + $SpecFile
    Invoke-Expression "$PyInstallerCmd $($buildArgs -join ' ')"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: $Description build failed!" -ForegroundColor Red
        exit 1
    }

    Write-Host "$Description build complete!" -ForegroundColor Green
    Write-Host ""
}

# Build all versions
Build-Spec "CLASSIC.spec" "GUI version - Folder Distribution (CLASSIC.exe)"
Build-Spec "CLASSIC-GUI-OneFile.spec" "GUI version - Single File (CLASSIC-GUI-OneFile.exe)"
Build-Spec "CLASSIC-CLI.spec" "CLI version (CLASSIC-CLI.exe)"
Build-Spec "CLASSIC-TUI.spec" "TUI version (CLASSIC-TUI.exe)"

# Optional test build
if ($BuildTest) {
    Build-Spec "CLASSIC-Test.spec" "Test version (CLASSIC-Test.exe)"
}

# Test the frozen executable
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Testing frozen executable..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path "dist\CLASSIC-Test.exe") {
    & "dist\CLASSIC-Test.exe"
}
else {
    Write-Host "Test executable not built. Use -BuildTest to include it." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Build Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# List built executables with sizes
$executables = @(
    @{Path = "dist\CLASSIC\CLASSIC.exe"; Type = "GUI (Folder)" },
    @{Path = "dist\CLASSIC-GUI-OneFile.exe"; Type = "GUI (Single File)" },
    @{Path = "dist\CLASSIC-CLI.exe"; Type = "CLI (Single)" },
    @{Path = "dist\CLASSIC-TUI.exe"; Type = "TUI (Single)" }
)

if ($BuildTest) {
    $executables += @{Path = "dist\CLASSIC-Test.exe"; Type = "Test (Debug)" }
}

foreach ($exe in $executables) {
    if (Test-Path $exe.Path) {
        $file = Get-Item $exe.Path
        $sizeMB = [math]::Round($file.Length / 1MB, 2)
        Write-Host ("{0,-20} {1,10} MB - {2}" -f $exe.Type, $sizeMB, $file.Name) -ForegroundColor Green
    }
    else {
        Write-Host ("{0,-20} Not found!" -f $exe.Type) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "All builds completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Executables are located in the 'dist' directory:" -ForegroundColor Cyan
Write-Host "  - GUI Folder: dist\CLASSIC\CLASSIC.exe (folder distribution - smaller)" -ForegroundColor White
Write-Host "  - GUI Single: dist\CLASSIC-GUI-OneFile.exe (single file - portable)" -ForegroundColor White
Write-Host "  - CLI: dist\CLASSIC-CLI.exe (single file)" -ForegroundColor White
Write-Host "  - TUI: dist\CLASSIC-TUI.exe (single file)" -ForegroundColor White

if ($BuildTest) {
    Write-Host "  - Test: dist\CLASSIC-Test.exe (debug build)" -ForegroundColor White
}

Write-Host ""
Write-Host "Build script completed!" -ForegroundColor Green
Write-Host "Build script completed!" -ForegroundColor Green
