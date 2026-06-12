param()

$ErrorActionPreference = "Stop"

$cmakeModule = Join-Path $PSScriptRoot "ClassicLinkerCheck.cmake"
$testScript = Join-Path $PSScriptRoot "test_classic_linker_check_prefers_cmake_linker.cmake"

if (-not (Test-Path $cmakeModule)) {
    throw "Could not find CMake module: $cmakeModule"
}

if (-not (Test-Path $testScript)) {
    throw "Could not find CMake test script: $testScript"
}

$git = Get-Command git.exe -ErrorAction Stop
$gitRoot = Split-Path (Split-Path $git.Source -Parent) -Parent
$shadowLink = Join-Path $gitRoot "usr\\bin\\link.exe"
if (-not (Test-Path $shadowLink)) {
    throw "Could not find Git-for-Windows link.exe at $shadowLink"
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\\Installer\\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "Could not find vswhere.exe at $vswhere"
}

$msvcLink = & $vswhere `
    -latest `
    -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -find "VC\\Tools\\MSVC\\**\\bin\\Hostx64\\x64\\link.exe" |
    Select-Object -First 1

if (-not $msvcLink) {
    throw "vswhere did not return an MSVC link.exe path."
}

$lldLink = Get-Command lld-link.exe -ErrorAction SilentlyContinue

function Invoke-LinkerCheckFixture {
    param(
        [string]$Label,
        [string]$CompilerId,
        [string]$SelectedLinker,
        [string]$CompilerSimulateId = "",
        [switch]$ExpectFailure
    )

    $cmakeArgs = @(
        "-DCLASSIC_LINKER_CHECK_MODULE=$cmakeModule",
        "-DCLASSIC_EXPECTED_LINKER=$msvcLink",
        "-DCLASSIC_SELECTED_LINKER=$SelectedLinker",
        "-DCLASSIC_SHADOW_LINKER_DIR=$(Split-Path $shadowLink -Parent)",
        "-DCLASSIC_COMPILER_ID=$CompilerId"
    )
    if ($CompilerSimulateId) {
        $cmakeArgs += "-DCLASSIC_COMPILER_SIMULATE_ID=$CompilerSimulateId"
    }
    $cmakeArgs += @("-P", $testScript)

    Write-Host "[$Label] cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
    & cmake @cmakeArgs
    $exitCode = $LASTEXITCODE

    if ($ExpectFailure) {
        if ($exitCode -eq 0) {
            throw "ClassicLinkerCheck regression: expected '$Label' to reject a non-MSVC-compatible linker."
        }
        Write-Host "ClassicLinkerCheck rejected non-MSVC-compatible linker for '$Label'." -ForegroundColor Green
        return
    }

    if ($exitCode -ne 0) {
        throw "ClassicLinkerCheck regression: expected '$Label' to accept the configured MSVC-compatible linker."
    }
    Write-Host "ClassicLinkerCheck accepted '$Label'." -ForegroundColor Green
}

Invoke-LinkerCheckFixture `
    -Label "MSVC compiler identity" `
    -CompilerId "MSVC" `
    -SelectedLinker $msvcLink

Invoke-LinkerCheckFixture `
    -Label "clang-cl MSVC ABI identity" `
    -CompilerId "Clang" `
    -CompilerSimulateId "MSVC" `
    -SelectedLinker $msvcLink

if ($lldLink) {
    Invoke-LinkerCheckFixture `
        -Label "clang-cl LLVM lld-link identity" `
        -CompilerId "Clang" `
        -CompilerSimulateId "MSVC" `
        -SelectedLinker $lldLink.Source
}

Invoke-LinkerCheckFixture `
    -Label "clang-cl rejects PATH-shadowed link.exe" `
    -CompilerId "Clang" `
    -CompilerSimulateId "MSVC" `
    -SelectedLinker $shadowLink `
    -ExpectFailure

Write-Host "ClassicLinkerCheck covers MSVC and clang-cl linker selection." -ForegroundColor Green
