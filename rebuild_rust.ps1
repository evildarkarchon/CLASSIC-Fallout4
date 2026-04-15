<#
.SYNOPSIS
    General-purpose Rust rebuild script for CLASSIC.

.DESCRIPTION
    Rebuilds one or more Rust targets used by the CLASSIC project:
      - Python bindings (PyO3 wheels, install + verify)
      - Rust workspace (cargo build --workspace)
      - Node bindings (NAPI-RS addon build)

    By default, this script targets the Rust workspace unless -Target is specified.
    Python bindings remain available for legacy/deprecation support.

.PARAMETER Target
    Rebuild scope:
      - python    : Build/install/verify Python bindings
      - workspace : Build full Rust workspace via cargo (default)
      - node      : Build Node/Bun bindings

.PARAMETER Crates
    Optional positional filters:
      - Target python: matches Python binding modules by package/wheel/import name
      - Target workspace/all: maps to cargo package filters (`cargo build -p <crate>`)
      - Target node: currently ignored

.PARAMETER Clean
    Perform clean rebuild behavior for selected targets.

.PARAMETER BuildOnly
    Python target: build wheels but skip install/verification.
    Other targets: accepted for compatibility but has no effect.

.PARAMETER Debug
    Workspace/node targets: use debug-oriented build commands.
    Python target: currently ignored (maturin release wheels are used).

.EXAMPLE
    ./rebuild_rust.ps1
    # Default: rebuild Rust workspace

.EXAMPLE
    ./rebuild_rust.ps1 classic_yaml
    # Default workspace target with package filter equivalent to `cargo build -p classic_yaml`

.EXAMPLE
    ./rebuild_rust.ps1 -Target python classic_yaml
    # Rebuild only matching Python binding module(s)

.EXAMPLE
    ./rebuild_rust.ps1 -Target workspace classic-scanlog-core
    # Rebuild only specific Rust workspace crate(s)

.EXAMPLE
    ./rebuild_rust.ps1 -Target workspace -Clean
    # Clean + rebuild Rust workspace

.EXAMPLE
    ./rebuild_rust.ps1 -Target node -DebugBuild
    # Build node addon in debug mode

.EXAMPLE
    ./rebuild_rust.ps1 -Clean
    # Clean + rebuild entire Rust workspace
#>

param (
    [Parameter(ValueFromRemainingArguments = $true, Position = 0)]
    [string[]]$Crates,

    [Parameter(Mandatory = $false)]
    [ValidateSet("python", "workspace", "node")]
    [string]$Target = "workspace",

    [Parameter(Mandatory = $false)]
    [switch]$Clean,

    [Parameter(Mandatory = $false)]
    [switch]$BuildOnly,

    [Parameter(Mandatory = $false)]
    [switch]$DebugBuild
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$WorkspaceRootManifest = Join-Path $ProjectRoot "Cargo.toml"
$UseUv = [bool](Get-Command uv -ErrorAction SilentlyContinue)
$PythonBindingsRoot = Join-Path $ProjectRoot "python-bindings"
$PythonBindingsVenv = Join-Path $PythonBindingsRoot ".venv"
$PythonBindingsPython = Join-Path $PythonBindingsVenv "Scripts/python.exe"

function Assert-LastExitCode {
    param (
        [string]$CommandLabel
    )

    if ($LASTEXITCODE -ne 0) {
        Write-Error "$CommandLabel failed with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
}

function Get-RustModuleInfo {
    param (
        [string]$CargoPath
    )

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
        return [PSCustomObject]@{
            WheelName   = $packageName.Replace('-', '_')
            Dir         = Split-Path -Path $CargoPath -Parent
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
            $exitCode = 1

            try {
                # Stream output directly so Ctrl+C is handled like a normal foreground command.
                $PSNativeCommandUseErrorActionPreference = $false
                if ($UseUv) {
                    & uv run --python $PythonBindingsPython maturin build --release --out dist 2>&1 | Tee-Object -Variable outputText | ForEach-Object { Write-Host $_ }
                }
                else {
                    & maturin build --release --out dist 2>&1 | Tee-Object -Variable outputText | ForEach-Object { Write-Host $_ }
                }
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

function Invoke-CommandWithTransientLinkerRetry {
    param (
        [string[]]$Command,
        [string]$CommandLabel,
        [int]$MaxAttempts = 3
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
        $outputText = @()
        $exitCode = 1
        $commandName = $Command[0]
        $commandArgs = if ($Command.Count -gt 1) { $Command[1..($Command.Count - 1)] } else { @() }

        try {
            $PSNativeCommandUseErrorActionPreference = $false
            & $commandName @commandArgs 2>&1 | Tee-Object -Variable outputText | ForEach-Object { Write-Host $_ }
            $exitCode = $LASTEXITCODE
        }
        finally {
            $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference
        }

        if ($exitCode -in @(-1073741510, 3221225786)) {
            throw [System.OperationCanceledException]::new("Build interrupted by Ctrl+C.")
        }

        if ($exitCode -eq 0) {
            return $true
        }

        $combinedOutput = (@($outputText | ForEach-Object { "$_" }) | Out-String)
        if ((-not (Test-IsTransientLinkerLock -Text $combinedOutput)) -or $attempt -eq $MaxAttempts) {
            return $false
        }

        $sleepSeconds = [int][Math]::Pow(2, $attempt)
        Write-Warning "Detected transient Windows linker file lock while running $CommandLabel (attempt $attempt/$MaxAttempts). Retrying in $sleepSeconds second(s)..."
        Start-Sleep -Seconds $sleepSeconds
    }

    return $false
}

function Get-PythonRustModules {
    param (
        [string[]]$CrateFilters
    )

    Write-Host "🔍 Discovering Rust Python modules..." -ForegroundColor Cyan
    $rustModules = @()

    $searchPaths = @(
        (Join-Path $ProjectRoot "foundation"),
        (Join-Path $ProjectRoot "python-bindings")
    )

    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            $cargoFiles = Get-ChildItem -Path $path -Filter "Cargo.toml" -Recurse -File
            foreach ($file in $cargoFiles) {
                $info = Get-RustModuleInfo -CargoPath $file.FullName
                if ($info) {
                    $rustModules += $info
                }
            }
        }
    }

    # Sort modules (foundation first, then alphabetical)
    $rustModules = @($rustModules | Sort-Object {
            if ($_.Dir -match "[\\/]foundation([\\/]|$)") { "0_" + $_.WheelName } else { "1_" + $_.WheelName }
        })

    # Filter modules if arguments provided
    if ($CrateFilters -and $CrateFilters.Count -gt 0) {
        $filteredModules = @()
        foreach ($crate in $CrateFilters) {
            $match = $rustModules | Where-Object {
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
            exit 1
        }

        # Deduplicate by WheelName and ensure array
        $rustModules = @($filteredModules | Group-Object WheelName | ForEach-Object { $_.Group[0] })
    }

    return @($rustModules)
}

function Remove-PythonInstalledArtifacts {
    param (
        [array]$RustModules
    )

    $sitePackages = Join-Path $PythonBindingsVenv "Lib/site-packages"
    if (-not (Test-Path $sitePackages)) {
        Write-Host "ℹ️  No Python bindings .venv site-packages found; skipping installed artifact cleanup." -ForegroundColor Gray
        return
    }

    Write-Host "🗑️  Removing old Python binding artifacts from python-bindings/.venv..." -ForegroundColor Cyan
    foreach ($module in $RustModules) {
        Remove-Item -Path (Join-Path $sitePackages "$($module.WheelName)*.pyd") -ErrorAction SilentlyContinue
        Remove-Item -Path (Join-Path $sitePackages "$($module.WheelName)*.dll") -ErrorAction SilentlyContinue
        Remove-Item -Path (Join-Path $sitePackages "$($module.WheelName)-*.dist-info") -Recurse -ErrorAction SilentlyContinue
    }
}

function Invoke-PythonBindingsRebuild {
    param (
        [string[]]$CrateFilters,
        [switch]$CleanBuild,
        [switch]$BuildOnlyMode
    )

    Write-Host "Rust bindings are mandatory prerequisites for CLASSIC Python entrypoints." -ForegroundColor Cyan
    Write-Host "This run rebuilds/installs required Python bindings used by startup-all validation." -ForegroundColor Cyan
    Write-Host "Using Python bindings virtual environment at $PythonBindingsVenv" -ForegroundColor Cyan

    if (-not (Test-Path $PythonBindingsPython)) {
        Write-Error "Python bindings virtual environment not found at '$PythonBindingsVenv'. Create it first with 'uv venv python-bindings/.venv' and install dependencies into that interpreter."
        exit 1
    }

    $rustModules = Get-PythonRustModules -CrateFilters $CrateFilters
    if ($rustModules.Count -eq 0) {
        Write-Error "No Rust Python modules were discovered."
        exit 1
    }

    Write-Host "Found $($rustModules.Count) Python module(s) to build." -ForegroundColor Cyan
    foreach ($m in $rustModules) {
        $relativeDir = $m.Dir.Replace($ProjectRoot, ".").Replace('\\', '/')
        Write-Host " - $($m.WheelName) ($relativeDir)" -ForegroundColor Gray
    }

    if ($CleanBuild) {
        Write-Host "🧹 Cleaning old Rust build artifacts..." -ForegroundColor Cyan
        Push-Location $ProjectRoot
        try {
            & cargo clean
            Assert-LastExitCode -CommandLabel "cargo clean"
        }
        finally {
            Pop-Location
        }

        Remove-PythonInstalledArtifacts -RustModules $rustModules
    }
    else {
        Write-Host "ℹ️  Skipping clean step (use -Clean to force)" -ForegroundColor Gray
    }

    Write-Host ""
    if ($BuildOnlyMode) {
        Write-Host "🔨 Building wheels (install skipped)..." -ForegroundColor Yellow
    }
    else {
        Write-Host "🔨 Building and installing..." -ForegroundColor Yellow
    }
    Write-Host ""

    foreach ($module in $rustModules) {
        Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "Building $($module.WheelName)..." -ForegroundColor Cyan
        Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

        Push-Location $module.Dir
        try {
            $buildOk = Invoke-MaturinBuildWithRetry -WheelName $module.WheelName
            if (-not $buildOk) {
                Write-Error "Failed to build $($module.WheelName)!"
                exit 1
            }

            $wheel = Get-ChildItem -Path "dist\$($module.WheelName)-*.whl" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

            if (-not $wheel) {
                Write-Error "No wheel file found for $($module.WheelName)!"
                exit 1
            }

            if (-not $BuildOnlyMode) {
                Write-Host "📦 Installing $($module.WheelName)..." -ForegroundColor Green
                if ($UseUv) {
                    & uv pip install --python $PythonBindingsPython $wheel.FullName --reinstall
                    Assert-LastExitCode -CommandLabel "uv pip install --python $PythonBindingsPython $($wheel.FullName)"
                }
                else {
                    & $PythonBindingsPython -m pip install $wheel.FullName --force-reinstall
                    Assert-LastExitCode -CommandLabel "$PythonBindingsPython -m pip install $($wheel.FullName)"
                }
            }
        }
        finally {
            Pop-Location
        }

        Write-Host ""
    }

    if ($BuildOnlyMode) {
        Write-Host "✨ Wheel build complete. Install these wheels before running CLASSIC Python entrypoints." -ForegroundColor Green
        return
    }

    Write-Host "✅ Verifying installations..." -ForegroundColor Green
    Write-Host ""

    $verificationResults = @()
    foreach ($module in $rustModules) {
        try {
            $importName = $module.ImportName
            $version = & $PythonBindingsPython -c "import $importName; print($importName.__version__)" 2>&1

            if ($LASTEXITCODE -eq 0) {
                $verificationResults += @{ Module = $module.WheelName; Status = "✓"; Version = $version }
                Write-Host "  ✓ $($module.WheelName) (import: $importName) v$version" -ForegroundColor Green
            }
            else {
                $verificationResults += @{ Module = $module.WheelName; Status = "✗"; Version = "Failed" }
                Write-Host "  ✗ $($module.WheelName) (import: $importName) - Import failed" -ForegroundColor Red
            }
        }
        catch {
            $verificationResults += @{ Module = $module.WheelName; Status = "✗"; Version = "Error" }
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
        Write-Host "✨ Python bindings rebuild complete!" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Some Python modules failed!" -ForegroundColor Yellow
        exit 1
    }
}

function Invoke-RustWorkspaceRebuild {
    param (
        [switch]$CleanBuild,
        [switch]$DebugBuild,
        [string[]]$CrateFilters
    )

    if (-not (Test-Path $WorkspaceRootManifest)) {
        Write-Error "Rust workspace manifest not found: $WorkspaceRootManifest"
        exit 1
    }

    if ($CleanBuild) {
        Write-Host "🧹 Cleaning Rust workspace..." -ForegroundColor Cyan
        Push-Location $ProjectRoot
        try {
            & cargo clean
            Assert-LastExitCode -CommandLabel "cargo clean"
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host "ℹ️  Skipping workspace clean step (use -Clean to force)" -ForegroundColor Gray
    }

    $cargoArgs = @("build")
    if ($CrateFilters -and $CrateFilters.Count -gt 0) {
        Write-Host "Using workspace crate filters: $($CrateFilters -join ', ')" -ForegroundColor Cyan
        foreach ($crate in $CrateFilters) {
            $cargoArgs += @("-p", $crate)
        }
    }
    else {
        $cargoArgs += "--workspace"
    }
    if (-not $DebugBuild) {
        $cargoArgs += "--release"
    }

    Write-Host "🔨 Building Rust workspace..." -ForegroundColor Yellow
    Write-Host "cargo $($cargoArgs -join ' ')" -ForegroundColor DarkGray
    Push-Location $ProjectRoot
    try {
        & cargo @cargoArgs
        Assert-LastExitCode -CommandLabel "cargo build --workspace"
    }
    finally {
        Pop-Location
    }

    Write-Host "✨ Rust workspace rebuild complete!" -ForegroundColor Green
}

function Invoke-NodeBindingsRebuild {
    param (
        [switch]$CleanBuild,
        [switch]$DebugBuild
    )

    $nodeDir = Join-Path $ProjectRoot "node-bindings/classic-node"
    if (-not (Test-Path $nodeDir)) {
        Write-Error "Node bindings directory not found: $nodeDir"
        exit 1
    }

    Push-Location $nodeDir
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "Installing node dependencies..." -ForegroundColor Cyan
            & bun install
            Assert-LastExitCode -CommandLabel "bun install"
        }

        if ($CleanBuild) {
            Write-Host "🧹 Cleaning Node binding artifacts..." -ForegroundColor Yellow
            Remove-Item -Force -ErrorAction SilentlyContinue *.node
            Remove-Item -Force -ErrorAction SilentlyContinue index.js
            Remove-Item -Force -ErrorAction SilentlyContinue index.d.ts

            & cargo clean -p classic-node
            Assert-LastExitCode -CommandLabel "cargo clean -p classic-node"
        }
        else {
            Write-Host "ℹ️  Skipping node clean step (use -Clean to force)" -ForegroundColor Gray
        }

        if ($DebugBuild) {
            Write-Host "🔨 Building classic-node (debug)..." -ForegroundColor Cyan
            if (-not (Invoke-CommandWithTransientLinkerRetry -Command @("bun", "run", "build:debug") -CommandLabel "bun run build:debug")) {
                Write-Error "bun run build:debug failed after retry attempts."
                exit 1
            }
        }
        else {
            Write-Host "🔨 Building classic-node (release)..." -ForegroundColor Cyan
            if (-not (Invoke-CommandWithTransientLinkerRetry -Command @("bun", "run", "build") -CommandLabel "bun run build")) {
                Write-Error "bun run build failed after retry attempts."
                exit 1
            }
        }

        Write-Host "Build complete!" -ForegroundColor Green

        $nodeFile = Get-ChildItem -Filter "*.node" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($nodeFile) {
            Write-Host "  Native addon: $($nodeFile.Name) ($([math]::Round($nodeFile.Length / 1MB, 2)) MB)" -ForegroundColor Gray
        }
        if (Test-Path "index.d.ts") {
            Write-Host "  TypeScript types: index.d.ts" -ForegroundColor Gray
        }

        Write-Host "✨ Node bindings rebuild complete!" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

Write-Host "CLASSIC Rust rebuild script" -ForegroundColor Cyan
Write-Host "Target: $Target" -ForegroundColor Cyan

if ($Crates -and $Target -eq "node") {
    Write-Warning "Positional crate/module filters are ignored for -Target node. Use -Target python to build wheels."
}
if ($BuildOnly -and ($Target -eq "workspace" -or $Target -eq "node")) {
    Write-Warning "-BuildOnly only affects Python wheel install/verification. No-op for target '$Target'."
}
if ($DebugBuild -and $Target -eq "python") {
    Write-Warning "-DebugBuild currently has no effect for Python bindings (release wheels are produced)."
}

switch ($Target) {
    "python" {
        Invoke-PythonBindingsRebuild -CrateFilters $Crates -CleanBuild:$Clean -BuildOnlyMode:$BuildOnly
    }
    "workspace" {
        Invoke-RustWorkspaceRebuild -CleanBuild:$Clean -DebugBuild:$DebugBuild -CrateFilters $Crates
    }
    "node" {
        Invoke-NodeBindingsRebuild -CleanBuild:$Clean -DebugBuild:$DebugBuild
    }
}

Write-Host "✨ Rebuild target '$Target' complete." -ForegroundColor Green
