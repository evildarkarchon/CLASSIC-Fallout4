<#
.SYNOPSIS
    Build the CLASSIC C++ Qt 6 GUI application.

.DESCRIPTION
    Builds the Qt 6 GUI using CMake + Ninja + Corrosion.
    Corrosion automatically builds the Rust static library (classic-cpp-bridge)
    as part of the CMake build process. Requires VS Dev Shell (auto-detected).

    The default presets expect Qt 6 to come from vcpkg via VCPKG_ROOT.
    Use the system-fallback presets only when you intentionally want a
    non-vcpkg Qt install, typically alongside CMAKE_PREFIX_PATH or Qt6_DIR.

.PARAMETER Clean
    Remove build directory before building.

.PARAMETER Test
    Run CTest after building (if tests are available).

.PARAMETER CTestName
    Run only the specified CTest test name or names. Requires -Test.
    Accepts PowerShell arrays and comma-separated strings.

.PARAMETER CTestArgs
    Additional arguments to pass to the CTest run command. Requires -Test.

.PARAMETER Debug
    Build using a debug preset (build-debug directory).

.PARAMETER Compiler
    C++ compiler toolchain to use. Default: msvc. Use clang-cl to build with
    clang-cl and lld-link against the Visual Studio/MSVC ABI toolchain.

.PARAMETER Install
    Run cmake --install to create a deployable layout with windeployqt.

.PARAMETER Package
    Run CPack to produce a distributable ZIP archive.
    Implies -Install (windeployqt must run first so Qt DLLs are included).

.PARAMETER Preset
    CMake preset name. Default: "default".

.EXAMPLE
    .\build_gui.ps1
    .\build_gui.ps1 -Clean
    .\build_gui.ps1 -Test
    .\build_gui.ps1 -Debug
    .\build_gui.ps1 -Debug -Install
    .\build_gui.ps1 -Install
    .\build_gui.ps1 -Package
    .\build_gui.ps1 -Clean -Package
    .\build_gui.ps1 -Preset system-fallback
    .\build_gui.ps1 -Debug -Preset system-fallback
    .\build_gui.ps1 -Compiler clang-cl
    .\build_gui.ps1 -Debug -Compiler clang-cl
    .\build_gui.ps1 -Preset system-fallback -Compiler clang-cl
    .\build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring
    .\build_gui.ps1 -Test -CTestName classic-gui-test-resultscontroller,classic-gui-test-markdownviewer
    .\build_gui.ps1 -Test -CTestArgs @('--repeat', 'until-fail:2')
#>

param(
    [switch]$Clean,
    [switch]$Test,
    [switch]$Debug,
    [switch]$Install,
    [switch]$Package,
    [string]$Preset = "default",
    [ValidateSet("msvc", "clang-cl")]
    [string]$Compiler = "msvc",
    [string[]]$CTestName = @(),
    [string[]]$CTestArgs = @(),
    [int]$TestTimeoutSec = 600
)

$ErrorActionPreference = "Stop"

function New-ExactTestNameRegex {
    param([string[]]$TestNames)

    $normalized = @(Normalize-TestNameList -TestNames $TestNames)
    if ($normalized.Count -eq 0) {
        return $null
    }

    $escaped = $normalized | ForEach-Object { [regex]::Escape($_) }
    return "^($($escaped -join '|'))$"
}

<#
.SYNOPSIS
    Normalizes selected test names from PowerShell arrays or comma-separated strings.
#>
function Normalize-TestNameList {
    param([string[]]$TestNames)

    $normalized = @()
    foreach ($testName in $TestNames) {
        if ($null -eq $testName) {
            continue
        }

        foreach ($candidate in ($testName -split ",")) {
            $trimmed = $candidate.Trim()
            if ($trimmed) {
                $normalized += $trimmed
            }
        }
    }

    return $normalized
}

function Add-ClangClCargoCxxFlags {
    $exceptionFlag = "/EHsc"
    foreach ($name in @("CXXFLAGS_x86_64_pc_windows_msvc", "CXXFLAGS_x86_64-pc-windows-msvc")) {
        $current = [Environment]::GetEnvironmentVariable($name, "Process")
        if ([string]::IsNullOrWhiteSpace($current)) {
            [Environment]::SetEnvironmentVariable($name, $exceptionFlag, "Process")
        }
        elseif ($current -notmatch '(^|\s)/EH') {
            [Environment]::SetEnvironmentVariable($name, "$current $exceptionFlag", "Process")
        }
    }
}

# -Package implies -Install (windeployqt must populate the install dir first)
if ($Package) { $Install = $true }

$CTestName = @(Normalize-TestNameList -TestNames $CTestName)
$CTestArgs = @($CTestArgs | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if (($CTestName.Count -gt 0 -or $CTestArgs.Count -gt 0) -and -not $Test) {
    Write-Error "-CTestName and -CTestArgs require -Test."
    exit 1
}

$ctestRegex = New-ExactTestNameRegex -TestNames $CTestName

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$effectivePreset = $Preset

function Convert-ToClangClPreset {
    param([string]$PresetName)

    switch ($PresetName) {
        "default" { return "default-clang-cl" }
        "debug" { return "debug-clang-cl" }
        "system-fallback" { return "system-fallback-clang-cl" }
        "system-fallback-debug" { return "system-fallback-debug-clang-cl" }
        "ci" { return "ci-clang-cl" }
        "ci-debug" { return "ci-debug-clang-cl" }
        default { return $PresetName }
    }
}

if ($Debug) {
    switch ($Preset) {
        "default" { $effectivePreset = "debug" }
        "ci" { $effectivePreset = "ci-debug" }
        "debug" { $effectivePreset = "debug" }
        "ci-debug" { $effectivePreset = "ci-debug" }
        "system-fallback" { $effectivePreset = "system-fallback-debug" }
        "system-fallback-debug" { $effectivePreset = "system-fallback-debug" }
        "default-clang-cl" { $effectivePreset = "debug-clang-cl" }
        "ci-clang-cl" { $effectivePreset = "ci-debug-clang-cl" }
        "debug-clang-cl" { $effectivePreset = "debug-clang-cl" }
        "ci-debug-clang-cl" { $effectivePreset = "ci-debug-clang-cl" }
        "system-fallback-clang-cl" { $effectivePreset = "system-fallback-debug-clang-cl" }
        "system-fallback-debug-clang-cl" { $effectivePreset = "system-fallback-debug-clang-cl" }
        default {
            Write-Error "Debug mode supports -Preset default, ci, debug, ci-debug, system-fallback, system-fallback-debug, and their -clang-cl variants. Received: '$Preset'."
            exit 1
        }
    }
}

if ($Compiler -eq "clang-cl") {
    $effectivePreset = Convert-ToClangClPreset -PresetName $effectivePreset
}

$usesClangCl = $effectivePreset.EndsWith("-clang-cl")
$isDebugPreset = $effectivePreset -in @(
    "debug",
    "ci-debug",
    "system-fallback-debug",
    "debug-clang-cl",
    "ci-debug-clang-cl",
    "system-fallback-debug-clang-cl"
)
$buildDirName = switch ($effectivePreset) {
    "system-fallback" { "build-system-fallback" }
    "system-fallback-debug" { "build-system-fallback-debug" }
    "default-clang-cl" { "build-clang-cl" }
    "debug-clang-cl" { "build-debug-clang-cl" }
    "ci-clang-cl" { "build-clang-cl" }
    "ci-debug-clang-cl" { "build-debug-clang-cl" }
    "system-fallback-clang-cl" { "build-system-fallback-clang-cl" }
    "system-fallback-debug-clang-cl" { "build-system-fallback-debug-clang-cl" }
    default {
        if ($isDebugPreset) { "build-debug" } else { "build" }
    }
}
$buildDir = Join-Path $ScriptDir $buildDirName

if ($usesClangCl) {
    Add-ClangClCargoCxxFlags
}

# ── Ensure VS Dev Shell environment (needed for Ninja + MSVC) ─────
$clFound = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $clFound) {
    Write-Host "Initializing VS Dev Shell..." -ForegroundColor Yellow
    $vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -property installationPath 2>$null
    if (-not $vsPath) {
        # Fallback: known VS 2026 location
        $vsPath = "C:\Program Files\Microsoft Visual Studio\18\Community"
    }
    $devShell = Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1"
    if (Test-Path $devShell) {
        & $devShell -Arch amd64 -SkipAutomaticLocation | Out-Null
    } else {
        Write-Error "Could not find VS Dev Shell. Run this script from a Developer PowerShell."
        exit 1
    }
}

# ── Verify required toolchain components are available ───────────
$clFound = Get-Command cl.exe -ErrorAction SilentlyContinue
$clangClFound = Get-Command clang-cl.exe -ErrorAction SilentlyContinue
$lldLinkFound = Get-Command lld-link.exe -ErrorAction SilentlyContinue
$ninjaFound = Get-Command ninja.exe -ErrorAction SilentlyContinue
if (-not $clFound -or ($usesClangCl -and (-not $clangClFound -or -not $lldLinkFound)) -or -not $ninjaFound) {
    if (-not $clFound) {
        Write-Host "Missing required tool: cl.exe" -ForegroundColor Red
    }
    if ($usesClangCl -and -not $clangClFound) {
        Write-Host "Missing required tool: clang-cl.exe" -ForegroundColor Red
    }
    if ($usesClangCl -and -not $lldLinkFound) {
        Write-Host "Missing required tool: lld-link.exe" -ForegroundColor Red
    }
    if (-not $ninjaFound) {
        Write-Host "Missing required tool: ninja" -ForegroundColor Red
    }
    Write-Error "Build prerequisites are missing. Run from Developer PowerShell for Visual Studio and ensure Visual Studio C++ workload, optional clang-cl/lld-link components, and Ninja/CMake components are installed."
    exit 1
}

if ($usesClangCl) {
    $env:CLASSIC_CLANG_CL = $clangClFound.Source
    $env:CLASSIC_LLD_LINK = $lldLinkFound.Source
}

# ── Step 1: Clean (optional) ─────────────────────────────────────
if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

# ── Step 2: CMake configure ─────────────────────────────────────
Write-Host "`n=== Configuring CMake (Ninja + Qt 6) ===" -ForegroundColor Cyan

Push-Location $ScriptDir
try {
    $cmakeArgs = @("--preset", $effectivePreset)
    Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    # ── Step 3: CMake build ──────────────────────────────────────
    Write-Host "`n=== Building Qt 6 GUI (Corrosion handles Rust build) ===" -ForegroundColor Cyan

    $buildArgs = @("--build", $buildDirName)
    Write-Host "cmake $($buildArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake build failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    Write-Host "`n=== Build complete ===" -ForegroundColor Green

    $exePath = Join-Path $buildDir "CLASSIC.exe"
    if (Test-Path $exePath) {
        Write-Host "Output: $exePath" -ForegroundColor Cyan
    }

    # ── Step 4: Tests (optional) ─────────────────────────────────
    if ($Test) {
        if ($TestTimeoutSec -le 0) {
            Write-Error "Test timeout must be greater than zero. Received: $TestTimeoutSec"
            exit 1
        }

        Write-Host "`n=== Running CTest ===" -ForegroundColor Cyan
        if ($CTestName.Count -gt 0) {
            Write-Host "Selected CTest names: $($CTestName -join ', ')" -ForegroundColor DarkGray
        }
        if ($CTestArgs.Count -gt 0) {
            Write-Host "Additional CTest args: $($CTestArgs -join ' ')" -ForegroundColor DarkGray
        }

        $ctestDiscoveryArgs = @("--test-dir", $buildDirName, "-N", "-V", "--no-tests=error")
        if ($ctestRegex) {
            $ctestDiscoveryArgs += @("-R", $ctestRegex)
        }
        & ctest @ctestDiscoveryArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CTest discovery failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }

        $ctestRunArgs = @("--test-dir", $buildDirName, "--output-on-failure", "--timeout", $TestTimeoutSec,
            "--no-tests=error")
        if ($ctestRegex) {
            $ctestRunArgs += @("-R", $ctestRegex)
        }
        $ctestRunArgs += $CTestArgs
        & ctest @ctestRunArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Tests failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Host "Tests passed." -ForegroundColor Green
    }

    # ── Step 5: Install (optional) ───────────────────────────────
    if ($Install) {
        if ($usesClangCl) {
            $installDirName = if ($isDebugPreset) { "install-debug-clang-cl" } else { "install-clang-cl" }
        }
        else {
            $installDirName = if ($isDebugPreset) { "install-debug" } else { "install" }
        }
        $installDir = Join-Path $ScriptDir $installDirName
        Write-Host "`n=== Installing to $installDir ===" -ForegroundColor Cyan
        & cmake --install $buildDirName --prefix $installDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Install failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Host "Installed to: $installDir" -ForegroundColor Green

        # -- Step 5.5: Sign (optional, after install) --------------------
        $signScript = Join-Path (Split-Path $ScriptDir -Parent) "tools" "sign-binaries.ps1"
        if (Test-Path $signScript) {
            . $signScript
            Invoke-CodeSigning -InstallDir $installDir -Binaries @("CLASSIC.exe")
        }
    }

    # ── Step 6: Package (optional) ──────────────────────────────────
    if ($Package) {
        $cpackConfig = Join-Path $buildDir "CPackConfig.cmake"
        $packageDir = Join-Path $buildDir "packages"
        Write-Host "`n=== Packaging with CPack (ZIP) ===" -ForegroundColor Cyan
        & cpack --config $cpackConfig -B $packageDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CPack failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        $zipFile = Get-ChildItem -Path $packageDir -Filter "*.zip" |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($zipFile) {
            Write-Host "Package: $($zipFile.FullName)" -ForegroundColor Green
        }
    }
} finally {
    Pop-Location
}
