<#
.SYNOPSIS
    Build the CLASSIC C++ CLI scanner.

.DESCRIPTION
    Builds the C++ CLI application using CMake + Ninja + Corrosion.
    Corrosion automatically builds the Rust static library (classic-cpp-bridge)
    as part of the CMake build process. Requires VS Dev Shell (auto-detected).

.PARAMETER Clean
    Remove build directory before building.

.PARAMETER Test
    Run CTest (Catch2 unit tests) and integration tests after building.

.PARAMETER CTestName
    Run only the specified CTest unit test name or names. Requires -Test.
    Accepts PowerShell arrays and comma-separated strings.

.PARAMETER CTestArgs
    Additional arguments to pass to the CTest unit test run command. Requires -Test.

.PARAMETER IntegrationTestName
    Run only the specified classic-cli integration scenario name or names. Requires -Test.
    Accepts PowerShell arrays and comma-separated strings.

.PARAMETER Debug
    Build using the CMake debug preset (build-debug directory).

.PARAMETER Compiler
    C++ compiler toolchain to use. Default: msvc. Use clang-cl to build with
    clang-cl and lld-link against the Visual Studio/MSVC ABI toolchain.

.PARAMETER Install
    Run cmake --install to create a deployable layout.

.PARAMETER Package
    Run CPack to produce a distributable ZIP archive.
    Implies -Install.

.EXAMPLE
    .\build_cli.ps1
    .\build_cli.ps1 -Clean
    .\build_cli.ps1 -Test
    .\build_cli.ps1 -Debug
    .\build_cli.ps1 -Debug -Install
    .\build_cli.ps1 -Clean -Test -Install
    .\build_cli.ps1 -Package
    .\build_cli.ps1 -Compiler clang-cl
    .\build_cli.ps1 -Debug -Compiler clang-cl
    .\build_cli.ps1 -Test -CTestName "ThreadPool executes all enqueued tasks"
    .\build_cli.ps1 -Test -CTestName "ThreadPool executes all enqueued tasks","Yaml update bridge returns status"
    .\build_cli.ps1 -Test -CTestArgs @('--repeat', 'until-fail:2')
    .\build_cli.ps1 -Test -IntegrationTestName help,version
#>

param(
    [switch]$Clean,
    [switch]$Test,
    [switch]$Debug,
    [switch]$Install,
    [switch]$Package,
    [ValidateSet("msvc", "clang-cl")]
    [string]$Compiler = "msvc",
    [string[]]$CTestName = @(),
    [string[]]$CTestArgs = @(),
    [string[]]$IntegrationTestName = @()
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

# -Package implies -Install
if ($Package) { $Install = $true }

$CTestName = @(Normalize-TestNameList -TestNames $CTestName)
$CTestArgs = @($CTestArgs | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$IntegrationTestName = @(Normalize-TestNameList -TestNames $IntegrationTestName)

if (($CTestName.Count -gt 0 -or $CTestArgs.Count -gt 0 -or $IntegrationTestName.Count -gt 0) -and -not $Test) {
    Write-Error "-CTestName, -CTestArgs, and -IntegrationTestName require -Test."
    exit 1
}

if ($CTestArgs.Count -gt 0 -and $IntegrationTestName.Count -gt 0 -and $CTestName.Count -eq 0) {
    Write-Error "-CTestArgs apply only to CTest unit tests and cannot be used when only integration scenarios are selected."
    exit 1
}

$ctestRegex = New-ExactTestNameRegex -TestNames $CTestName
$selectiveTestMode = $CTestName.Count -gt 0 -or $IntegrationTestName.Count -gt 0

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-Tool([string]$ToolName) {
    return Get-Command $ToolName -ErrorAction SilentlyContinue
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

# Verify VCPKG_ROOT is set
if (-not $env:VCPKG_ROOT) {
    Write-Error "VCPKG_ROOT environment variable is not set. Install vcpkg and set VCPKG_ROOT."
    exit 1
}

# ── Ensure VS Dev Shell environment (needed for Ninja + MSVC) ─────
# Check if cl.exe is already in PATH (i.e., we're in a VS Dev Shell)
$clFound = Get-Tool "cl.exe"
if (-not $clFound) {
    Write-Host "Initializing VS Dev Shell..." -ForegroundColor Yellow
    $vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -property installationPath 2>$null
    if (-not $vsPath) {
        # Fallback: try without vswhere
        $vsPath = "C:\Program Files\Microsoft Visual Studio\18\Community"
    }
    $devShell = Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1"
    if (Test-Path $devShell) {
        & $devShell -Arch amd64 -SkipAutomaticLocation | Out-Null
    }
    else {
        Write-Error "Could not find VS Dev Shell. Run this script from a Developer PowerShell."
        exit 1
    }
}

# Validate required toolchain components before CMake configure.
$clFound = Get-Tool "cl.exe"
$clangClFound = Get-Tool "clang-cl.exe"
$lldLinkFound = Get-Tool "lld-link.exe"
$ninjaFound = Get-Tool "ninja"
if (-not $clFound -or ($Compiler -eq "clang-cl" -and (-not $clangClFound -or -not $lldLinkFound)) -or -not $ninjaFound) {
    if (-not $clFound) {
        Write-Host "Missing required tool: cl.exe" -ForegroundColor Red
    }
    if ($Compiler -eq "clang-cl" -and -not $clangClFound) {
        Write-Host "Missing required tool: clang-cl.exe" -ForegroundColor Red
    }
    if ($Compiler -eq "clang-cl" -and -not $lldLinkFound) {
        Write-Host "Missing required tool: lld-link.exe" -ForegroundColor Red
    }
    if (-not $ninjaFound) {
        Write-Host "Missing required tool: ninja" -ForegroundColor Red
    }
    Write-Error "Build prerequisites are missing. Run from Developer PowerShell for Visual Studio and ensure Visual Studio C++ workload, optional clang-cl/lld-link components, and Ninja/CMake components are installed."
    exit 1
}

# ── Step 1: Clean (optional) ─────────────────────────────────────
if ($Compiler -eq "clang-cl") {
    $buildPreset = if ($Debug) { "debug-clang-cl" } else { "default-clang-cl" }
    $buildDirName = if ($Debug) { "build-debug-clang-cl" } else { "build-clang-cl" }
}
else {
    $buildPreset = if ($Debug) { "debug" } else { "default" }
    $buildDirName = if ($Debug) { "build-debug" } else { "build" }
}
$buildDir = Join-Path $ScriptDir $buildDirName

if ($Compiler -eq "clang-cl") {
    Add-ClangClCargoCxxFlags
    $env:CLASSIC_CLANG_CL = $clangClFound.Source
    $env:CLASSIC_LLD_LINK = $lldLinkFound.Source
}

if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

# ── Step 2: CMake configure ─────────────────────────────────────
Write-Host "`n=== Configuring CMake (Ninja) ===" -ForegroundColor Cyan

$cmakeArgs = @("--preset", $buildPreset)

Push-Location $ScriptDir
try {
    Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake configure failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    # ── Step 3: CMake build ──────────────────────────────────────
    Write-Host "`n=== Building C++ CLI (Corrosion handles Rust build) ===" -ForegroundColor Cyan

    # Corrosion builds the Rust crate with PROFILE release and compiles
    # the CXX bridge glue code, so a single cmake --build is all that's needed.
    $buildArgs = @("--build", $buildDirName)

    Write-Host "cmake $($buildArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake build failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    Write-Host "`n=== Build complete ===" -ForegroundColor Green

    $exePath = Join-Path $buildDir "classic-cli.exe"
    if (Test-Path $exePath) {
        Write-Host "Output: $exePath" -ForegroundColor Cyan
    }

    # ── Step 4: Tests (optional) ─────────────────────────────────
    if ($Test) {
        $runCtest = ($CTestName.Count -gt 0) -or (-not $selectiveTestMode)
        $runIntegrationTests = ($IntegrationTestName.Count -gt 0) -or (-not $selectiveTestMode)

        if ($runCtest) {
            # Catch2 unit tests via CTest
            Write-Host "`n=== Running Catch2 unit tests (CTest) ===" -ForegroundColor Cyan
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

            $ctestRunArgs = @("--test-dir", $buildDirName, "--output-on-failure", "--no-tests=error")
            if ($ctestRegex) {
                $ctestRunArgs += @("-R", $ctestRegex)
            }
            $ctestRunArgs += $CTestArgs
            & ctest @ctestRunArgs
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Unit tests failed with exit code $LASTEXITCODE"
                exit $LASTEXITCODE
            }
            Write-Host "Unit tests passed." -ForegroundColor Green
        }
        else {
            Write-Host "Skipping Catch2 unit tests because only integration scenarios were selected." -ForegroundColor DarkGray
        }

        # Integration tests
        $integrationScript = Join-Path $ScriptDir "test_cli.ps1"
        if ($runIntegrationTests -and (Test-Path $integrationScript)) {
            Write-Host "`n=== Running integration tests ===" -ForegroundColor Cyan
            if ($IntegrationTestName.Count -gt 0) {
                Write-Host "Selected integration scenarios: $($IntegrationTestName -join ', ')" -ForegroundColor DarkGray
                & $integrationScript -BuildDir $buildDirName -TestName $IntegrationTestName
            }
            else {
                & $integrationScript -BuildDir $buildDirName
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Integration tests failed with exit code $LASTEXITCODE"
                exit $LASTEXITCODE
            }
        }
        elseif (-not $runIntegrationTests) {
            Write-Host "Skipping integration tests because only CTest names were selected." -ForegroundColor DarkGray
        }
    }

    # ── Step 5: Install (optional) ───────────────────────────────
    if ($Install) {
        if ($Compiler -eq "clang-cl") {
            $installDirName = if ($Debug) { "install-debug-clang-cl" } else { "install-clang-cl" }
        }
        else {
            $installDirName = if ($Debug) { "install-debug" } else { "install" }
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
            Invoke-CodeSigning -InstallDir $installDir -Binaries @("classic-cli.exe")
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
}
finally {
    Pop-Location
}
