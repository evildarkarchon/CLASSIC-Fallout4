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

$cmakeArgs = @(
    "-DCLASSIC_LINKER_CHECK_MODULE=$cmakeModule",
    "-DCLASSIC_EXPECTED_LINKER=$msvcLink",
    "-DCLASSIC_SHADOW_LINKER_DIR=$(Split-Path $shadowLink -Parent)",
    "-P",
    $testScript
)

Write-Host "cmake $($cmakeArgs -join ' ')" -ForegroundColor DarkGray
& cmake @cmakeArgs
if ($LASTEXITCODE -ne 0) {
    throw "ClassicLinkerCheck regression: expected the configured MSVC linker to win over PATH shadowing."
}

Write-Host "ClassicLinkerCheck prefers the configured linker over PATH shadowing." -ForegroundColor Green
