# Rebuild Rust Extension Script
# Ensures clean rebuild of all Rust Python modules

$ErrorActionPreference = "Stop"

# Define all Rust Python modules in dependency order
# WheelName: used for finding the built wheel file (must match Cargo package name with dashes->underscores)
# Dir: the source directory (relative to rust/ directory)
# ImportName: the actual Python module name for import (optional, defaults to WheelName)
$RustModules = @(
    @{WheelName = "classic_shared_py"; Dir = "rust/foundation/classic-shared-py"; ImportName = $null },  # Not a Python module
    @{WheelName = "classic_config_py"; Dir = "rust/python-bindings/classic-config-py"; ImportName = "classic_config" },
    @{WheelName = "classic_database_py"; Dir = "rust/python-bindings/classic-database-py"; ImportName = "classic_database" },
    @{WheelName = "classic_file_io_py"; Dir = "rust/python-bindings/classic-file-io-py"; ImportName = "classic_file_io" },
    @{WheelName = "classic_message_py"; Dir = "rust/python-bindings/classic-message-py"; ImportName = "classic_message" },
    @{WheelName = "classic_path_py"; Dir = "rust/python-bindings/classic-path-py"; ImportName = "classic_path" },
    @{WheelName = "classic_perf_py"; Dir = "rust/python-bindings/classic-perf-py"; ImportName = "classic_perf" },
    @{WheelName = "classic_pybridge_py"; Dir = "rust/python-bindings/classic-pybridge-py"; ImportName = "classic_pybridge" },
    @{WheelName = "classic_registry_py"; Dir = "rust/python-bindings/classic-registry-py"; ImportName = "classic_registry" },
    @{WheelName = "classic_scangame_py"; Dir = "rust/python-bindings/classic-scangame-py"; ImportName = "classic_scangame" },
    @{WheelName = "classic_scanlog_py"; Dir = "rust/python-bindings/classic-scanlog-py"; ImportName = "classic_scanlog" },
    @{WheelName = "classic_settings_py"; Dir = "rust/python-bindings/classic-settings-py"; ImportName = "classic_settings" },
    @{WheelName = "classic_yaml_py"; Dir = "rust/python-bindings/classic-yaml-py"; ImportName = "classic_yaml" },

    # Phase 4 - Constants and Utilities
    @{WheelName = "classic_constants_py"; Dir = "rust/python-bindings/classic-constants-py"; ImportName = "classic_constants" },
    @{WheelName = "classic_version_py"; Dir = "rust/python-bindings/classic-version-py"; ImportName = "classic_version" },
    @{WheelName = "classic_resource_py"; Dir = "rust/python-bindings/classic-resource-py"; ImportName = "classic_resource" },
    @{WheelName = "classic_xse_py"; Dir = "rust/python-bindings/classic-xse-py"; ImportName = "classic_xse" },
    @{WheelName = "classic_web_py"; Dir = "rust/python-bindings/classic-web-py"; ImportName = "classic_web" },

    # Phase 5 - Application Coordination
    @{WheelName = "classic_update_py"; Dir = "rust/python-bindings/classic-update-py"; ImportName = "classic_update" }
)

Write-Host "🧹 Cleaning old builds..." -ForegroundColor Cyan
Push-Location rust
cargo clean --workspace
Pop-Location

Write-Host "🗑️  Removing old .pyd files from venv..." -ForegroundColor Cyan
foreach ($module in $RustModules) {
    Remove-Item -Path ".venv\Lib\site-packages\$($module.WheelName)*.pyd" -ErrorAction SilentlyContinue
    Remove-Item -Path ".venv\Lib\site-packages\$($module.WheelName)*.dll" -ErrorAction SilentlyContinue
    Remove-Item -Path ".venv\Lib\site-packages\$($module.WheelName)-*.dist-info" -Recurse -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "🔨 Building and installing Rust modules in dependency order..." -ForegroundColor Yellow
Write-Host ""

foreach ($module in $RustModules) {
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Building $($module.WheelName)..." -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

    Push-Location $module.Dir

    # Build wheel
    maturin build --release --out dist
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Error "Failed to build $($module.WheelName)!"
        exit 1
    }

    # Find and install the latest wheel
    $wheel = Get-ChildItem -Path "dist\$($module.WheelName)-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($wheel) {
        Write-Host "📦 Installing $($module.WheelName)..." -ForegroundColor Green
        uv pip install $wheel.FullName --force-reinstall
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-Error "Failed to install $($module.WheelName)!"
            exit 1
        }
    }
    else {
        Pop-Location
        Write-Error "No wheel file found for $($module.WheelName)!"
        exit 1
    }

    Pop-Location
    Write-Host ""
}

Write-Host "✅ Verifying installations..." -ForegroundColor Green
Write-Host ""

# Verify each module
$verificationResults = @()
foreach ($module in $RustModules) {
    # Special handling for non-Python modules (like classic_shared - pure Rust rlib)
    if ($null -eq $module.ImportName) {
        # Verify the rlib was built by checking target directory
        $rlibPath = "rust\target\release\$($module.WheelName.Replace('_', '-')).rlib"
        if (Test-Path $rlibPath) {
            $verificationResults += @{Module = $module.WheelName; Status = "✓"; Version = "Rust rlib"; IsPython = $false }
            Write-Host "  ✓ $($module.WheelName) - Rust library built" -ForegroundColor Cyan
        }
        else {
            $verificationResults += @{Module = $module.WheelName; Status = "✗"; Version = "Not found"; IsPython = $false }
            Write-Host "  ✗ $($module.WheelName) - Rust library not found" -ForegroundColor Red
        }
        continue
    }
    
    # Verify Python modules via import
    try {
        $importName = $module.ImportName
        $version = .venv\Scripts\python -c "import $importName; print($importName.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $verificationResults += @{Module = $module.WheelName; Status = "✓"; Version = $version; IsPython = $true }
            Write-Host "  ✓ $($module.WheelName) (import: $importName) v$version" -ForegroundColor Green
        }
        else {
            $verificationResults += @{Module = $module.WheelName; Status = "✗"; Version = "Failed"; IsPython = $true }
            Write-Host "  ✗ $($module.WheelName) (import: $importName) - Import failed" -ForegroundColor Red
        }
    }
    catch {
        $verificationResults += @{Module = $module.WheelName; Status = "✗"; Version = "Error"; IsPython = $true }
        Write-Host "  ✗ $($module.WheelName) (import: $importName) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

$successCount = ($verificationResults | Where-Object { $_.Status -eq "✓" }).Count
$pythonModuleCount = ($verificationResults | Where-Object { $_.IsPython -eq $true }).Count
$pythonSuccessCount = ($verificationResults | Where-Object { $_.Status -eq "✓" -and $_.IsPython -eq $true }).Count
$totalCount = $verificationResults.Count

Write-Host ""
Write-Host "Installed: $pythonSuccessCount/$pythonModuleCount Python modules | $successCount/$totalCount total" -ForegroundColor $(if ($successCount -eq $totalCount) { "Green" } else { "Yellow" })
Write-Host ""

if ($successCount -eq $totalCount) {
    Write-Host "✨ Rebuild complete - All modules built and installed successfully!" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Some modules failed to build or install!" -ForegroundColor Yellow
    exit 1
}
