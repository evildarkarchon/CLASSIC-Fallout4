# Rebuild Rust Extension Script
# Ensures clean rebuild of all Rust Python modules

param (
    [Parameter(ValueFromRemainingArguments = $true, Position = 0)]
    [string[]]$Crates,

    [Parameter(Mandatory = $false)]
    [switch]$Clean,

    [Parameter(Mandatory = $false)]
    [switch]$BuildOnly  # Skip install and verification (useful for CI)
)

$ErrorActionPreference = "Stop"

Write-Host "Rust bindings are mandatory prerequisites for CLASSIC Python entrypoints." -ForegroundColor Cyan
Write-Host "This script rebuilds/installs required bindings used by startup-all validation." -ForegroundColor Cyan

# Function to parse Cargo.toml
function Get-RustModuleInfo {
    param ($CargoPath)

    $content = Get-Content $CargoPath -Raw
    
    # Extract package name
    $packageName = $null
    if ($content -match '\[package\][\s\S]*?name\s*=\s*"(?<name>[^"]+)"') {
        $packageName = $Matches.name
    }

    # Extract lib name (import name)
    $libName = $null
    if ($content -match '\[lib\][\s\S]*?name\s*=\s*"(?<name>[^"]+)"') {
        $libName = $Matches.name
    }

    # Check for PyO3 dependency or cdylib crate-type
    $isPyO3 = $content -match 'pyo3\s*=' -or $content -match 'crate-type\s*=\s*\[.*"cdylib".*\]'

    if ($packageName -and $libName -and $isPyO3) {
        return @{
            WheelName   = $packageName.Replace('-', '_')
            Dir         = $CargoPath | Split-Path -Parent
            ImportName  = $libName
            PackageName = $packageName
        }
    }
    return $null
}

function Test-IsTransientLinkerLock {
    param (
        [string]$Text
    )

    return ($Text -match "LNK1105" -and $Text -match "error code 1224") -or
           $Text -match "cannot close file '.*lnk.*\.tmp'"
}

function Invoke-MaturinBuildWithRetry {
    param (
        [string]$WheelName,
        [int]$MaxAttempts = 3
    )

    $tempRoot = Join-Path $PWD.Path ".maturin-temp"
    if (-not (Test-Path $tempRoot)) {
        New-Item -ItemType Directory -Path $tempRoot | Out-Null
    }

    $originalTemp = $env:TEMP
    $originalTmp = $env:TMP

    try {
        for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
            $attemptTemp = Join-Path $tempRoot ("{0}-{1}" -f $WheelName, $attempt)
            New-Item -ItemType Directory -Path $attemptTemp -Force | Out-Null
            $env:TEMP = $attemptTemp
            $env:TMP = $attemptTemp

            $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
            $outputText = @()
            try {
                # Stream output directly so Ctrl+C is handled like a normal foreground command.
                $PSNativeCommandUseErrorActionPreference = $false
                & maturin build --release --out dist 2>&1 | Tee-Object -Variable outputText | ForEach-Object { Write-Host $_ }
                $exitCode = $LASTEXITCODE
            }
            finally {
                $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference
            }

            if ($exitCode -in @(-1073741510, 3221225786)) {
                throw [System.OperationCanceledException]::new("Build interrupted by Ctrl+C.")
            }

            $outputText = @($outputText | ForEach-Object { "$_" })

            if ($exitCode -eq 0) {
                return $true
            }

            $combinedOutput = ($outputText | Out-String)
            if ((-not (Test-IsTransientLinkerLock -Text $combinedOutput)) -or $attempt -eq $MaxAttempts) {
                return $false
            }

            $sleepSeconds = [int][Math]::Pow(2, $attempt)
            Write-Warning "Detected transient Windows linker file lock while building $WheelName (attempt $attempt/$MaxAttempts). Retrying in $sleepSeconds second(s)..."
            Start-Sleep -Seconds $sleepSeconds
        }
    }
    finally {
        $env:TEMP = $originalTemp
        $env:TMP = $originalTmp
    }

    return $false
}

# Discover modules
Write-Host "🔍 Discovering Rust Python modules..." -ForegroundColor Cyan
$RustModules = @()

# Search directories
$searchPaths = @("ClassicLib-rs/foundation", "ClassicLib-rs/python-bindings")
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        $cargoFiles = Get-ChildItem -Path $path -Filter "Cargo.toml" -Recurse
        foreach ($file in $cargoFiles) {
            $info = Get-RustModuleInfo -CargoPath $file.FullName
            if ($info) {
                # Make path relative to project root
                $relPath = $info.Dir.Substring($PWD.Path.Length + 1).Replace('\', '/')
                $info.Dir = $relPath
                $RustModules += $info
            }
        }
    }
}

# Sort modules (foundation first, then alphabetical)
$RustModules = $RustModules | Sort-Object { 
    if ($_.Dir -match "foundation") { "0_" + $_.WheelName } else { "1_" + $_.WheelName } 
}

# Filter modules if arguments provided
if ($Crates) {
    $filteredModules = @()
    foreach ($crate in $Crates) {
        $match = $RustModules | Where-Object { 
            $_.WheelName -match $crate -or 
            $_.ImportName -match $crate -or 
            $_.PackageName -match $crate 
        }
        if ($match) {
            $filteredModules += $match
        }
        else {
            Write-Warning "Could not find module matching '$crate'"
        }
    }
    if ($filteredModules.Count -eq 0) {
        Write-Error "No modules matched the provided arguments."
    }
    # Deduplicate by WheelName and ensure array
    $RustModules = @($filteredModules | Group-Object WheelName | ForEach-Object { $_.Group[0] })
}

Write-Host "Found $($RustModules.Count) modules to build." -ForegroundColor Cyan
foreach ($m in $RustModules) {
    Write-Host " - $($m.WheelName) ($($m.Dir))" -ForegroundColor Gray
}

# Clean if requested
if ($Clean) {
    Write-Host "🧹 Cleaning old builds..." -ForegroundColor Cyan
    Push-Location ClassicLib-rs
    cargo clean
    Pop-Location

    Write-Host "🗑️  Removing old .pyd files from venv..." -ForegroundColor Cyan
    foreach ($module in $RustModules) {
        Remove-Item -Path ".venv\Lib\site-packages\$($module.WheelName)*.pyd" -ErrorAction SilentlyContinue
        Remove-Item -Path ".venv\Lib\site-packages\$($module.WheelName)*.dll" -ErrorAction SilentlyContinue
        Remove-Item -Path ".venv\Lib\site-packages\$($module.WheelName)-*.dist-info" -Recurse -ErrorAction SilentlyContinue
    }
}
else {
    Write-Host "ℹ️  Skipping clean step (use -Clean to force)" -ForegroundColor Gray
}

Write-Host ""
if ($BuildOnly) {
    Write-Host "🔨 Building wheels (install skipped)..." -ForegroundColor Yellow
}
else {
    Write-Host "🔨 Building and installing..." -ForegroundColor Yellow
}
Write-Host ""

foreach ($module in $RustModules) {
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Building $($module.WheelName)..." -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

    Push-Location $module.Dir

    # Build wheel
    $buildOk = Invoke-MaturinBuildWithRetry -WheelName $module.WheelName
    if (-not $buildOk) {
        Pop-Location
        Write-Error "Failed to build $($module.WheelName)!"
        exit 1
    }

    # Find the latest wheel
    $wheel = Get-ChildItem -Path "dist\$($module.WheelName)-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $wheel) {
        Pop-Location
        Write-Error "No wheel file found for $($module.WheelName)!"
        exit 1
    }

    # Install unless BuildOnly mode
    if (-not $BuildOnly) {
        Write-Host "📦 Installing $($module.WheelName)..." -ForegroundColor Green
        uv pip install $wheel.FullName --force-reinstall
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-Error "Failed to install $($module.WheelName)!"
            exit 1
        }
    }

    Pop-Location
    Write-Host ""
}

# Skip verification in BuildOnly mode
if ($BuildOnly) {
    Write-Host "✨ Wheel build complete. Install these wheels before running CLASSIC Python entrypoints." -ForegroundColor Green
    exit 0
}

Write-Host "✅ Verifying installations..." -ForegroundColor Green
Write-Host ""

# Verify each module
$verificationResults = @()
foreach ($module in $RustModules) {
    try {
        $importName = $module.ImportName
        $version = .venv\Scripts\python -c "import $importName; print($importName.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $verificationResults += @{Module = $module.WheelName; Status = "✓"; Version = $version }
            Write-Host "  ✓ $($module.WheelName) (import: $importName) v$version" -ForegroundColor Green
        }
        else {
            $verificationResults += @{Module = $module.WheelName; Status = "✗"; Version = "Failed" }
            Write-Host "  ✗ $($module.WheelName) (import: $importName) - Import failed" -ForegroundColor Red
        }
    }
    catch {
        $verificationResults += @{Module = $module.WheelName; Status = "✗"; Version = "Error" }
        Write-Host "  ✗ $($module.WheelName) (import: $importName) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

$successCount = @($verificationResults | Where-Object { $_.Status -eq "✓" }).Count
$totalCount = @($verificationResults).Count

Write-Host ""
Write-Host "Installed: $successCount/$totalCount modules" -ForegroundColor $(if ($successCount -eq $totalCount) { "Green" } else { "Yellow" })
Write-Host ""

if ($successCount -eq $totalCount) {
    Write-Host "✨ Build complete!" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Some modules failed!" -ForegroundColor Yellow
    exit 1
}
