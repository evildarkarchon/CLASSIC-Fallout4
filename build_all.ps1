# PowerShell build script for CLASSIC-Fallout4 PyInstaller executables
# This script builds all versions with proper data bundling and error handling
# Note: UPX compression is disabled to avoid antivirus false positives
#
# Parameters:
#   -BuildTest           : Also build the test executable
#   -NoClean            : Skip cleaning previous builds
#   -AutoCleanShadowing : Automatically delete shadowing directories without prompting

param(
    [switch]$BuildTest = $false,
    [switch]$NoClean = $false,
    [switch]$AutoCleanShadowing = $false  # Automatically clean shadowing directories without prompting
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CLASSIC-Fallout4 Build Script (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Clean up any shadowing directories in project root that could interfere with imports
# These directories can be created by accidental wheel extractions or build artifacts
$ShadowingDirs = @(
    "classic_shared",
    "classic_config",
    "classic_database",
    "classic_file_io",
    "classic_message",
    "classic_path",
    "classic_perf",
    "classic_pybridge",
    "classic_registry",
    "classic_scangame",
    "classic_scanlog",
    "classic_settings",
    "classic_yaml"
)

$foundShadowingDirs = @()
foreach ($dirName in $ShadowingDirs) {
    $dirPath = Join-Path $PSScriptRoot $dirName
    if (Test-Path $dirPath -PathType Container) {
        $foundShadowingDirs += @{Path = $dirPath; Name = $dirName}
    }
}

if ($foundShadowingDirs.Count -gt 0) {
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "WARNING: Found directories that could shadow Rust modules!" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    foreach ($dir in $foundShadowingDirs) {
        $isEmpty = (Get-ChildItem -Path $dir.Path -Force | Measure-Object).Count -eq 0
        if ($isEmpty) {
            Write-Host "  - $($dir.Name) (empty)" -ForegroundColor Cyan
        } else {
            Write-Host "  - $($dir.Name) (contains files)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "These directories can prevent Python from finding the installed Rust modules." -ForegroundColor Yellow
    Write-Host "They are likely build artifacts or accidental wheel extractions." -ForegroundColor Yellow
    Write-Host ""

    if ($AutoCleanShadowing) {
        Write-Host "Auto-cleanup enabled - deleting all shadowing directories..." -ForegroundColor Cyan
        $response = "Y"
    } else {
        $response = Read-Host "Delete these directories? [Y]es / [N]o / [E]mpty only (default: E)"
        if ([string]::IsNullOrWhiteSpace($response)) { $response = "E" }
    }

    switch ($response.ToUpper()) {
        "Y" {
            foreach ($dir in $foundShadowingDirs) {
                Write-Host "  Deleting $($dir.Name)..." -ForegroundColor Cyan
                Remove-Item -Path $dir.Path -Recurse -Force
            }
            Write-Host "Cleanup complete!" -ForegroundColor Green
        }
        "E" {
            $deletedCount = 0
            foreach ($dir in $foundShadowingDirs) {
                $isEmpty = (Get-ChildItem -Path $dir.Path -Force | Measure-Object).Count -eq 0
                if ($isEmpty) {
                    Write-Host "  Deleting empty directory $($dir.Name)..." -ForegroundColor Cyan
                    Remove-Item -Path $dir.Path -Recurse -Force
                    $deletedCount++
                } else {
                    Write-Host "  Skipping non-empty directory $($dir.Name)" -ForegroundColor Yellow
                }
            }
            if ($deletedCount -gt 0) {
                Write-Host "Deleted $deletedCount empty directories" -ForegroundColor Green
            }
            $remaining = $foundShadowingDirs.Count - $deletedCount
            if ($remaining -gt 0) {
                Write-Host "WARNING: $remaining non-empty directories remain - these may cause import issues!" -ForegroundColor Yellow
            }
        }
        "N" {
            Write-Host "Skipping cleanup - continuing with build..." -ForegroundColor Yellow
            Write-Host "WARNING: These directories may cause import issues!" -ForegroundColor Yellow
        }
        default {
            Write-Host "Invalid response - skipping cleanup..." -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

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
#
# Architecture Overview (as of 2025-10-08):
# -----------------------------------------
# The Rust workspace uses separated architecture:
#   - *-core crates: Pure Rust business logic (rlib only, NO PyO3)
#   - *-py crates: Thin PyO3 bindings (cdylib, produces .pyd files)
#
# This separation enables:
#   1. CLI/TUI applications to use pure Rust business logic directly
#   2. Python applications to use the same logic via PyO3 bindings
#   3. 10-150x performance improvements for all operations
# Python imports individual modules directly (e.g., import classic_yaml)
#
if (Test-Path "rust/python-bindings/classic-yaml-py") {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Building Rust workspace (separated architecture)..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Building: *-core crates (business logic) + *-py crates (bindings)" -ForegroundColor Yellow

    # Define all Rust Python modules (.pyd files from *-py crates) in dependency order
    # Note: Only *-py crates produce .pyd files; *-core crates are pure Rust (rlib)
    $RustModules = @(
        @{Name = "classic_shared"; Dir = "rust/foundation/classic-shared-py"; Description = "Foundation (runtime, errors, utilities)"},
        @{Name = "classic_config"; Dir = "rust/python-bindings/classic-config-py"; Description = "YamlData configuration (bindings)"},
        @{Name = "classic_database"; Dir = "rust/python-bindings/classic-database-py"; Description = "SQLite operations (bindings)"},
        @{Name = "classic_file_io"; Dir = "rust/python-bindings/classic-file-io-py"; Description = "File I/O + DDS parsing (bindings)"},
        @{Name = "classic_message"; Dir = "rust/python-bindings/classic-message-py"; Description = "Message handling (bindings)"},
        @{Name = "classic_path"; Dir = "rust/python-bindings/classic-path-py"; Description = "Path management (bindings)"},
        @{Name = "classic_perf"; Dir = "rust/python-bindings/classic-perf-py"; Description = "Performance monitoring (bindings)"},
        @{Name = "classic_pybridge"; Dir = "rust/python-bindings/classic-pybridge-py"; Description = "Async Python bridge utilities (bindings)"},
        @{Name = "classic_registry"; Dir = "rust/python-bindings/classic-registry-py"; Description = "Windows registry operations (bindings)"},
        @{Name = "classic_scangame"; Dir = "rust/python-bindings/classic-scangame-py"; Description = "Game scanning + validation (bindings)"},
        @{Name = "classic_scanlog"; Dir = "rust/python-bindings/classic-scanlog-py"; Description = "Log parsing + analysis (bindings)"},
        @{Name = "classic_settings"; Dir = "rust/python-bindings/classic-settings-py"; Description = "Settings cache management (bindings)"},
        @{Name = "classic_yaml"; Dir = "rust/python-bindings/classic-yaml-py"; Description = "YAML operations (bindings for yaml-rust2)"}
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

        # Extract each module's .pyd from its wheel (flattened structure)
        $extractedModules = @()
        foreach ($module in $RustModules) {
            $wheel = Get-ChildItem -Path "dist-rust\$($module.Name)-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($wheel) {
                $tempDir = "temp_extract_$($module.Name)"

                # Extract wheel (it's just a zip file)
                Expand-Archive -Path $wheel.FullName -DestinationPath $tempDir -Force

                # Find the module directory
                $moduleDir = Get-ChildItem -Path $tempDir -Directory -Filter $module.Name -Recurse | Select-Object -First 1
                if ($moduleDir) {
                    # Copy .pyd files directly to rust_extensions/ (flattened)
                    $pydFiles = Get-ChildItem -Path $moduleDir.FullName -Filter "*.pyd" -Recurse
                    foreach ($pyd in $pydFiles) {
                        $destFile = Join-Path $rustExtDir $pyd.Name
                        Copy-Item -Path $pyd.FullName -Destination $destFile -Force
                        $extractedModules += @{Module = $module.Name; File = $pyd.Name}
                    }

                    # Copy __init__.py if it exists (directly to rust_extensions/)
                    $initFile = Get-ChildItem -Path $moduleDir.FullName -Filter "__init__.py" -Recurse | Select-Object -First 1
                    if ($initFile) {
                        $destInit = Join-Path $rustExtDir "$($module.Name)__init__.py"
                        Copy-Item -Path $initFile.FullName -Destination $destInit -Force
                    }

                    # Copy .pyi files if they exist (directly to rust_extensions/)
                    $pyiFiles = Get-ChildItem -Path $moduleDir.FullName -Filter "*.pyi" -Recurse
                    foreach ($pyi in $pyiFiles) {
                        $destPyi = Join-Path $rustExtDir $pyi.Name
                        Copy-Item -Path $pyi.FullName -Destination $destPyi -Force
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
            Write-Host "Extracted Rust Python modules (.pyd files - flattened):" -ForegroundColor Green
            foreach ($ext in $extractedModules) {
                Write-Host "  - $($ext.Module): $($ext.File)" -ForegroundColor White
            }
            Write-Host ""
            Write-Host "Note: Files are extracted directly to rust_extensions/ (no subdirectories)" -ForegroundColor Yellow
            Write-Host "This prevents shadowing the actual Rust modules in site-packages" -ForegroundColor Yellow

            # Create manifest file
            $manifestContent = @"
Rust extensions built on $(Get-Date)

Architecture: Separated *-core (business logic) + *-py (PyO3 bindings)
Structure: Flattened (no subdirectories to avoid module shadowing)

Modules:
$($extractedModules | ForEach-Object { "$($_.Module): $($_.File)" } | Out-String)
"@
            Set-Content -Path "$rustExtDir\MANIFEST.txt" -Value $manifestContent
        }
        else {
            Write-Host "WARNING: No Rust extensions extracted!" -ForegroundColor Red
        }

        Write-Host "Rust extensions ready in $rustExtDir/ (flattened structure)" -ForegroundColor Green
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
        Write-Host "Found pre-built Rust extensions in $rustExtDir/ (flattened)" -ForegroundColor Green
        Get-ChildItem -Path $rustExtDir -Filter "*.pyd" | ForEach-Object {
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
