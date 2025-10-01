# Rebuild Rust Extension Script
# Ensures clean rebuild of classic_core.pyd

$ErrorActionPreference = "Stop"

Write-Host "🧹 Cleaning old builds..." -ForegroundColor Cyan
Push-Location classic-rust
cargo clean
Pop-Location

Write-Host "🗑️  Removing old .pyd files..." -ForegroundColor Cyan
Remove-Item -Path ".venv\Lib\site-packages\classic_core*.pyd" -ErrorAction SilentlyContinue
Remove-Item -Path ".venv\Lib\site-packages\classic_core*.dll" -ErrorAction SilentlyContinue
Remove-Item -Path ".venv\Lib\site-packages\classic_core-*.dist-info" -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path "classic-rust\python\classic_core\*.pyd" -ErrorAction SilentlyContinue
Remove-Item -Path "classic-rust\python\classic_core\*.dll" -ErrorAction SilentlyContinue

Write-Host "🔨 Building Rust extension..." -ForegroundColor Yellow
Push-Location classic-rust
maturin build --release --out dist
Pop-Location

Write-Host "📦 Installing wheel..." -ForegroundColor Green
$wheel = Get-ChildItem -Path "classic-rust\dist\classic_core-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($wheel) {
    uv pip install $wheel.FullName --force-reinstall
} else {
    Write-Error "No wheel file found!"
    exit 1
}

Write-Host "✅ Verifying installation..." -ForegroundColor Green
python -c "import classic_core; print(f'Rust version: {classic_core.__version__}')"

Write-Host "`n✨ Rebuild complete!" -ForegroundColor Green
