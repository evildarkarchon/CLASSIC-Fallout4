param(
    [string]$BuildRoot = (Join-Path $PSScriptRoot "build-qt-policy-check"),
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Stop"

$policyProjectDir = Join-Path $PSScriptRoot "cmake\qt-policy-check"
$fakeQtDir = Join-Path $BuildRoot "fake-system-qt\lib\cmake\Qt6"
$rejectBuildDir = Join-Path $BuildRoot "reject"
$allowBuildDir = Join-Path $BuildRoot "allow"

function New-FakeQtPackage {
    param([string]$QtConfigDir)

    New-Item -ItemType Directory -Force -Path $QtConfigDir | Out-Null

@'
set(Qt6_FOUND TRUE)
set(Qt6_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(Qt6_VERSION 6.10.0)
set(Qt6_VERSION_MAJOR 6)
set(Qt6_VERSION_MINOR 10)
set(Qt6_VERSION_PATCH 0)
include("${CMAKE_CURRENT_LIST_DIR}/Qt6CoreConfig.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/Qt6WidgetsConfig.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/Qt6NetworkConfig.cmake")
'@ | Set-Content -Path (Join-Path $QtConfigDir "Qt6Config.cmake") -Encoding utf8

    @'
set(Qt6Core_FOUND TRUE)
if(NOT TARGET Qt6::Core)
    add_library(Qt6::Core INTERFACE IMPORTED)
endif()
'@ | Set-Content -Path (Join-Path $QtConfigDir "Qt6CoreConfig.cmake") -Encoding utf8

    @'
set(Qt6Widgets_FOUND TRUE)
if(NOT TARGET Qt6::Widgets)
    add_library(Qt6::Widgets INTERFACE IMPORTED)
endif()
'@ | Set-Content -Path (Join-Path $QtConfigDir "Qt6WidgetsConfig.cmake") -Encoding utf8

    @'
set(Qt6Network_FOUND TRUE)
if(NOT TARGET Qt6::Network)
    add_library(Qt6::Network INTERFACE IMPORTED)
endif()
'@ | Set-Content -Path (Join-Path $QtConfigDir "Qt6NetworkConfig.cmake") -Encoding utf8
}

function Invoke-PolicyConfigure {
    param(
        [string]$BuildDir,
        [string[]]$AdditionalArgs = @()
    )

    $allArgs = @("-S", $policyProjectDir, "-B", $BuildDir) + $AdditionalArgs
    $output = & cmake @allArgs 2>&1
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output -join [Environment]::NewLine)
    }
}

if (Test-Path $BuildRoot) {
    Remove-Item -Recurse -Force $BuildRoot
}

New-FakeQtPackage -QtConfigDir $fakeQtDir

$rejectResult = Invoke-PolicyConfigure -BuildDir $rejectBuildDir -AdditionalArgs @(
    "-DQt6_DIR=$fakeQtDir"
)

if ($rejectResult.ExitCode -eq 0) {
    throw "Qt policy check failed: default configuration unexpectedly accepted a non-vcpkg Qt path."
}

if ($rejectResult.Output -notmatch "Resolved Qt6 from a non-vcpkg path") {
    throw "Qt policy check failed: expected the default configuration to reject non-vcpkg Qt, but got:`n$($rejectResult.Output)"
}

$allowResult = Invoke-PolicyConfigure -BuildDir $allowBuildDir -AdditionalArgs @(
    "-DQt6_DIR=$fakeQtDir",
    "-DCLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON"
)

if ($allowResult.ExitCode -ne 0) {
    throw "Qt policy check failed: fallback-enabled configuration did not accept a non-vcpkg Qt path.`n$($allowResult.Output)"
}

if ($allowResult.Output -notmatch "Using non-vcpkg Qt from") {
    throw "Qt policy check failed: fallback-enabled configuration succeeded without reporting fallback usage.`n$($allowResult.Output)"
}

Write-Host "Qt policy checks passed." -ForegroundColor Green

if (-not $KeepArtifacts -and (Test-Path $BuildRoot)) {
    Remove-Item -Recurse -Force $BuildRoot
}
