# Rebuild Rust Extension Script
# Ensures clean rebuild of all Rust Python modules

$ErrorActionPreference = "Stop"

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

Write-Host "🧹 Cleaning old builds..." -ForegroundColor Cyan
cargo clean --workspace

Write-Host "🗑️  Removing old .pyd files from venv..." -ForegroundColor Cyan
foreach ($module in $RustModules) {
    Remove-Item -Path ".venv\Lib\site-packages\$($module.Name)*.pyd" -ErrorAction SilentlyContinue
    Remove-Item -Path ".venv\Lib\site-packages\$($module.Name)*.dll" -ErrorAction SilentlyContinue
    Remove-Item -Path ".venv\Lib\site-packages\$($module.Name)-*.dist-info" -Recurse -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "🔨 Building and installing Rust modules in dependency order..." -ForegroundColor Yellow
Write-Host ""

foreach ($module in $RustModules) {
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Building $($module.Name)..." -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

    Push-Location $module.Dir

    # Build wheel
    maturin build --release --out dist
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Error "Failed to build $($module.Name)!"
        exit 1
    }

    # Find and install the latest wheel
    $wheel = Get-ChildItem -Path "dist\$($module.Name)-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($wheel) {
        Write-Host "📦 Installing $($module.Name)..." -ForegroundColor Green
        uv pip install $wheel.FullName --force-reinstall
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-Error "Failed to install $($module.Name)!"
            exit 1
        }
    } else {
        Pop-Location
        Write-Error "No wheel file found for $($module.Name)!"
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
    try {
        $version = .venv\Scripts\python -c "import $($module.Name); print($($module.Name).__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $verificationResults += @{Module = $module.Name; Status = "✓"; Version = $version}
            Write-Host "  ✓ $($module.Name) v$version" -ForegroundColor Green
        } else {
            $verificationResults += @{Module = $module.Name; Status = "✗"; Version = "Failed"}
            Write-Host "  ✗ $($module.Name) - Import failed" -ForegroundColor Red
        }
    } catch {
        $verificationResults += @{Module = $module.Name; Status = "✗"; Version = "Error"}
        Write-Host "  ✗ $($module.Name) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

$successCount = ($verificationResults | Where-Object { $_.Status -eq "✓" }).Count
$totalCount = $verificationResults.Count

Write-Host ""
Write-Host "Installed: $successCount/$totalCount modules" -ForegroundColor $(if ($successCount -eq $totalCount) { "Green" } else { "Yellow" })
Write-Host ""

if ($successCount -eq $totalCount) {
    Write-Host "✨ Rebuild complete - All modules installed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some modules failed to install!" -ForegroundColor Yellow
    exit 1
}
