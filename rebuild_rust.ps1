<#
.SYNOPSIS
    General-purpose Rust rebuild script for CLASSIC.

.DESCRIPTION
    Rebuilds one or more Rust targets used by the CLASSIC project:
      - Python bindings (the one PyO3 wheel for all 18 classic_* modules:
        build, remove obsolete per-module wheels, install, verify, clean-install probe)
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
      - Target python: ignored (all 18 modules ship in one wheel)
      - Target workspace/all: maps to cargo package filters (`cargo build -p <crate>`)
      - Target node: currently ignored

.PARAMETER Clean
    Perform clean rebuild behavior for selected targets.

.PARAMETER BuildOnly
    Python target: build the wheel but skip install/verification.
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
    ./rebuild_rust.ps1 -Target python
    # Rebuild, install, and verify the one Python wheel (18 classic_* modules)

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
$PythonAdapterDir = Join-Path $PythonBindingsRoot "classic-python-bindings"
$OneWheelTool = Join-Path $ProjectRoot "tools/python_wheel/one_wheel.py"

function Assert-LastExitCode {
    param (
        [string]$CommandLabel
    )

    if ($LASTEXITCODE -ne 0) {
        Write-Error "$CommandLabel failed with exit code $LASTEXITCODE."
        exit $LASTEXITCODE
    }
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
                    & uv run --no-project --python $PythonBindingsPython maturin build --release --out dist 2>&1 | Tee-Object -Variable outputText | ForEach-Object { Write-Host $_ }
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

function Get-PythonAdapterInfo {
    # The one PyO3 adapter crate builds one wheel behind the 18 classic_* facades.
    $manifest = Join-Path $PythonAdapterDir "Cargo.toml"
    if (-not (Test-Path $manifest)) {
        Write-Error "Python adapter crate not found at '$PythonAdapterDir'."
        exit 1
    }

    $content = Get-Content $manifest -Raw
    $version = $null
    if ($content -match '\[package\][\s\S]*?version\s*=\s*"(?<version>[^"]+)"') {
        $version = $Matches.version
    }
    if (-not $version) {
        Write-Error "Could not read the package version from '$manifest'."
        exit 1
    }

    return [PSCustomObject]@{
        Dir       = $PythonAdapterDir
        WheelName = "classic_python_bindings"
        Version   = $version
    }
}

function Invoke-OneWheelTool {
    param (
        [string]$Python,
        [string[]]$Arguments,
        [string]$CommandLabel
    )

    & $Python $OneWheelTool @Arguments
    Assert-LastExitCode -CommandLabel $CommandLabel
}

function Test-CleanWheelInstall {
    param (
        [string]$WheelPath,
        [string]$ExpectedVersion
    )

    # Prove the wheel on its own: a fresh environment with nothing else
    # installed, so a development artifact cannot mask a broken package.
    $cleanRoot = Join-Path $ProjectRoot ".maturin-temp\clean-install"
    if (Test-Path $cleanRoot) {
        Remove-Item -Recurse -Force $cleanRoot
    }

    Write-Host "🧪 Verifying a clean install in $cleanRoot..." -ForegroundColor Cyan
    if ($UseUv) {
        & uv venv --quiet --python $PythonBindingsPython $cleanRoot
        Assert-LastExitCode -CommandLabel "uv venv $cleanRoot"
        $cleanPython = Join-Path $cleanRoot "Scripts/python.exe"
        & uv pip install --quiet --python $cleanPython $WheelPath
        Assert-LastExitCode -CommandLabel "uv pip install (clean environment)"
    }
    else {
        & $PythonBindingsPython -m venv $cleanRoot
        Assert-LastExitCode -CommandLabel "python -m venv $cleanRoot"
        $cleanPython = Join-Path $cleanRoot "Scripts/python.exe"
        & $cleanPython -m pip install --quiet $WheelPath
        Assert-LastExitCode -CommandLabel "pip install (clean environment)"
    }

    Invoke-OneWheelTool -Python $cleanPython -Arguments @("verify", "--expected-version", $ExpectedVersion) -CommandLabel "clean-install verification"
    Remove-Item -Recurse -Force $cleanRoot
}

function Invoke-PythonBindingsRebuild {
    param (
        [string[]]$CrateFilters,
        [switch]$CleanBuild,
        [switch]$BuildOnlyMode
    )

    Write-Host "Rust bindings are mandatory prerequisites for CLASSIC Python entrypoints." -ForegroundColor Cyan
    Write-Host "This run rebuilds the one CLASSIC Python wheel (18 direct-import facades over one native extension)." -ForegroundColor Cyan
    Write-Host "Using Python bindings virtual environment at $PythonBindingsVenv" -ForegroundColor Cyan

    if (-not (Test-Path $PythonBindingsPython)) {
        Write-Error "Python bindings virtual environment not found at '$PythonBindingsVenv'. Create it first with 'uv sync --project python-bindings --inexact' (the python-bindings/ directory is a uv-managed project: pyproject.toml + uv.lock)."
        exit 1
    }

    if ($CrateFilters -and $CrateFilters.Count -gt 0) {
        Write-Warning "Python module filters are ignored: all 18 classic_* modules ship in one wheel and are always rebuilt together."
    }

    $adapter = Get-PythonAdapterInfo
    $relativeDir = $adapter.Dir.Replace($ProjectRoot, ".").Replace('\', '/')
    Write-Host " - $($adapter.WheelName) $($adapter.Version) ($relativeDir)" -ForegroundColor Gray

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
    }
    else {
        Write-Host "ℹ️  Skipping clean step (use -Clean to force)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Building $($adapter.WheelName)..." -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan

    $wheel = $null
    Push-Location $adapter.Dir
    try {
        $buildOk = Invoke-MaturinBuildWithRetry -WheelName $adapter.WheelName
        if (-not $buildOk) {
            Write-Error "Failed to build $($adapter.WheelName)!"
            exit 1
        }

        $wheel = Get-ChildItem -Path "dist\$($adapter.WheelName)-$($adapter.Version)-*.whl" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    }
    finally {
        Pop-Location
    }

    if (-not $wheel) {
        Write-Error "No wheel file found for $($adapter.WheelName) $($adapter.Version)!"
        exit 1
    }
    Write-Host "  Wheel: $($wheel.FullName)" -ForegroundColor Gray

    if ($BuildOnlyMode) {
        Write-Host "✨ Wheel build complete. Install it before running CLASSIC Python entrypoints." -ForegroundColor Green
        return
    }

    # Upgrade path: the 18 legacy per-module wheels share directory names with
    # the new facade packages. Remove their recorded files and any leftover
    # native module first, so neither a stale .pyd nor a later uninstall of a
    # legacy distribution can affect the new install.
    Write-Host "🗑️  Removing obsolete per-module binding wheels from python-bindings/.venv..." -ForegroundColor Cyan
    Invoke-OneWheelTool -Python $PythonBindingsPython -Arguments @("remove-obsolete") -CommandLabel "remove obsolete Python binding artifacts"

    Write-Host "📦 Installing $($wheel.Name)..." -ForegroundColor Green
    if ($UseUv) {
        & uv pip install --python $PythonBindingsPython $wheel.FullName --reinstall
        Assert-LastExitCode -CommandLabel "uv pip install --python $PythonBindingsPython $($wheel.FullName)"
    }
    else {
        & $PythonBindingsPython -m pip install $wheel.FullName --force-reinstall
        Assert-LastExitCode -CommandLabel "$PythonBindingsPython -m pip install $($wheel.FullName)"
    }

    Write-Host ""
    Write-Host "✅ Verifying the upgraded environment (18 imports, versions, no obsolete artifacts)..." -ForegroundColor Green
    Invoke-OneWheelTool -Python $PythonBindingsPython -Arguments @("verify", "--expected-version", $adapter.Version) -CommandLabel "installed-wheel verification"

    Test-CleanWheelInstall -WheelPath $wheel.FullName -ExpectedVersion $adapter.Version

    Write-Host ""
    Write-Host "✨ Python bindings rebuild complete! 18/18 modules verified from one wheel." -ForegroundColor Green
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
    Write-Warning "Positional crate/module filters are ignored for -Target node."
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
