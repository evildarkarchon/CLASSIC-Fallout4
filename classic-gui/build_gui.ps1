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
    The ci-system-qt presets are CI-oriented release presets for prebuilt Qt
    installs and intentionally avoid vcpkg manifest mode.

.PARAMETER Clean
    Remove build directory before building.

.PARAMETER Test
    Run CTest after building (if tests are available).

.PARAMETER TestOnly
    Run selected tests against a completed build from the same checkout,
    compiler, and preset. Requires -Test and cannot be combined with build
    cleanup, install, or packaging.

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
    .\build_gui.ps1 -Preset ci-system-qt
    .\build_gui.ps1 -Compiler clang-cl
    .\build_gui.ps1 -Debug -Compiler clang-cl
    .\build_gui.ps1 -Preset system-fallback -Compiler clang-cl
    .\build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring
    .\build_gui.ps1 -Test -CTestName classic-gui-test-resultscontroller,classic-gui-test-markdownviewer
    .\build_gui.ps1 -Test -CTestArgs @('--repeat', 'until-fail:2')
    .\build_gui.ps1 -Preset ci-system-qt -Test -TestOnly -CTestName classic-gui-consumer-conformance
#>

param(
    [switch]$Clean,
    [switch]$Test,
    [switch]$TestOnly,
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

    $normalized = @(ConvertTo-TestNameList -TestNames $TestNames)
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
function ConvertTo-TestNameList {
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

<#
.SYNOPSIS
    Finds the resource compiler CMake should use for MSVC-style manifest links.
#>
function Get-WindowsResourceCompiler {
    param([string]$ClangClPath)

    # VS Dev Shell can publish the SDK root/version without adding its x64 bin directory to PATH.
    # Prefer that exact SDK rc.exe so resource compilation uses the validated SDK toolchain.
    if (Test-WindowsSdkEnvironment) {
        $sdkVersion = $env:WindowsSDKVersion.TrimEnd("\\")
        $sdkRcPath = Join-Path $env:WindowsSdkDir "bin\$sdkVersion\x64\rc.exe"
        if (Test-Path $sdkRcPath) {
            return Get-Command $sdkRcPath -ErrorAction SilentlyContinue
        }
    }

    $rcCommands = @(Get-Command rc.exe -All -ErrorAction SilentlyContinue | Where-Object { $_.Source })
    $windowsSdkRc = $rcCommands |
        Where-Object { $_.Source -match '\\Windows Kits\\10\\bin\\[^\\]+\\x64\\rc\.exe$' } |
        Select-Object -First 1
    if ($windowsSdkRc) {
        return $windowsSdkRc
    }

    if ($ClangClPath) {
        $llvmRcPath = Join-Path (Split-Path -Parent $ClangClPath) "llvm-rc.exe"
        if (Test-Path $llvmRcPath) {
            return Get-Command $llvmRcPath -ErrorAction SilentlyContinue
        }
    }

    return $rcCommands | Select-Object -First 1
}

<#
.SYNOPSIS
    Checks that the Visual Studio environment exposes Windows SDK variables.
#>
function Test-WindowsSdkEnvironment {
    return -not [string]::IsNullOrWhiteSpace($env:WindowsSDKVersion) -and
        -not [string]::IsNullOrWhiteSpace($env:WindowsSdkDir)
}

<#
.SYNOPSIS
    Configures Cargo cc-rs build scripts to use clang-cl for MSVC-targeted C/C++ glue.
#>
function Set-ClangClCargoCcEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ClangClPath
    )

    # cc-rs defaults to cl.exe for -msvc targets unless target-specific
    # compiler selectors override the built-in tool lookup.
    foreach ($name in @(
            "CC_x86_64_pc_windows_msvc",
            "CC_x86_64-pc-windows-msvc",
            "CXX_x86_64_pc_windows_msvc",
            "CXX_x86_64-pc-windows-msvc"
        )) {
        [Environment]::SetEnvironmentVariable($name, $ClangClPath, "Process")
    }

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

<#
.SYNOPSIS
    Returns the checked-out commit used to bind a reusable native build.
#>
function Get-BuildSourceRevision {
    param([Parameter(Mandatory)][string]$RepositoryRoot)

    $revision = @(& git -C $RepositoryRoot rev-parse HEAD)
    if ($LASTEXITCODE -ne 0 -or $revision.Count -ne 1 -or $revision[0] -notmatch '^[0-9a-f]{40}$') {
        throw "Cannot identify the repository revision for native build reuse."
    }
    return [string]$revision[0]
}

<#
.SYNOPSIS
    Rejects a missing or mismatched completion marker before running CTest.
#>
function Assert-ReusableBuildMarker {
    param(
        [Parameter(Mandatory)][string]$MarkerPath,
        [Parameter(Mandatory)][string]$Compiler,
        [Parameter(Mandatory)][string]$Preset,
        [Parameter(Mandatory)][string]$SourceRevision
    )

    if (-not (Test-Path -LiteralPath $MarkerPath -PathType Leaf)) {
        throw "No completed native build marker exists at '$MarkerPath'. Run the build first."
    }
    try {
        $marker = Get-Content -LiteralPath $MarkerPath -Raw | ConvertFrom-Json -AsHashtable
    }
    catch {
        throw "Cannot read native build marker at '$MarkerPath': $($_.Exception.Message)"
    }
    if ($marker.schemaVersion -ne 1 -or $marker.compiler -cne $Compiler -or
        $marker.preset -cne $Preset -or $marker.sourceRevision -cne $SourceRevision) {
        throw "Native build marker does not match this checkout, compiler, and preset: '$MarkerPath'."
    }
}

<#
.SYNOPSIS
    Uses a preverified Corrosion source when CI provides one; otherwise lets FetchContent download it.
#>
function Get-CorrosionSourceCmakeArgument {
    param([string]$SourceDir)

    if ([string]::IsNullOrWhiteSpace($SourceDir)) {
        return
    }
    $resolved = [System.IO.Path]::GetFullPath($SourceDir)
    if (-not (Test-Path -LiteralPath (Join-Path $resolved "CMakeLists.txt") -PathType Leaf)) {
        throw "Corrosion source override at '$resolved' is missing CMakeLists.txt."
    }
    return "-DFETCHCONTENT_SOURCE_DIR_CORROSION:PATH=$resolved"
}

# -Package implies -Install (windeployqt must populate the install dir first)
if ($Package) { $Install = $true }

if ($TestOnly -and (-not $Test -or $Clean -or $Install -or $Package)) {
    Write-Error "-TestOnly requires -Test and cannot be combined with -Clean, -Install, or -Package."
    exit 1
}

$CTestName = @(ConvertTo-TestNameList -TestNames $CTestName)
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
        "ci-system-qt" { return "ci-system-qt-clang-cl" }
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
    "ci-system-qt" { "build" }
    "ci-system-qt-clang-cl" { "build-clang-cl" }
    "system-fallback-clang-cl" { "build-system-fallback-clang-cl" }
    "system-fallback-debug-clang-cl" { "build-system-fallback-debug-clang-cl" }
    default {
        if ($isDebugPreset) { "build-debug" } else { "build" }
    }
}
$buildDir = Join-Path $ScriptDir $buildDirName
$sourceRevision = Get-BuildSourceRevision -RepositoryRoot (Split-Path -Parent $ScriptDir)
$buildMarkerPath = Join-Path $buildDir ".classic-build-complete.json"

# ── Ensure VS Dev Shell environment (needed for Ninja + MSVC) ─────
# vcpkg Qt pulls SDK-backed ports such as opengl; those portfiles need the
# Windows SDK env vars, not just cl.exe on PATH.
$clFound = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $clFound -or -not (Test-WindowsSdkEnvironment)) {
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
$dumpbinFound = Get-Command dumpbin.exe -ErrorAction SilentlyContinue
$rcFound = Get-WindowsResourceCompiler -ClangClPath $clangClFound.Source
$ninjaFound = Get-Command ninja.exe -ErrorAction SilentlyContinue
if (-not $clFound -or -not (Test-WindowsSdkEnvironment) -or ($usesClangCl -and (-not $clangClFound -or -not $lldLinkFound -or -not $dumpbinFound -or -not $rcFound)) -or -not $ninjaFound) {
    if (-not $clFound) {
        Write-Host "Missing required tool: cl.exe" -ForegroundColor Red
    }
    if (-not (Test-WindowsSdkEnvironment)) {
        Write-Host "Missing required environment: WindowsSDKVersion and WindowsSdkDir" -ForegroundColor Red
    }
    if ($usesClangCl -and -not $clangClFound) {
        Write-Host "Missing required tool: clang-cl.exe" -ForegroundColor Red
    }
    if ($usesClangCl -and -not $lldLinkFound) {
        Write-Host "Missing required tool: lld-link.exe" -ForegroundColor Red
    }
    if ($usesClangCl -and -not $dumpbinFound) {
        Write-Host "Missing required tool: dumpbin.exe" -ForegroundColor Red
    }
    if ($usesClangCl -and -not $rcFound) {
        Write-Host "Missing required tool: rc.exe or llvm-rc.exe" -ForegroundColor Red
    }
    if (-not $ninjaFound) {
        Write-Host "Missing required tool: ninja" -ForegroundColor Red
    }
    Write-Error "Build prerequisites are missing. Run from Developer PowerShell for Visual Studio and ensure Visual Studio C++ workload, optional clang-cl/lld-link components, and Ninja/CMake components are installed."
    exit 1
}

if ($usesClangCl) {
    Set-ClangClCargoCcEnvironment -ClangClPath $clangClFound.Source
    $env:CLASSIC_CLANG_CL = $clangClFound.Source
    $env:CLASSIC_LLD_LINK = $lldLinkFound.Source
    $env:CLASSIC_DUMPBIN = $dumpbinFound.Source
    $env:CLASSIC_RC = $rcFound.Source
}

# ── Step 1: Clean (optional) ─────────────────────────────────────
if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

Push-Location $ScriptDir
try {
    if ($TestOnly) {
        # Receipt runs must reuse only the build completed by this checkout's
        # retained GUI test step, including its Qt provider and compiler preset.
        Assert-ReusableBuildMarker -MarkerPath $buildMarkerPath -Compiler $Compiler -Preset $effectivePreset -SourceRevision $sourceRevision
        if (-not (Test-Path -LiteralPath (Join-Path $buildDir "CMakeCache.txt") -PathType Leaf) -or
            -not (Test-Path -LiteralPath (Join-Path $buildDir "build.ninja") -PathType Leaf)) {
            throw "The completed native build at '$buildDir' is missing CMake/Ninja state."
        }
        Write-Host "`n=== Reusing completed Qt 6 GUI build ===" -ForegroundColor Cyan
    }
    else {
        # Invalidate the previous completion before configure so a failed
        # rebuild cannot leave a marker that authorizes stale test evidence.
        if (Test-Path -LiteralPath $buildMarkerPath -PathType Leaf) {
            Remove-Item -LiteralPath $buildMarkerPath -Force
        }

        # ── Step 2: CMake configure ─────────────────────────────
        Write-Host "`n=== Configuring CMake (Ninja + Qt 6) ===" -ForegroundColor Cyan
        $cmakeArgs = @("--preset", $effectivePreset)
        $corrosionSourceArgument = Get-CorrosionSourceCmakeArgument -SourceDir $env:CLASSIC_CORROSION_SOURCE_DIR
        if ($corrosionSourceArgument) {
            $cmakeArgs += $corrosionSourceArgument
        }
        Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
        & cmake @cmakeArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CMake configure failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }

        # ── Step 3: CMake build ──────────────────────────────────
        Write-Host "`n=== Building Qt 6 GUI (Corrosion handles Rust build) ===" -ForegroundColor Cyan
        $buildArgs = @("--build", $buildDirName)
        Write-Host "cmake $($buildArgs -join ' ')" -ForegroundColor DarkGray
        & cmake @buildArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CMake build failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }

        $marker = [ordered]@{
            schemaVersion = 1
            compiler = $Compiler
            preset = $effectivePreset
            sourceRevision = $sourceRevision
        }
        $marker | ConvertTo-Json | Set-Content -LiteralPath $buildMarkerPath -Encoding utf8
        Write-Host "`n=== Build complete ===" -ForegroundColor Green
    }

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
