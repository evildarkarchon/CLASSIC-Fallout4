# PowerShell build script for CLASSIC-Fallout4 PyInstaller executables
# This script builds all versions with proper data bundling and error handling
# Note: UPX compression is disabled to avoid antivirus false positives

param(
    [switch]$BuildTest = $false,
    [switch]$NoClean = $false
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

# Build Rust workspace (if source available)
if (Test-Path "classic-core") {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Building Rust workspace..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    # Define all Rust Python modules in dependency order
    $RustModules = @(
        @{Name = "classic_shared"; Dir = "classic-shared"},
        @{Name = "classic_yaml"; Dir = "classic-yaml"},
        @{Name = "classic_database"; Dir = "classic-database"},
        @{Name = "classic_file_io"; Dir = "classic-file-io"},
        @{Name = "classic_scanlog"; Dir = "classic-scanlog"},
        @{Name = "classic_config"; Dir = "config-core"},
        @{Name = "classic_core"; Dir = "classic-core"}
    )

    # Build all Rust modules
    Write-Host "Building Rust modules with maturin..." -ForegroundColor Yellow
    $buildSuccess = $true
    foreach ($module in $RustModules) {
        Write-Host "  Building $($module.Name)..." -ForegroundColor Cyan
        Push-Location $module.Dir
        Invoke-Expression "$MaturinCmd build --release --out ../dist-rust 2>&1" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  WARNING: $($module.Name) build failed!" -ForegroundColor Red
            $buildSuccess = $false
        }
        Pop-Location
    }

    if ($buildSuccess) {
        # Extract all built extensions from wheels
        Write-Host "Extracting Rust extensions from wheels..." -ForegroundColor Yellow

        # Create base directory for all Rust modules
        $rustExtDir = "rust_extensions"
        if (Test-Path $rustExtDir) {
            Remove-Item -Path $rustExtDir -Recurse -Force
        }
        New-Item -ItemType Directory -Path $rustExtDir | Out-Null

        # Extract each module's .pyd from its wheel
        $extractedModules = @()
        foreach ($module in $RustModules) {
            $wheel = Get-ChildItem -Path "dist-rust\$($module.Name)-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($wheel) {
                $tempDir = "temp_extract_$($module.Name)"

                # Extract wheel (it's just a zip file)
                Expand-Archive -Path $wheel.FullName -DestinationPath $tempDir -Force

                # Find and copy the module directory
                $moduleDir = Get-ChildItem -Path $tempDir -Directory -Filter $module.Name -Recurse | Select-Object -First 1
                if ($moduleDir) {
                    # Copy the entire module directory
                    $destPath = Join-Path $rustExtDir $module.Name
                    Copy-Item -Path $moduleDir.FullName -Destination $destPath -Recurse -Force

                    # Track extracted files
                    $pydFiles = Get-ChildItem -Path $destPath -Filter "*.pyd" -Recurse
                    foreach ($pyd in $pydFiles) {
                        $extractedModules += @{Module = $module.Name; File = $pyd.Name}
                    }
                }
                else {
                    Write-Host "  WARNING: $($module.Name) directory not found in wheel!" -ForegroundColor Yellow
                }

                # Clean up temp directory
                Remove-Item -Path $tempDir -Recurse -Force
            }
            else {
                Write-Host "  WARNING: No wheel file found for $($module.Name)!" -ForegroundColor Yellow
            }
        }

        # Display extracted modules
        if ($extractedModules.Count -gt 0) {
            Write-Host "Extracted Rust extensions:" -ForegroundColor Green
            foreach ($ext in $extractedModules) {
                Write-Host "  - $($ext.Module): $($ext.File)" -ForegroundColor White
            }

            # Create manifest file
            $manifestContent = @"
Rust extensions built on $(Get-Date)

Modules:
$($extractedModules | ForEach-Object { "$($_.Module): $($_.File)" } | Out-String)
"@
            Set-Content -Path "$rustExtDir\MANIFEST.txt" -Value $manifestContent
        }
        else {
            Write-Host "WARNING: No Rust extensions extracted!" -ForegroundColor Red
        }

        Write-Host "Rust extensions ready in $rustExtDir/" -ForegroundColor Green
    }
    else {
        Write-Host "WARNING: Some Rust modules failed to build!" -ForegroundColor Red
        Write-Host "Continuing without full Rust optimizations..." -ForegroundColor Yellow
    }
    Write-Host ""
}
else {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Rust source not found - checking for pre-built extensions..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    $rustExtDir = "rust_extensions"
    if (Test-Path $rustExtDir) {
        Write-Host "Found pre-built Rust extensions in $rustExtDir/" -ForegroundColor Green
        Get-ChildItem -Path $rustExtDir -Filter "*.pyd" -Recurse | ForEach-Object {
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

# Prepare PyInstaller arguments (UPX disabled in spec files)
$PyInstallerArgs = @("--clean")

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
